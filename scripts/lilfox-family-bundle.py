"""Build private Happ subscriptions and approved personal pages outside Git.

Input is a protected JSON file created after recipient provisioning. This tool
never prints credentials or URLs. Publish only output/public/, never output/.

The output must not exist, even as an empty directory or dangling symlink.
Its parent must already exist, belong to the operator and not be writable by
group/others. Atomic publication requires Linux renameat2(RENAME_NOREPLACE)
and a supporting local filesystem; there is deliberately no overwrite fallback.
The operator/root must not concurrently tamper with that parent or staging tree.
SIGKILL or a cleanup failure can leave a private staging directory. Never sweep
staging names: another run may own them. A failure after rename (e.g. parent
fsync) leaves the complete bundle in place and reports STOP; it must not be
deleted or overwritten on retry. This is atomic visibility, not a guarantee
against filesystem, hardware or power-loss failures.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import html
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import urllib.parse
import uuid

BUILDER_PATH = Path(__file__).with_name("pp-build.py")
spec = importlib.util.spec_from_file_location("pp_build_family", BUILDER_PATH)
pp = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pp
assert spec.loader is not None
spec.loader.exec_module(pp)

META = '<meta name="deepwork-subscription" content="__SUBSCRIPTION_URL__">'
HEADING = '<h1>Из Лисьей Бухты<br>с Любовью</h1>'


def _rename_noreplace(parent_fd: int, source: str, destination: str) -> None:
    """One commit point; an existence check followed by os.rename is unsafe."""
    if sys.platform != "linux":
        raise OSError(errno.ENOTSUP, "FAMILY_ATOMIC_RENAME_UNAVAILABLE")
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, "renameat2", None)
    if rename is None:
        raise OSError(errno.ENOTSUP, "FAMILY_ATOMIC_RENAME_UNAVAILABLE")
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(parent_fd, os.fsencode(source), parent_fd, os.fsencode(destination), 1) != 0:
        raise OSError(ctypes.get_errno(), "FAMILY_ATOMIC_PUBLISH_FAILED")


def _verify_bundle(staging: Path, files: dict[Path, str]) -> None:
    """Check exact inventory, bytes, types and permissions before publication."""
    directories = {Path("."), Path("public"), Path("public/page"), Path("public/sub")}
    seen: set[Path] = set()
    for root, dirs, names in os.walk(staging, followlinks=False):
        for path in [Path(root), *(Path(root) / name for name in dirs + names)]:
            relative = path.relative_to(staging)
            info = path.lstat()
            if relative in directories:
                valid = stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
            else:
                valid = (relative in files and stat.S_ISREG(info.st_mode)
                         and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1)
                if valid:
                    valid = path.read_bytes() == files[relative].encode("utf-8")
            if not valid:
                raise ValueError("FAMILY_STAGING_INVALID")
            seen.add(relative)
    if seen != directories | files.keys():
        raise ValueError("FAMILY_STAGING_INVALID")


def _sync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _publish_bundle(output: Path, files: dict[Path, str]) -> None:
    """Build under a private sibling; clean only the directory we created."""
    if sys.platform != "linux" or not shutil.rmtree.avoids_symlink_attacks:
        raise OSError(errno.ENOTSUP, "FAMILY_ATOMIC_PLATFORM_UNSUPPORTED")
    parent_fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    staging = None
    identity = None
    published = False
    try:
        parent = os.fstat(parent_fd)
        if parent.st_uid != os.geteuid() or parent.st_mode & 0o022:
            raise ValueError("FAMILY_OUTPUT_PARENT_UNSAFE")
        # Test directory fsync support before the commit point as well.
        os.fsync(parent_fd)
        staging = Path(tempfile.mkdtemp(prefix=".lilfox-bundle-", dir=output.parent))
        info = staging.lstat()
        identity = (info.st_dev, info.st_ino)
        for relative in ("public", "public/page", "public/sub"):
            (staging / relative).mkdir(mode=0o700)
        for relative, text in files.items():
            pp.write_private(staging / relative, text)
        _verify_bundle(staging, files)
        for relative in ("public/page", "public/sub", "public", "."):
            _sync_dir(staging / relative)
        _rename_noreplace(parent_fd, staging.name, output.name)
        published = True
        os.fsync(parent_fd)
    finally:
        try:
            if staging is not None and identity is not None and not published:
                try:
                    info = os.stat(staging.name, dir_fd=parent_fd, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    if stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == identity:
                        shutil.rmtree(staging.name, dir_fd=parent_fd)
        finally:
            os.close(parent_fd)


def _private_path(path: Path, *, input_file: bool = False) -> Path:
    resolved = path.expanduser().resolve()
    repo = Path(__file__).resolve().parents[1]
    if resolved.is_relative_to(repo) or any((parent / ".git").exists() for parent in (resolved, *resolved.parents)):
        raise ValueError("FAMILY_PRIVATE_PATH_IN_GIT")
    if input_file and (not resolved.is_file() or stat.S_IMODE(resolved.stat().st_mode) & 0o077):
        raise ValueError("FAMILY_INPUT_NOT_PRIVATE")
    return resolved


def _public_base(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.port not in (None, 443, 9443) or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ValueError("FAMILY_PUBLIC_BASE_INVALID")
    return urllib.parse.urlunsplit(("https", parsed.netloc.lower(), "", "", ""))


def build_bundle(raw: dict, template: str, output: Path) -> None:
    # Reject links before _private_path resolves them, including dangling links.
    candidate = output.expanduser()
    if candidate.is_symlink():
        raise ValueError("FAMILY_OUTPUT_EXISTS")
    # Resolve only the parent: resolving the leaf would follow a racing link.
    output = _private_path(candidate.parent) / candidate.name
    if output.exists():
        raise ValueError("FAMILY_OUTPUT_EXISTS")
    if template.count(META) != 1 or template.count(HEADING) != 1:
        raise ValueError("FAMILY_TEMPLATE_UNEXPECTED")
    if "!SUBSCRIPTION_URL.includes('__SUBSCRIPTION_URL__')" not in template:
        raise ValueError("FAMILY_TEMPLATE_GUARD_MISSING")
    base = _public_base(str(raw["public_base"]))
    host, cover = pp.validate_host(str(raw["host"])), pp.validate_cover_hostname(str(raw["cover_hostname"]))
    values = raw["ports"]
    keys = {"route_i_tcp", "route_ii_tcp", "route_iii_udp"}
    if (not isinstance(values, dict) or set(values) != keys
            or any(type(values[k]) is not int or not 1 <= values[k] <= 65535 for k in keys)
            or values["route_i_tcp"] == values["route_ii_tcp"]):
        raise ValueError("FAMILY_PORTS_INVALID")
    ports = pp.Ports(**values)
    recipients = raw["recipients"]
    if not isinstance(recipients, list) or not recipients:
        raise ValueError("FAMILY_RECIPIENT_COUNT_INVALID")
    names, slugs = set(), set()
    all_tokens: set[str] = set()
    all_auth: set[str] = set()
    all_short_ids: set[str] = set()
    rendered: list[tuple[str, str, str, str, str]] = []
    for entry in recipients:
        if not isinstance(entry, dict):
            raise ValueError("FAMILY_RECIPIENT_INVALID")
        name, slug = entry.get("name"), entry.get("slug")
        if (not isinstance(name, str) or not name.strip() or name != name.strip()
                or len(name) > 100 or any(ord(c) < 32 or ord(c) == 127 for c in name)
                or name.casefold() in names):
            raise ValueError("FAMILY_RECIPIENT_NAME_INVALID")
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{1,31}", slug) or slug in slugs:
            raise ValueError("FAMILY_RECIPIENT_SLUG_INVALID")
        names.add(name.casefold()); slugs.add(slug)
        tokens = (str(entry["page_token"]), str(entry["subscription_token"]))
        if len(set(tokens)) != 2 or any(not re.fullmatch(r"[0-9a-f]{48,96}", token) or token in all_tokens for token in tokens):
            raise ValueError("FAMILY_TOKEN_INVALID")
        all_tokens.update(tokens)
        routes = entry["routes"]
        if set(routes) != {r.value for r in pp.Route}:
            raise ValueError("FAMILY_ROUTE_SET_INVALID")
        lines = []
        for route in pp.Route:
            material = pp.RouteMaterial.from_mapping(routes[route.value])
            if material.route is not route:
                raise ValueError("FAMILY_ROUTE_MATERIAL_MISMATCH")
            material.validate()
            credential = str(uuid.UUID(material.uuid)) if route is not pp.Route.III else material.auth
            if credential in all_auth:
                raise ValueError("FAMILY_CREDENTIAL_DUPLICATE")
            all_auth.add(credential)
            if route is not pp.Route.III:
                if material.short_id.lower() in all_short_ids:
                    raise ValueError("FAMILY_SHORT_ID_DUPLICATE")
                all_short_ids.add(material.short_id.lower())
            if route is pp.Route.III and not material.auth.startswith(slug + ":"):
                raise ValueError("FAMILY_HYSTERIA_USER_MISMATCH")
            label = f"🇯🇲 Доброе 🌞 Утро {route.value}"
            lines.append(pp.render_share_uri(route, host, ports.for_route(route), material, cover, name,
                                             label_override=label))
        page_url = f"{base}/page/{tokens[0]}.html"
        sub_url = f"{base}/sub/{tokens[1]}.txt"
        page = template.replace(META, f'<meta name="deepwork-subscription" content="{html.escape(sub_url, quote=True)}">', 1)
        page = page.replace(HEADING, HEADING + f'\n  <div class="brand">{html.escape(name)}</div>', 1)
        if page.count("__SUBSCRIPTION_URL__") != template.count("__SUBSCRIPTION_URL__") - 1:
            raise ValueError("FAMILY_TEMPLATE_GUARD_CHANGED")
        rendered.append((name, page_url, sub_url, page, "\n".join(lines) + "\n"))
    files: dict[Path, str] = {}
    for name, page_url, sub_url, page, subscription in rendered:
        page_name = page_url.rsplit("/", 1)[-1]
        sub_name = sub_url.rsplit("/", 1)[-1]
        files[Path("public/page") / page_name] = page
        files[Path("public/sub") / sub_name] = subscription
    files[Path("private-delivery.txt")] = (
        "\n".join(f"{name} — {page_url} — {sub_url}" for name, page_url, sub_url, _, _ in rendered) + "\n")
    files[Path("public/_headers")] = "/*\n  Referrer-Policy: no-referrer\n  X-Robots-Tag: noindex, nofollow\n/sub/*\n  Cache-Control: no-store\n  Content-Type: text/plain; charset=utf-8\n  profile-title: DeepWork AILab\n/page/*\n  Cache-Control: no-store\n"
    files[Path("public/404.html")] = '<!doctype html><meta charset="utf-8"><title>404</title><p>Страница не найдена.</p>\n'
    _publish_bundle(output, files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--material-json", required=True, type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        source = _private_path(args.material_json, input_file=True)
        raw = json.loads(source.read_text(encoding="utf-8"))
        template = args.template.read_text(encoding="utf-8")
        build_bundle(raw, template, args.output)
    except (OSError, ValueError, KeyError, TypeError, pp.BuilderStop):
        print("FAMILY_BUNDLE=STOP")
        return 2
    print("FAMILY_BUNDLE=READY_PRIVATE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
