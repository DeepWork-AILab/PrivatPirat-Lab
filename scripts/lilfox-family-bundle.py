"""Build private Happ subscriptions and approved personal pages outside Git.

Input is a protected JSON file created after recipient provisioning. This tool
never prints credentials or URLs. Publish only output/public/, never output/.
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
from pathlib import Path
import re
import stat
import sys
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
    output = _private_path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("FAMILY_OUTPUT_NOT_EMPTY")
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
    pp.ensure_private_dir(output)
    public = output / "public"
    pp.ensure_private_dir(public)
    pp.ensure_private_dir(public / "page")
    pp.ensure_private_dir(public / "sub")
    for name, page_url, sub_url, page, subscription in rendered:
        page_name = page_url.rsplit("/", 1)[-1]
        sub_name = sub_url.rsplit("/", 1)[-1]
        pp.write_private(public / "page" / page_name, page)
        pp.write_private(public / "sub" / sub_name, subscription)
    pp.write_private(output / "private-delivery.txt",
                     "\n".join(f"{name} — {page_url} — {sub_url}" for name, page_url, sub_url, _, _ in rendered) + "\n")
    pp.write_private(public / "_headers", "/*\n  Referrer-Policy: no-referrer\n  X-Robots-Tag: noindex, nofollow\n/sub/*\n  Cache-Control: no-store\n  Content-Type: text/plain; charset=utf-8\n  profile-title: DeepWork AILab\n/page/*\n  Cache-Control: no-store\n")
    pp.write_private(public / "404.html", '<!doctype html><meta charset="utf-8"><title>404</title><p>Страница не найдена.</p>\n')


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
