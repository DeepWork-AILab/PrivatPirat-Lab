#!/usr/bin/env python3
"""PrivatPirat Reproducible Node Builder v0.1.

R3-CODE-2 checkpoint: deployment stages, rollback, server verification and
client data-path verification are implemented, but the public CLI --apply
entrypoint remains deliberately disabled until a separate R3-SERVER gate.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import ipaddress
import json
import os
import platform
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.parse
import urllib.request
import uuid
import zipfile
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping, Protocol, Sequence

BUILDER_VERSION = "0.1.0-r3-code-2"
SUPPORTED_OS = ("ubuntu", "24.04", "x86_64")
MIN_MEMORY_KIB = 512 * 1024
MIN_ROOT_FREE_KIB = 1024 * 1024
PORT_MIN, PORT_MAX = 20000, 60000
XRAY_VERSION = "26.3.27"
HYSTERIA_VERSION = "2.12.1"
REMOTE_ROOT = "/var/lib/privatpirat-builder"
XRAY_INSTALL = f"/usr/local/lib/privatpirat/xray-{XRAY_VERSION}/xray"
HYSTERIA_INSTALL = f"/usr/local/lib/privatpirat/hysteria-{HYSTERIA_VERSION}/hysteria"

HTTP_PROBE_URL = "http://example.com/"
HTTPS_PROBE_URL = "https://example.com/"
EXIT_IP_URLS = ("https://api.ipify.org", "https://icanhazip.com")


@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    url: str
    sha256: str
    archive_member: str | None = None


ARTIFACTS: Mapping[str, ArtifactSpec] = {
    "xray-linux-amd64": ArtifactSpec(
        "Xray-linux-64.zip",
        f"https://github.com/XTLS/Xray-core/releases/download/v{XRAY_VERSION}/Xray-linux-64.zip",
        "23cd9af937744d97776ee35ecad4972cf4b2109d1e0fe6be9930467608f7c8ae",
        "xray",
    ),
    "xray-android-arm64": ArtifactSpec(
        "Xray-android-arm64-v8a.zip",
        f"https://github.com/XTLS/Xray-core/releases/download/v{XRAY_VERSION}/Xray-android-arm64-v8a.zip",
        "57149ffd48b629c07bf76938e73ab2729fde5910091497eab3e93d1c190f4c1b",
        "xray",
    ),
    "hysteria-linux-amd64": ArtifactSpec(
        "hysteria-linux-amd64",
        f"https://github.com/HyNetworks/hysteria/releases/download/app/v{HYSTERIA_VERSION}/hysteria-linux-amd64",
        "ffc032c7ca6b78676d337097ca7f61bebc3a90a4f3a656693adf368f304cdbc7",
    ),
    "hysteria-android-arm64": ArtifactSpec(
        "hysteria-android-arm64",
        f"https://github.com/HyNetworks/hysteria/releases/download/app/v{HYSTERIA_VERSION}/hysteria-android-arm64",
        "92728ca71dee10508040939c0c99e69f8800519fcedb6ec35eed92b90f1b2a5f",
    ),
}
# Backward-compatible public checksum view used by existing tests/tooling.
ARTIFACT_SHA256 = {spec.name: spec.sha256 for spec in ARTIFACTS.values()}


class BuilderStop(RuntimeError):
    pass


class Route(str, Enum):
    I = "I"
    II = "II"
    III = "III"


class State(str, Enum):
    NEW = "NEW"
    PREFLIGHT_PASS = "PREFLIGHT_PASS"
    I_APPLYING = "I_APPLYING"
    I_PASS = "I_PASS"
    II_APPLYING = "II_APPLYING"
    REGRESSION_I_PASS = "REGRESSION_I_PASS"
    II_PASS = "II_PASS"
    III_APPLYING = "III_APPLYING"
    III_PASS = "III_PASS"
    FINAL_REGRESSION_PASS = "FINAL_REGRESSION_PASS"
    CLIENT_BUNDLE_READY = "CLIENT_BUNDLE_READY"
    PASS = "PASS"
    STAGE_FAIL = "STAGE_FAIL"
    ROLLED_BACK = "ROLLED_BACK"
    STOPPED = "STOPPED"


TRANSITIONS: Mapping[State, set[State]] = {
    State.NEW: {State.PREFLIGHT_PASS, State.STOPPED},
    State.PREFLIGHT_PASS: {State.I_APPLYING, State.STOPPED},
    State.I_APPLYING: {State.I_PASS, State.STAGE_FAIL},
    State.I_PASS: {State.II_APPLYING, State.STOPPED},
    State.II_APPLYING: {State.REGRESSION_I_PASS, State.STAGE_FAIL},
    State.REGRESSION_I_PASS: {State.II_PASS, State.STAGE_FAIL},
    State.II_PASS: {State.III_APPLYING, State.STOPPED},
    State.III_APPLYING: {State.III_PASS, State.STAGE_FAIL},
    State.III_PASS: {State.FINAL_REGRESSION_PASS, State.STAGE_FAIL},
    State.FINAL_REGRESSION_PASS: {State.CLIENT_BUNDLE_READY, State.STOPPED},
    State.CLIENT_BUNDLE_READY: {State.PASS, State.STOPPED},
    State.STAGE_FAIL: {State.ROLLED_BACK, State.STOPPED},
    State.ROLLED_BACK: {State.STOPPED},
    State.PASS: set(),
    State.STOPPED: set(),
}

PUBLIC_FIELDS = frozenset({
    "builder_version", "phase", "host_key_match", "os_supported",
    "arch_supported", "resources_supported", "clean_room", "firewall_clear",
    "egress_consistent", "route_i", "route_ii", "route_iii", "regression",
    "client_bundle", "verdict", "error",
})


@dataclass(frozen=True)
class Inventory:
    os_id: str
    os_version: str
    arch: str
    uid: int
    cpu_count: int
    mem_kib: int
    root_free_kib: int
    systemd: bool
    ss: bool
    openssl: bool
    sha256sum: bool
    python3: bool
    ufw_state: str
    nft_nonempty: bool
    relevant_found: bool
    listen_tcp: frozenset[int]
    listen_udp: frozenset[int]
    egress_a: str
    egress_b: str

    @property
    def egress_ip(self) -> str:
        if self.egress_a != self.egress_b:
            raise BuilderStop("EGRESS_IP_MISMATCH=STOP")
        try:
            return str(ipaddress.ip_address(self.egress_a))
        except ValueError as exc:
            raise BuilderStop("EGRESS_IP_INVALID=STOP") from exc


@dataclass(frozen=True)
class Ports:
    route_i_tcp: int
    route_ii_tcp: int
    route_iii_udp: int

    def for_route(self, route: Route) -> int:
        return {
            Route.I: self.route_i_tcp,
            Route.II: self.route_ii_tcp,
            Route.III: self.route_iii_udp,
        }[route]


@dataclass(frozen=True)
class RemoteSession:
    host: str
    user: str
    port: int
    known_hosts: Path


@dataclass(frozen=True)
class RuntimePrivateInput:
    profile_name: str
    cover_hostname: str


@dataclass(frozen=True)
class PreflightContext:
    profile_name: str
    slug: str
    session: RemoteSession
    inventory: Inventory
    ports: Ports
    private_dir: Path
    state_dir: Path
    checks: Mapping[str, bool]


@dataclass(frozen=True)
class RouteMaterial:
    route: Route
    uuid: str | None = None
    public_key: str | None = None
    short_id: str | None = None
    xhttp_path: str | None = None
    auth: str | None = None
    pin_sha256: str | None = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "RouteMaterial":
        try:
            route = Route(str(values["route"]))
        except (KeyError, ValueError) as exc:
            raise BuilderStop("CLIENT_MATERIAL_ROUTE_INVALID=STOP") from exc
        allowed = {"route", "uuid", "public_key", "short_id", "xhttp_path", "auth", "pin_sha256"}
        if set(values) - allowed:
            raise BuilderStop("CLIENT_MATERIAL_UNKNOWN_FIELD=STOP")
        material = cls(
            route=route,
            uuid=_optional_text(values.get("uuid")),
            public_key=_optional_text(values.get("public_key")),
            short_id=_optional_text(values.get("short_id")),
            xhttp_path=_optional_text(values.get("xhttp_path")),
            auth=_optional_text(values.get("auth")),
            pin_sha256=_optional_text(values.get("pin_sha256")),
        )
        material.validate()
        return material

    def validate(self) -> None:
        if self.route in {Route.I, Route.II}:
            if not self.uuid or not self.public_key or not self.short_id:
                raise BuilderStop("XRAY_CLIENT_MATERIAL_INCOMPLETE=STOP")
            try:
                uuid.UUID(self.uuid)
            except ValueError as exc:
                raise BuilderStop("XRAY_UUID_INVALID=STOP") from exc
            if not re.fullmatch(r"[A-Za-z0-9_-]{43}", self.public_key):
                raise BuilderStop("REALITY_PUBLIC_KEY_INVALID=STOP")
            if not re.fullmatch(r"[0-9a-fA-F]{2,16}", self.short_id) or len(self.short_id) % 2:
                raise BuilderStop("REALITY_SHORT_ID_INVALID=STOP")
            if self.route is Route.II:
                if not self.xhttp_path or not re.fullmatch(r"/[A-Za-z0-9._~-]{8,80}", self.xhttp_path):
                    raise BuilderStop("XHTTP_PATH_INVALID=STOP")
            elif self.xhttp_path is not None:
                raise BuilderStop("ROUTE_I_XHTTP_PATH_UNEXPECTED=STOP")
        else:
            if not self.auth or not re.fullmatch(r"[0-9a-f]{32,128}", self.auth):
                raise BuilderStop("HYSTERIA_AUTH_INVALID=STOP")
            if not self.pin_sha256 or not re.fullmatch(r"[0-9a-fA-F]{64}", self.pin_sha256):
                raise BuilderStop("HYSTERIA_PIN_INVALID=STOP")


INVENTORY_SCRIPT = r'''set -eu
. /etc/os-release
has() { command -v "$1" >/dev/null 2>&1 && printf 1 || printf 0; }
printf 'OS_ID=%s\n' "${ID:-unknown}"
printf 'OS_VERSION=%s\n' "${VERSION_ID:-unknown}"
printf 'ARCH=%s\n' "$(uname -m)"
printf 'UID=%s\n' "$(id -u)"
printf 'CPU_COUNT=%s\n' "$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf 0)"
printf 'MEM_KIB=%s\n' "$(awk '/^MemTotal:/ {print $2; exit}' /proc/meminfo)"
printf 'ROOT_FREE_KIB=%s\n' "$(df -Pk / | awk 'NR==2 {print $4}')"
printf 'SYSTEMD=%s\n' "$(has systemctl)"
printf 'SS=%s\n' "$(has ss)"
printf 'OPENSSL=%s\n' "$(has openssl)"
printf 'SHA256SUM=%s\n' "$(has sha256sum)"
printf 'PYTHON3=%s\n' "$(has python3)"
if command -v ufw >/dev/null 2>&1; then
  u="$(ufw status 2>/dev/null | sed -n '1p' || true)"
  case "$u" in *inactive*) u=inactive;; *active*) u=active;; *) u=unknown;; esac
else u=absent; fi
printf 'UFW_STATE=%s\n' "$u"
if command -v nft >/dev/null 2>&1 && [ -n "$(nft list ruleset 2>/dev/null | sed '/^[[:space:]]*$/d' | head -n1 || true)" ]; then
  printf 'NFT_NONEMPTY=1\n'
else printf 'NFT_NONEMPTY=0\n'; fi
r=0
for b in xray hysteria hysteria2; do command -v "$b" >/dev/null 2>&1 && r=1 || true; done
for d in /etc/xray /usr/local/etc/xray /etc/hysteria /etc/hysteria2 /etc/privatpirat /usr/local/lib/privatpirat /var/lib/privatpirat-builder; do [ -e "$d" ] && r=1 || true; done
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files --no-legend --no-pager 2>/dev/null | grep -Eiq '(xray|hysteria|privatpirat|pp-lab-)'; then r=1; fi
printf 'RELEVANT_FOUND=%s\n' "$r"
if command -v ss >/dev/null 2>&1; then
  tcp="$(ss -H -ltn 2>/dev/null | awk '{print $4}' | sed -E 's/.*:([0-9]+)$/\1/' | grep -E '^[0-9]+$' | sort -nu | paste -sd, - || true)"
  udp="$(ss -H -lun 2>/dev/null | awk '{print $4}' | sed -E 's/.*:([0-9]+)$/\1/' | grep -E '^[0-9]+$' | sort -nu | paste -sd, - || true)"
else tcp=""; udp=""; fi
printf 'LISTEN_TCP=%s\n' "$tcp"
printf 'LISTEN_UDP=%s\n' "$udp"
egress() { python3 - "$1" <<'__PP_EGRESS_PY__' 2>/dev/null || true
import ipaddress, sys, urllib.request
req = urllib.request.Request(sys.argv[1], headers={"User-Agent":"PrivatPirat-Builder/0.1"})
with urllib.request.urlopen(req, timeout=8) as r:
    value = r.read(128).decode().strip()
print(ipaddress.ip_address(value))
__PP_EGRESS_PY__
}
if command -v python3 >/dev/null 2>&1; then
  printf 'EGRESS_A=%s\n' "$(egress https://api.ipify.org)"
  printf 'EGRESS_B=%s\n' "$(egress https://icanhazip.com)"
else
  printf 'EGRESS_A=\nEGRESS_B=\n'
fi
'''


def _optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise BuilderStop("CLIENT_MATERIAL_VALUE_INVALID=STOP")
    return value


def slugify(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("display name must not be empty")
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return (slug or "node-" + hashlib.sha256(value.encode()).hexdigest()[:10])[:48].rstrip("-")


def sanitize_error(message: str | None) -> str:
    safe = str(message or "unknown error")
    safe = safe.replace(str(Path.home()), "%HOME%")
    safe = re.sub(r"(?i)\b(?:https?|vless|hysteria2?)://\S+", "[URI REDACTED]", safe)
    safe = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP REDACTED]", safe)
    safe = re.sub(r"(?i)(?<![0-9a-f:])(?:[0-9a-f]{1,4}:){2,7}[0-9a-f:]{0,4}(?![0-9a-f:])", "[IP REDACTED]", safe)
    safe = re.sub(r"\b[0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\b", "[UUID REDACTED]", safe)
    safe = re.sub(r"\b[A-Za-z0-9_+/=-]{32,}\b", "[TOKEN REDACTED]", safe)
    return re.sub(r"[\r\n]+", " ", safe).strip()[:240]


def public_report(values: Mapping[str, object]) -> dict[str, object]:
    if set(values) - PUBLIC_FIELDS:
        raise ValueError("public report contains non-allowlisted fields")
    result = dict(values)
    if result.get("error") is not None:
        result["error"] = sanitize_error(str(result["error"]))
    return result


def transition(current: State, target: State) -> State:
    if target not in TRANSITIONS[current]:
        raise BuilderStop(f"STATE_TRANSITION_INVALID={current.value}->{target.value}")
    return target


def private_root() -> Path:
    return Path(os.environ.get("PRIVATPIRAT_BUILDER_PRIVATE_ROOT", Path.home() / "deepwork-mobile/private/privatpirat-builder")).expanduser()


def state_root() -> Path:
    return Path(os.environ.get("PRIVATPIRAT_BUILDER_STATE_ROOT", Path.home() / ".local/state/privatpirat-builder")).expanduser()


def cache_root() -> Path:
    return Path(os.environ.get("PRIVATPIRAT_BUILDER_CACHE_ROOT", Path.home() / ".cache/privatpirat-builder")).expanduser()


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


def write_private(path: Path, text: str) -> None:
    ensure_private_dir(path.parent)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def verify_sha256(path: Path, expected: str) -> bool:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return secrets.compare_digest(digest.hexdigest(), expected.lower())


def parse_ports(value: str) -> frozenset[int]:
    return frozenset(int(x) for x in value.split(",") if x.isdigit() and 1 <= int(x) <= 65535)


def parse_inventory(text: str) -> Inventory:
    values = dict(line.split("=", 1) for line in text.splitlines() if re.fullmatch(r"[A-Z0-9_]+=.*", line))
    required = {
        "OS_ID", "OS_VERSION", "ARCH", "UID", "CPU_COUNT", "MEM_KIB", "ROOT_FREE_KIB",
        "SYSTEMD", "SS", "OPENSSL", "SHA256SUM", "PYTHON3", "UFW_STATE", "NFT_NONEMPTY",
        "RELEVANT_FOUND", "LISTEN_TCP", "LISTEN_UDP", "EGRESS_A", "EGRESS_B",
    }
    if required - values.keys():
        raise BuilderStop("INVENTORY_MISSING_FIELDS=STOP")
    try:
        return Inventory(
            values["OS_ID"].lower(), values["OS_VERSION"], values["ARCH"], int(values["UID"]),
            int(values["CPU_COUNT"]), int(values["MEM_KIB"]), int(values["ROOT_FREE_KIB"]),
            values["SYSTEMD"] == "1", values["SS"] == "1", values["OPENSSL"] == "1",
            values["SHA256SUM"] == "1", values["PYTHON3"] == "1", values["UFW_STATE"],
            values["NFT_NONEMPTY"] == "1", values["RELEVANT_FOUND"] == "1",
            parse_ports(values["LISTEN_TCP"]), parse_ports(values["LISTEN_UDP"]),
            values["EGRESS_A"], values["EGRESS_B"],
        )
    except ValueError as exc:
        raise BuilderStop("INVENTORY_PARSE_FAIL=STOP") from exc


def evaluate_inventory(inv: Inventory) -> dict[str, bool]:
    os_ok = (inv.os_id, inv.os_version) == SUPPORTED_OS[:2]
    arch_ok = inv.arch == SUPPORTED_OS[2]
    resources_ok = inv.cpu_count >= 1 and inv.mem_kib >= MIN_MEMORY_KIB and inv.root_free_kib >= MIN_ROOT_FREE_KIB
    clean = inv.uid == 0 and inv.systemd and inv.ss and inv.openssl and inv.sha256sum and inv.python3 and not inv.relevant_found
    firewall = inv.ufw_state in {"absent", "inactive"} and not inv.nft_nonempty
    try:
        egress = bool(inv.egress_ip)
    except BuilderStop:
        egress = False
    return {
        "os_supported": os_ok,
        "arch_supported": arch_ok,
        "resources_supported": resources_ok,
        "clean_room": clean,
        "firewall_clear": firewall,
        "egress_consistent": egress,
    }


def assert_inventory(inv: Inventory) -> dict[str, bool]:
    result = evaluate_inventory(inv)
    if not all(result.values()):
        raise BuilderStop("PRECHECK_UNSUPPORTED_OR_NOT_CLEAN=STOP")
    return result


def select_ports(inv: Inventory) -> Ports:
    used = set(inv.listen_tcp) | set(inv.listen_udp)
    chosen: list[int] = []
    for _ in range(1000):
        p = secrets.randbelow(PORT_MAX - PORT_MIN + 1) + PORT_MIN
        if p not in used and p not in chosen:
            chosen.append(p)
        if len(chosen) == 3:
            return Ports(*chosen)
    raise BuilderStop("FREE_PORT_SELECTION_FAIL=STOP")


def validate_host(host: str) -> str:
    host = host.strip()
    if not host or len(host) > 253 or any(c.isspace() for c in host):
        raise BuilderStop("TARGET_HOST_INVALID=STOP")
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    if not re.fullmatch(r"(?i)[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", host):
        raise BuilderStop("TARGET_HOST_INVALID=STOP")
    return host


def validate_cover_hostname(value: str) -> str:
    value = value.strip().rstrip(".").lower()
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        raise BuilderStop("REALITY_COVER_MUST_BE_HOSTNAME=STOP")
    if len(value) > 253 or "." not in value or not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])", value):
        raise BuilderStop("REALITY_COVER_INVALID=STOP")
    if any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-") for label in value.split(".")):
        raise BuilderStop("REALITY_COVER_INVALID=STOP")
    return value


def validate_user(user: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,31}", user.strip()):
        raise BuilderStop("SSH_USER_INVALID=STOP")
    return user.strip()


def validate_fingerprint(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"SHA256:[A-Za-z0-9+/]{43}=?", value):
        raise BuilderStop("HOST_KEY_FINGERPRINT_INVALID=STOP")
    return value


def _authority(host: str, port: int) -> str:
    host = validate_host(host)
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return f"{host}:{port}"
    return f"[{host}]:{port}" if ip.version == 6 else f"{host}:{port}"



def _scp_host(host: str) -> str:
    host = validate_host(host)
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host
    return f"[{host}]" if ip.version == 6 else host

def pin_host_key(host: str, port: int, expected: str, directory: Path) -> Path:
    host, expected = validate_host(host), validate_fingerprint(expected)
    ensure_private_dir(directory)
    candidate, known = directory / "known_hosts.candidate", directory / "known_hosts"
    try:
        scan = subprocess.run(["ssh-keyscan", "-T", "8", "-p", str(port), "-t", "ed25519", host], text=True, capture_output=True, timeout=12)
        if scan.returncode or not scan.stdout.strip():
            raise BuilderStop("HOST_KEY_SCAN_FAIL=STOP")
        write_private(candidate, scan.stdout)
        fp = subprocess.run(["ssh-keygen", "-lf", str(candidate)], text=True, capture_output=True, timeout=8)
        match = re.search(r"\b(SHA256:[A-Za-z0-9+/]{43}=?)\b", fp.stdout) if not fp.returncode else None
        if not match:
            raise BuilderStop("HOST_KEY_PARSE_FAIL=STOP")
        if not secrets.compare_digest(match.group(1), expected):
            raise BuilderStop("HOST_KEY_MISMATCH=STOP")
        write_private(known, scan.stdout)
        return known
    finally:
        try:
            candidate.unlink()
        except FileNotFoundError:
            pass


def _ssh_base(session: RemoteSession) -> list[str]:
    return [
        "ssh", "-T", "-p", str(session.port),
        "-o", "StrictHostKeyChecking=yes",
        "-o", f"UserKnownHostsFile={session.known_hosts}",
        "-o", "LogLevel=ERROR",
        f"{validate_user(session.user)}@{validate_host(session.host)}",
    ]


def remote_inventory(host: str, user: str, port: int, known_hosts: Path) -> Inventory:
    session = RemoteSession(validate_host(host), validate_user(user), port, known_hosts)
    try:
        proc = subprocess.run(_ssh_base(session) + ["sh", "-s"], input=INVENTORY_SCRIPT, text=True, capture_output=True, timeout=55)
    except subprocess.TimeoutExpired as exc:
        raise BuilderStop("SSH_INVENTORY_TIMEOUT=STOP") from exc
    if proc.returncode:
        raise BuilderStop("SSH_INVENTORY_FAIL=STOP")
    return parse_inventory(proc.stdout)


def remote_cover_probe(session: RemoteSession, cover_hostname: str) -> None:
    """Read-only TLS reachability probe for the private REALITY cover target."""
    cover = validate_cover_hostname(cover_hostname)
    payload = (
        "import socket, ssl\n"
        f"host = {json.dumps(cover)}\n"
        "ctx = ssl.create_default_context()\n"
        "with socket.create_connection((host, 443), timeout=8) as raw:\n"
        "    with ctx.wrap_socket(raw, server_hostname=host) as tls:\n"
        "        if not tls.version(): raise SystemExit(2)\n"
        "print('COVER_TLS=PASS')\n"
    )
    try:
        proc = subprocess.run(
            _ssh_base(session) + ["python3", "-"], input=payload, text=True,
            capture_output=True, timeout=15,
        )
    except subprocess.TimeoutExpired as exc:
        raise BuilderStop("REALITY_COVER_PROBE_TIMEOUT=STOP") from exc
    if proc.returncode or "COVER_TLS=PASS" not in proc.stdout.splitlines():
        raise BuilderStop("REALITY_COVER_TLS_UNREACHABLE=STOP")


def local_prerequisites() -> dict[str, bool]:
    result = {name: shutil.which(name) is not None for name in ("ssh", "scp", "ssh-keyscan", "ssh-keygen", "curl")}
    result["python"] = sys.version_info >= (3, 11)
    return result


def download_verified(spec: ArtifactSpec, directory: Path) -> Path:
    ensure_private_dir(directory)
    target = directory / spec.name
    if target.exists():
        if verify_sha256(target, spec.sha256):
            return target
        target.unlink()
    fd, tmp_name = tempfile.mkstemp(prefix=".download-", dir=directory)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        request = urllib.request.Request(spec.url, headers={"User-Agent": f"PrivatPirat-Builder/{BUILDER_VERSION}"})
        with urllib.request.urlopen(request, timeout=60) as response, tmp.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
        if not verify_sha256(tmp, spec.sha256):
            raise BuilderStop(f"ARTIFACT_SHA256_FAIL={spec.name}")
        os.replace(tmp, target)
        os.chmod(target, 0o600)
        return target
    except Exception:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


def extract_archive_member(archive: Path, member: str, target: Path) -> Path:
    ensure_private_dir(target.parent)
    with zipfile.ZipFile(archive) as zf:
        names = [name for name in zf.namelist() if Path(name).name == member and not name.endswith("/")]
        if len(names) != 1:
            raise BuilderStop("ARCHIVE_MEMBER_AMBIGUOUS_OR_MISSING=STOP")
        data = zf.read(names[0])
    fd, tmp_name = tempfile.mkstemp(prefix=".extract-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o700)
        os.replace(tmp_name, target)
        os.chmod(target, 0o700)
        return target
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def prepare_artifacts(directory: Path | None = None) -> dict[str, Path]:
    directory = directory or cache_root()
    arch = platform.machine().lower()
    androidish = bool(os.environ.get("ANDROID_ROOT")) or arch in {"aarch64", "arm64"}
    if arch in {"x86_64", "amd64"} and not os.environ.get("ANDROID_ROOT"):
        client_xray_key, client_hy_key = "xray-linux-amd64", "hysteria-linux-amd64"
    elif androidish:
        client_xray_key, client_hy_key = "xray-android-arm64", "hysteria-android-arm64"
    else:
        raise BuilderStop("LOCAL_CLIENT_ARCH_UNSUPPORTED=STOP")
    server_xray = download_verified(ARTIFACTS["xray-linux-amd64"], directory)
    server_hy = download_verified(ARTIFACTS["hysteria-linux-amd64"], directory)
    client_xray_archive = download_verified(ARTIFACTS[client_xray_key], directory)
    client_hy = download_verified(ARTIFACTS[client_hy_key], directory)
    client_xray = extract_archive_member(client_xray_archive, "xray", directory / "client-xray")
    os.chmod(client_hy, 0o700)
    return {
        "server_xray_archive": server_xray,
        "server_hysteria": server_hy,
        "client_xray": client_xray,
        "client_hysteria": client_hy,
    }


def render_xray_server_config(route: Route, port: int, material: RouteMaterial, cover_hostname: str, private_key: str) -> str:
    if route not in {Route.I, Route.II}:
        raise ValueError("xray route required")
    material.validate()
    cover = validate_cover_hostname(cover_hostname)
    client = {"id": material.uuid}
    if route is Route.I:
        client["flow"] = "xtls-rprx-vision"
    stream: dict[str, object] = {
        "network": "raw" if route is Route.I else "xhttp",
        "security": "reality",
        "realitySettings": {
            "show": False,
            "target": f"{cover}:443",
            "serverNames": [cover],
            "privateKey": private_key,
            "shortIds": [material.short_id],
        },
    }
    if route is Route.II:
        stream["xhttpSettings"] = {"path": material.xhttp_path, "mode": "auto"}
    cfg = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "listen": "0.0.0.0", "port": port, "protocol": "vless",
            "settings": {"clients": [client], "decryption": "none"},
            "streamSettings": stream,
        }],
        "outbounds": [{"protocol": "freedom", "tag": "direct"}],
    }
    return json.dumps(cfg, indent=2, sort_keys=True) + "\n"


def render_xray_client_config(route: Route, host: str, port: int, material: RouteMaterial, cover_hostname: str, socks_port: int) -> str:
    if route not in {Route.I, Route.II}:
        raise ValueError("xray route required")
    material.validate()
    cover = validate_cover_hostname(cover_hostname)
    user: dict[str, object] = {"id": material.uuid, "encryption": "none"}
    if route is Route.I:
        user["flow"] = "xtls-rprx-vision"
    stream: dict[str, object] = {
        "network": "raw" if route is Route.I else "xhttp",
        "security": "reality",
        "realitySettings": {
            "fingerprint": "firefox", "serverName": cover,
            "password": material.public_key, "shortId": material.short_id, "spiderX": "/",
        },
    }
    if route is Route.II:
        stream["xhttpSettings"] = {"path": material.xhttp_path, "mode": "auto"}
    cfg = {
        "log": {"loglevel": "warning"},
        "inbounds": [{"listen": "127.0.0.1", "port": socks_port, "protocol": "socks", "settings": {"udp": True}}],
        "outbounds": [{
            "tag": "proxy", "protocol": "vless",
            "settings": {"vnext": [{"address": validate_host(host), "port": port, "users": [user]}]},
            "streamSettings": stream,
        }],
    }
    return json.dumps(cfg, indent=2, sort_keys=True) + "\n"


def render_hysteria_server_config(port: int, auth: str, cert: str, key: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{32,128}", auth):
        raise BuilderStop("HYSTERIA_AUTH_INVALID=STOP")
    return (
        f"listen: :{port}\n"
        f"tls:\n  cert: {cert}\n  key: {key}\n"
        f"auth:\n  type: password\n  password: {auth}\n"
    )


def render_hysteria_client_config(host: str, port: int, material: RouteMaterial, socks_port: int) -> str:
    if material.route is not Route.III:
        raise ValueError("hysteria route required")
    material.validate()
    return (
        f"server: {_authority(host, port)}\n"
        f"auth: {material.auth}\n"
        "tls:\n  insecure: true\n"
        f"  pinSHA256: {material.pin_sha256}\n"
        f"socks5:\n  listen: 127.0.0.1:{socks_port}\n"
    )


def render_share_uri(route: Route, host: str, port: int, material: RouteMaterial, cover_hostname: str, profile_name: str) -> str:
    label = urllib.parse.quote(f"{profile_name}-{route.value}", safe="")
    authority = _authority(host, port)
    if route in {Route.I, Route.II}:
        material.validate()
        query = {
            "encryption": "none", "security": "reality", "sni": validate_cover_hostname(cover_hostname),
            "fp": "firefox", "pbk": material.public_key, "sid": material.short_id,
            "type": "tcp" if route is Route.I else "xhttp",
        }
        if route is Route.I:
            query["flow"] = "xtls-rprx-vision"
        else:
            query["path"] = material.xhttp_path
            query["mode"] = "auto"
        return f"vless://{material.uuid}@{authority}?{urllib.parse.urlencode(query)}#{label}"
    material.validate()
    query = urllib.parse.urlencode({"insecure": "1", "pinSHA256": material.pin_sha256})
    return f"hysteria2://{urllib.parse.quote(material.auth or '', safe='')}@{authority}/?{query}#{label}"


def _systemd_unit(user: str, exec_start: str) -> str:
    return f"""[Unit]
Description=PrivatPirat {user}
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
Group={user}
ExecStart={exec_start}
Restart=on-failure
RestartSec=2s
NoNewPrivileges=yes
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=strict
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes

[Install]
WantedBy=multi-user.target
"""


def stage_i_apply_script(port: int) -> str:
    archive = ARTIFACTS["xray-linux-amd64"]
    unit = _systemd_unit("pp-lab-i", f"{XRAY_INSTALL} run -config /etc/privatpirat/pp-lab-i/config.json")
    return f'''set -euo pipefail
ROOT={REMOTE_ROOT!r}
CFG=/etc/privatpirat/pp-lab-i/config.json
MAT="$ROOT/material-I.json"
XRAY={XRAY_INSTALL!r}
PORT={port}
rollback() {{ systemctl disable --now pp-lab-i.service >/dev/null 2>&1 || true; rm -f /etc/systemd/system/pp-lab-i.service; rm -rf /etc/privatpirat/pp-lab-i; userdel pp-lab-i >/dev/null 2>&1 || true; rm -rf /usr/local/lib/privatpirat/xray-{XRAY_VERSION}; rm -f "$MAT"; systemctl daemon-reload >/dev/null 2>&1 || true; }}
trap 'rollback' ERR HUP INT TERM
[ "$(id -u)" = 0 ]
[ -f "$ROOT/{archive.name}" ] && [ -f "$ROOT/runtime.json" ]
! id pp-lab-i >/dev/null 2>&1
[ ! -e /etc/privatpirat/pp-lab-i ] && [ ! -e /etc/systemd/system/pp-lab-i.service ]
! ss -H -ltn | awk '{{print $4}}' | grep -Eq ':{port}$'
printf '%s  %s\n' {archive.sha256!r} "$ROOT/{archive.name}" | sha256sum -c - >/dev/null
install -d -m 0755 /usr/local/lib/privatpirat/xray-{XRAY_VERSION}
python3 - "$ROOT/{archive.name}" "$XRAY" <<'__PP_XRAY_EXTRACT__'
import os, pathlib, sys, tempfile, zipfile
src, dst = sys.argv[1:]
with zipfile.ZipFile(src) as z:
    hits=[n for n in z.namelist() if pathlib.PurePosixPath(n).name == "xray" and not n.endswith("/")]
    if len(hits) != 1: raise SystemExit(31)
    data=z.read(hits[0])
fd,tmp=tempfile.mkstemp(dir=str(pathlib.Path(dst).parent), prefix=".xray-")
with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
os.chmod(tmp,0o755); os.replace(tmp,dst)
__PP_XRAY_EXTRACT__
useradd --system --user-group --home /nonexistent --shell /usr/sbin/nologin pp-lab-i
install -d -m 0750 -o root -g pp-lab-i /etc/privatpirat/pp-lab-i
umask 077
python3 - <<'__PP_UUID_I__' > "$ROOT/i.uuid"
import uuid
print(uuid.uuid4())
__PP_UUID_I__
"$XRAY" x25519 > "$ROOT/i.x25519"
openssl rand -hex 8 > "$ROOT/i.sid"
python3 - "$ROOT/runtime.json" "$ROOT/i.uuid" "$ROOT/i.x25519" "$ROOT/i.sid" "$CFG" "$MAT" "$PORT" <<'__PP_CONFIG_I__'
import json, pathlib, re, sys
runtime, uuidf, keyf, sidf, cfgf, matf, port = sys.argv[1:]
cover=json.load(open(runtime, encoding="utf-8"))["cover_hostname"]
uuidv=pathlib.Path(uuidf).read_text().strip(); sid=pathlib.Path(sidf).read_text().strip()
lines=pathlib.Path(keyf).read_text().splitlines()
private=next(x.split(": ",1)[1] for x in lines if x.startswith("PrivateKey: "))
public=next(x.split(": ",1)[1] for x in lines if x.startswith("Password (PublicKey): "))
client={{"id":uuidv,"flow":"xtls-rprx-vision"}}
cfg={{"log":{{"loglevel":"warning"}},"inbounds":[{{"listen":"0.0.0.0","port":int(port),"protocol":"vless","settings":{{"clients":[client],"decryption":"none"}},"streamSettings":{{"network":"raw","security":"reality","realitySettings":{{"show":False,"target":cover+":443","serverNames":[cover],"privateKey":private,"shortIds":[sid]}}}}}}],"outbounds":[{{"protocol":"freedom","tag":"direct"}}]}}
pathlib.Path(cfgf).write_text(json.dumps(cfg,indent=2,sort_keys=True)+"\n")
pathlib.Path(matf).write_text(json.dumps({{"route":"I","uuid":uuidv,"public_key":public,"short_id":sid}})+"\n")
__PP_CONFIG_I__
chown root:pp-lab-i "$CFG" && chmod 0640 "$CFG" && chmod 0600 "$MAT"
rm -f "$ROOT/i.uuid" "$ROOT/i.x25519" "$ROOT/i.sid"
"$XRAY" run -test -config "$CFG" >/dev/null 2>&1
cat > /etc/systemd/system/pp-lab-i.service <<'__PP_UNIT_I__'
{unit}__PP_UNIT_I__
systemctl daemon-reload
systemctl enable --now pp-lab-i.service >/dev/null
for _ in $(seq 1 25); do systemctl is-active --quiet pp-lab-i.service && ss -H -ltn | awk '{{print $4}}' | grep -Eq ':{port}$' && break; sleep .2; done
systemctl is-active --quiet pp-lab-i.service
ss -H -ltn | awk '{{print $4}}' | grep -Eq ':{port}$'
trap - ERR HUP INT TERM
printf 'STAGE_I_APPLY=PASS\n'
'''


def stage_ii_apply_script(port: int) -> str:
    unit = _systemd_unit("pp-lab-ii", f"{XRAY_INSTALL} run -config /etc/privatpirat/pp-lab-ii/config.json")
    return f'''set -euo pipefail
ROOT={REMOTE_ROOT!r}
CFG=/etc/privatpirat/pp-lab-ii/config.json
MAT="$ROOT/material-II.json"
XRAY={XRAY_INSTALL!r}
PORT={port}
rollback() {{ systemctl disable --now pp-lab-ii.service >/dev/null 2>&1 || true; rm -f /etc/systemd/system/pp-lab-ii.service; rm -rf /etc/privatpirat/pp-lab-ii; userdel pp-lab-ii >/dev/null 2>&1 || true; rm -f "$MAT" "$ROOT/ii.uuid" "$ROOT/ii.x25519" "$ROOT/ii.sid" "$ROOT/ii.path"; systemctl daemon-reload >/dev/null 2>&1 || true; }}
trap 'rollback' ERR HUP INT TERM
[ -x "$XRAY" ] && [ -f "$ROOT/runtime.json" ]
systemctl is-active --quiet pp-lab-i.service
I_HASH_BEFORE="$(sha256sum /etc/privatpirat/pp-lab-i/config.json | awk '{{print $1}}')"
! id pp-lab-ii >/dev/null 2>&1
[ ! -e /etc/privatpirat/pp-lab-ii ] && [ ! -e /etc/systemd/system/pp-lab-ii.service ]
! ss -H -ltn | awk '{{print $4}}' | grep -Eq ':{port}$'
useradd --system --user-group --home /nonexistent --shell /usr/sbin/nologin pp-lab-ii
install -d -m 0750 -o root -g pp-lab-ii /etc/privatpirat/pp-lab-ii
umask 077
python3 - <<'__PP_UUID_II__' > "$ROOT/ii.uuid"
import uuid
print(uuid.uuid4())
__PP_UUID_II__
"$XRAY" x25519 > "$ROOT/ii.x25519"
openssl rand -hex 8 > "$ROOT/ii.sid"
printf '/%s\n' "$(openssl rand -hex 12)" > "$ROOT/ii.path"
python3 - "$ROOT/runtime.json" "$ROOT/ii.uuid" "$ROOT/ii.x25519" "$ROOT/ii.sid" "$ROOT/ii.path" "$CFG" "$MAT" "$PORT" <<'__PP_CONFIG_II__'
import json, pathlib, sys
runtime, uuidf, keyf, sidf, pathf, cfgf, matf, port = sys.argv[1:]
cover=json.load(open(runtime, encoding="utf-8"))["cover_hostname"]
uuidv=pathlib.Path(uuidf).read_text().strip(); sid=pathlib.Path(sidf).read_text().strip(); path=pathlib.Path(pathf).read_text().strip()
lines=pathlib.Path(keyf).read_text().splitlines()
private=next(x.split(": ",1)[1] for x in lines if x.startswith("PrivateKey: "))
public=next(x.split(": ",1)[1] for x in lines if x.startswith("Password (PublicKey): "))
cfg={{"log":{{"loglevel":"warning"}},"inbounds":[{{"listen":"0.0.0.0","port":int(port),"protocol":"vless","settings":{{"clients":[{{"id":uuidv}}],"decryption":"none"}},"streamSettings":{{"network":"xhttp","security":"reality","realitySettings":{{"show":False,"target":cover+":443","serverNames":[cover],"privateKey":private,"shortIds":[sid]}},"xhttpSettings":{{"path":path,"mode":"auto"}}}}}}],"outbounds":[{{"protocol":"freedom","tag":"direct"}}]}}
pathlib.Path(cfgf).write_text(json.dumps(cfg,indent=2,sort_keys=True)+"\n")
pathlib.Path(matf).write_text(json.dumps({{"route":"II","uuid":uuidv,"public_key":public,"short_id":sid,"xhttp_path":path}})+"\n")
__PP_CONFIG_II__
chown root:pp-lab-ii "$CFG" && chmod 0640 "$CFG" && chmod 0600 "$MAT"
rm -f "$ROOT/ii.uuid" "$ROOT/ii.x25519" "$ROOT/ii.sid" "$ROOT/ii.path"
"$XRAY" run -test -config "$CFG" >/dev/null 2>&1
cat > /etc/systemd/system/pp-lab-ii.service <<'__PP_UNIT_II__'
{unit}__PP_UNIT_II__
systemctl daemon-reload
systemctl enable --now pp-lab-ii.service >/dev/null
for _ in $(seq 1 25); do systemctl is-active --quiet pp-lab-ii.service && ss -H -ltn | awk '{{print $4}}' | grep -Eq ':{port}$' && break; sleep .2; done
systemctl is-active --quiet pp-lab-i.service
systemctl is-active --quiet pp-lab-ii.service
[ "$I_HASH_BEFORE" = "$(sha256sum /etc/privatpirat/pp-lab-i/config.json | awk '{{print $1}}')" ]
ss -H -ltn | awk '{{print $4}}' | grep -Eq ':{port}$'
trap - ERR HUP INT TERM
printf 'STAGE_II_APPLY=PASS\n'
'''


def stage_iii_apply_script(port: int) -> str:
    spec = ARTIFACTS["hysteria-linux-amd64"]
    unit = _systemd_unit("pp-lab-iii", f"{HYSTERIA_INSTALL} server -c /etc/privatpirat/pp-lab-iii/config.yaml")
    return f'''set -euo pipefail
ROOT={REMOTE_ROOT!r}
DIR=/etc/privatpirat/pp-lab-iii
CFG="$DIR/config.yaml"
MAT="$ROOT/material-III.json"
HY={HYSTERIA_INSTALL!r}
PORT={port}
rollback() {{ if [ -n "${{TEST_PID:-}}" ]; then kill "$TEST_PID" >/dev/null 2>&1 || true; fi; systemctl disable --now pp-lab-iii.service >/dev/null 2>&1 || true; rm -f /etc/systemd/system/pp-lab-iii.service; rm -rf "$DIR"; userdel pp-lab-iii >/dev/null 2>&1 || true; rm -rf /usr/local/lib/privatpirat/hysteria-{HYSTERIA_VERSION}; rm -f "$MAT" "$ROOT/{spec.name}" "$ROOT/iii.auth" "$ROOT/iii-validate.log"; systemctl daemon-reload >/dev/null 2>&1 || true; }}
trap 'rollback' ERR HUP INT TERM
systemctl is-active --quiet pp-lab-i.service
systemctl is-active --quiet pp-lab-ii.service
I_HASH_BEFORE="$(sha256sum /etc/privatpirat/pp-lab-i/config.json | awk '{{print $1}}')"
II_HASH_BEFORE="$(sha256sum /etc/privatpirat/pp-lab-ii/config.json | awk '{{print $1}}')"
[ -f "$ROOT/{spec.name}" ]
! id pp-lab-iii >/dev/null 2>&1
[ ! -e "$DIR" ] && [ ! -e /etc/systemd/system/pp-lab-iii.service ]
! ss -H -lun | awk '{{print $4}}' | grep -Eq ':{port}$'
printf '%s  %s\n' {spec.sha256!r} "$ROOT/{spec.name}" | sha256sum -c - >/dev/null
install -d -m 0755 /usr/local/lib/privatpirat/hysteria-{HYSTERIA_VERSION}
install -m 0755 "$ROOT/{spec.name}" "$HY"
useradd --system --user-group --home /nonexistent --shell /usr/sbin/nologin pp-lab-iii
install -d -m 0750 -o root -g pp-lab-iii "$DIR"
umask 077
openssl rand -hex 32 > "$ROOT/iii.auth"
openssl req -x509 -newkey rsa:2048 -sha256 -days 825 -nodes -subj '/CN=privatpirat.local' -keyout "$DIR/server.key" -out "$DIR/server.crt" >/dev/null 2>&1
AUTH="$(cat "$ROOT/iii.auth")"
cat > "$CFG" <<__PP_HY_CFG__
listen: :{port}
tls:
  cert: $DIR/server.crt
  key: $DIR/server.key
auth:
  type: password
  password: $AUTH
__PP_HY_CFG__
unset AUTH
chown root:pp-lab-iii "$CFG" "$DIR/server.crt" "$DIR/server.key"
chmod 0640 "$CFG" "$DIR/server.crt" "$DIR/server.key"
"$HY" server -c "$CFG" > "$ROOT/iii-validate.log" 2>&1 & TEST_PID=$!
SEEN=0
for _ in $(seq 1 30); do if ss -H -lun | awk '{{print $4}}' | grep -Eq ':{port}$'; then SEEN=1; break; fi; kill -0 "$TEST_PID" >/dev/null 2>&1 || break; sleep .2; done
kill "$TEST_PID" >/dev/null 2>&1 || true
wait "$TEST_PID" >/dev/null 2>&1 || true
[ "$SEEN" = 1 ]
rm -f "$ROOT/iii-validate.log"
PIN="$(openssl x509 -in "$DIR/server.crt" -outform DER | sha256sum | awk '{{print $1}}')"
python3 - "$ROOT/iii.auth" "$PIN" "$MAT" <<'__PP_MAT_III__'
import json, pathlib, sys
authf,pin,matf=sys.argv[1:]
auth=pathlib.Path(authf).read_text().strip()
pathlib.Path(matf).write_text(json.dumps({{"route":"III","auth":auth,"pin_sha256":pin}})+"\n")
__PP_MAT_III__
chmod 0600 "$MAT" && rm -f "$ROOT/iii.auth"
cat > /etc/systemd/system/pp-lab-iii.service <<'__PP_UNIT_III__'
{unit}__PP_UNIT_III__
systemctl daemon-reload
systemctl enable --now pp-lab-iii.service >/dev/null
for _ in $(seq 1 25); do systemctl is-active --quiet pp-lab-iii.service && ss -H -lun | awk '{{print $4}}' | grep -Eq ':{port}$' && break; sleep .2; done
systemctl is-active --quiet pp-lab-i.service
systemctl is-active --quiet pp-lab-ii.service
systemctl is-active --quiet pp-lab-iii.service
[ "$I_HASH_BEFORE" = "$(sha256sum /etc/privatpirat/pp-lab-i/config.json | awk '{{print $1}}')" ]
[ "$II_HASH_BEFORE" = "$(sha256sum /etc/privatpirat/pp-lab-ii/config.json | awk '{{print $1}}')" ]
ss -H -lun | awk '{{print $4}}' | grep -Eq ':{port}$'
trap - ERR HUP INT TERM
printf 'STAGE_III_APPLY=PASS\n'
'''


def server_verify_script(route: Route, port: int) -> str:
    unit = {Route.I: "pp-lab-i.service", Route.II: "pp-lab-ii.service", Route.III: "pp-lab-iii.service"}[route]
    socket_flag = "-ltn" if route in {Route.I, Route.II} else "-lun"
    prior = []
    if route in {Route.II, Route.III}:
        prior.append("systemctl is-active --quiet pp-lab-i.service")
    if route is Route.III:
        prior.append("systemctl is-active --quiet pp-lab-ii.service")
    prior_checks = "\n".join(prior)
    return f'''set -euo pipefail
UNIT={unit!r}
{prior_checks}
systemctl is-active --quiet "$UNIT"
ss -H {socket_flag} | awk '{{print $4}}' | grep -Eq ':{port}$'
systemctl restart "$UNIT"
for _ in $(seq 1 25); do systemctl is-active --quiet "$UNIT" && ss -H {socket_flag} | awk '{{print $4}}' | grep -Eq ':{port}$' && break; sleep .2; done
systemctl is-active --quiet "$UNIT"
ss -H {socket_flag} | awk '{{print $4}}' | grep -Eq ':{port}$'
systemctl stop "$UNIT"
! systemctl is-active --quiet "$UNIT"
{prior_checks}
systemctl start "$UNIT"
for _ in $(seq 1 25); do systemctl is-active --quiet "$UNIT" && ss -H {socket_flag} | awk '{{print $4}}' | grep -Eq ':{port}$' && break; sleep .2; done
systemctl is-active --quiet "$UNIT"
ss -H {socket_flag} | awk '{{print $4}}' | grep -Eq ':{port}$'
{prior_checks}
printf 'SERVER_VERIFY_{route.value}=PASS\n'
'''


def rollback_script(route: Route, port: int | None = None) -> str:
    if route is Route.I:
        body = f'''systemctl disable --now pp-lab-i.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/pp-lab-i.service
rm -rf /etc/privatpirat/pp-lab-i
userdel pp-lab-i >/dev/null 2>&1 || true
rm -rf /usr/local/lib/privatpirat/xray-{XRAY_VERSION}
rm -rf {REMOTE_ROOT}
systemctl daemon-reload >/dev/null 2>&1 || true
! id pp-lab-i >/dev/null 2>&1
[ ! -e /etc/privatpirat/pp-lab-i ] && [ ! -e /etc/systemd/system/pp-lab-i.service ]'''
    elif route is Route.II:
        body = f'''systemctl disable --now pp-lab-ii.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/pp-lab-ii.service
rm -rf /etc/privatpirat/pp-lab-ii
userdel pp-lab-ii >/dev/null 2>&1 || true
rm -f {REMOTE_ROOT}/material-II.json {REMOTE_ROOT}/ii.uuid {REMOTE_ROOT}/ii.x25519 {REMOTE_ROOT}/ii.sid {REMOTE_ROOT}/ii.path
systemctl daemon-reload >/dev/null 2>&1 || true
systemctl is-active --quiet pp-lab-i.service
! id pp-lab-ii >/dev/null 2>&1
[ ! -e /etc/privatpirat/pp-lab-ii ] && [ ! -e /etc/systemd/system/pp-lab-ii.service ]'''
    else:
        body = f'''systemctl disable --now pp-lab-iii.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/pp-lab-iii.service
rm -rf /etc/privatpirat/pp-lab-iii
userdel pp-lab-iii >/dev/null 2>&1 || true
rm -rf /usr/local/lib/privatpirat/hysteria-{HYSTERIA_VERSION}
rm -f {REMOTE_ROOT}/material-III.json {REMOTE_ROOT}/{ARTIFACTS["hysteria-linux-amd64"].name} {REMOTE_ROOT}/iii.auth {REMOTE_ROOT}/iii-validate.log
systemctl daemon-reload >/dev/null 2>&1 || true
systemctl is-active --quiet pp-lab-i.service
systemctl is-active --quiet pp-lab-ii.service
! id pp-lab-iii >/dev/null 2>&1
[ ! -e /etc/privatpirat/pp-lab-iii ] && [ ! -e /etc/systemd/system/pp-lab-iii.service ]'''
    listener_check = ""
    if port is not None:
        if not 1 <= int(port) <= 65535:
            raise ValueError("invalid port")
        flag = "-ltn" if route in {Route.I, Route.II} else "-lun"
        listener_check = f"\n! ss -H {flag} | awk '{{print $4}}' | grep -Eq ':{int(port)}$'"
    return f"set -euo pipefail\n{body}{listener_check}\nprintf 'ROLLBACK_{route.value}=PASS\\n'\n"


def finalize_remote_script() -> str:
    return f'''set -euo pipefail
systemctl is-active --quiet pp-lab-i.service
systemctl is-active --quiet pp-lab-ii.service
systemctl is-active --quiet pp-lab-iii.service
rm -f {REMOTE_ROOT}/runtime.json {REMOTE_ROOT}/material-I.json {REMOTE_ROOT}/material-II.json {REMOTE_ROOT}/material-III.json
rm -f {REMOTE_ROOT}/{ARTIFACTS["xray-linux-amd64"].name} {REMOTE_ROOT}/{ARTIFACTS["hysteria-linux-amd64"].name}
printf 'REMOTE_FINALIZE=PASS\n'
'''


class StageExecutor(Protocol):
    def apply(self, route: Route) -> None: ...
    def verify_server(self, route: Route) -> None: ...
    def fetch_material(self, route: Route) -> RouteMaterial: ...
    def rollback(self, route: Route) -> None: ...
    def finalize(self) -> None: ...


class ClientVerifier(Protocol):
    def verify(self, route: Route, material: RouteMaterial, rounds: int = 3) -> bool: ...


class SSHStageExecutor:
    """Concrete remote executor. Kept unreachable from CLI until R3-SERVER."""

    def __init__(self, session: RemoteSession, ports: Ports, runtime: RuntimePrivateInput, artifacts: Mapping[str, Path], private_dir: Path):
        self.session = session
        self.ports = ports
        self.runtime = RuntimePrivateInput(runtime.profile_name, validate_cover_hostname(runtime.cover_hostname))
        self.artifacts = artifacts
        self.private_dir = private_dir
        ensure_private_dir(private_dir)

    def _run(self, script: str, expected_marker: str, timeout: int = 90) -> None:
        try:
            proc = subprocess.run(_ssh_base(self.session) + ["bash", "-s"], input=script, text=True, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise BuilderStop("REMOTE_STAGE_TIMEOUT=STOP") from exc
        if proc.returncode or expected_marker not in proc.stdout.splitlines():
            raise BuilderStop(f"REMOTE_STAGE_FAILED={expected_marker}")

    def _scp_to(self, local: Path, remote: str) -> None:
        cmd = [
            "scp", "-q", "-P", str(self.session.port),
            "-o", "StrictHostKeyChecking=yes",
            "-o", f"UserKnownHostsFile={self.session.known_hosts}",
            str(local), f"{self.session.user}@{_scp_host(self.session.host)}:{remote}",
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=90)
        if proc.returncode:
            raise BuilderStop("SCP_UPLOAD_FAIL=STOP")

    def _scp_from(self, remote: str, local: Path) -> None:
        ensure_private_dir(local.parent)
        cmd = [
            "scp", "-q", "-P", str(self.session.port),
            "-o", "StrictHostKeyChecking=yes",
            "-o", f"UserKnownHostsFile={self.session.known_hosts}",
            f"{self.session.user}@{_scp_host(self.session.host)}:{remote}", str(local),
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=90)
        if proc.returncode:
            raise BuilderStop("SCP_DOWNLOAD_FAIL=STOP")
        os.chmod(local, 0o600)

    def _ensure_staging(self) -> None:
        self._run(f"set -eu\ninstall -d -m 0700 {REMOTE_ROOT}\nprintf 'STAGING=PASS\\n'\n", "STAGING=PASS")

    def _upload_runtime(self) -> None:
        runtime_file = self.private_dir / "runtime.json"
        write_private(runtime_file, json.dumps({"cover_hostname": self.runtime.cover_hostname}) + "\n")
        self._scp_to(runtime_file, f"{REMOTE_ROOT}/runtime.json")
        self._run(f"set -eu\nchmod 0600 {REMOTE_ROOT}/runtime.json\nprintf 'RUNTIME=PASS\\n'\n", "RUNTIME=PASS")

    def apply(self, route: Route) -> None:
        self._ensure_staging()
        if route is Route.I:
            self._upload_runtime()
            spec = ARTIFACTS["xray-linux-amd64"]
            self._scp_to(self.artifacts["server_xray_archive"], f"{REMOTE_ROOT}/{spec.name}")
            script = stage_i_apply_script(self.ports.route_i_tcp)
        elif route is Route.II:
            script = stage_ii_apply_script(self.ports.route_ii_tcp)
        else:
            spec = ARTIFACTS["hysteria-linux-amd64"]
            self._scp_to(self.artifacts["server_hysteria"], f"{REMOTE_ROOT}/{spec.name}")
            script = stage_iii_apply_script(self.ports.route_iii_udp)
        self._run(script, f"STAGE_{route.value}_APPLY=PASS", timeout=120)

    def verify_server(self, route: Route) -> None:
        self._run(server_verify_script(route, self.ports.for_route(route)), f"SERVER_VERIFY_{route.value}=PASS", timeout=90)

    def fetch_material(self, route: Route) -> RouteMaterial:
        local = self.private_dir / f"material-{route.value}.json"
        remote = f"{REMOTE_ROOT}/material-{route.value}.json"
        self._scp_from(remote, local)
        try:
            values = json.loads(local.read_text(encoding="utf-8"))
            if not isinstance(values, dict):
                raise BuilderStop("CLIENT_MATERIAL_FORMAT_INVALID=STOP")
            material = RouteMaterial.from_mapping(values)
        except json.JSONDecodeError as exc:
            raise BuilderStop("CLIENT_MATERIAL_JSON_INVALID=STOP") from exc
        self._run(f"set -eu\nrm -f {remote}\nprintf 'MATERIAL_CLEANUP=PASS\\n'\n", "MATERIAL_CLEANUP=PASS")
        return material

    def rollback(self, route: Route) -> None:
        self._run(rollback_script(route, self.ports.for_route(route)), f"ROLLBACK_{route.value}=PASS", timeout=90)
        for path in self.private_dir.glob(f"*{route.value}*"):
            if path.is_file():
                path.unlink()

    def finalize(self) -> None:
        self._run(finalize_remote_script(), "REMOTE_FINALIZE=PASS", timeout=60)


class LocalClientVerifier:
    """Three-round clean reconnect verifier using local SOCKS and curl."""

    def __init__(self, host: str, ports: Ports, runtime: RuntimePrivateInput, expected_egress_ip: str, artifacts: Mapping[str, Path], private_dir: Path):
        self.host = validate_host(host)
        self.ports = ports
        self.runtime = RuntimePrivateInput(runtime.profile_name, validate_cover_hostname(runtime.cover_hostname))
        self.expected_egress_ip = str(ipaddress.ip_address(expected_egress_ip))
        self.artifacts = artifacts
        self.private_dir = private_dir
        ensure_private_dir(private_dir)

    def _free_local_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _wait_socks(self, port: int, proc: subprocess.Popen[str]) -> bool:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                return False
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.2):
                    return True
            except OSError:
                time.sleep(.15)
        return False

    def _curl(self, socks_port: int, url: str) -> str:
        cmd = [
            "curl", "--fail", "--silent", "--show-error", "--max-time", "20",
            "--socks5-hostname", f"127.0.0.1:{socks_port}", url,
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=25)
        if proc.returncode or not proc.stdout:
            raise BuilderStop("CLIENT_DATA_PATH_FAIL=STOP")
        return proc.stdout.strip()

    def _verify_round(self, route: Route, material: RouteMaterial, index: int) -> bool:
        socks_port = self._free_local_port()
        cfg = self.private_dir / f"verify-{route.value}-{index}.conf"
        if route in {Route.I, Route.II}:
            write_private(cfg, render_xray_client_config(route, self.host, self.ports.for_route(route), material, self.runtime.cover_hostname, socks_port))
            binary = self.artifacts["client_xray"]
            cmd = [str(binary), "run", "-config", str(cfg)]
        else:
            write_private(cfg, render_hysteria_client_config(self.host, self.ports.route_iii_udp, material, socks_port))
            binary = self.artifacts["client_hysteria"]
            cmd = [str(binary), "client", "-c", str(cfg)]
        proc = subprocess.Popen(cmd, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            if not self._wait_socks(socks_port, proc):
                return False
            if not self._curl(socks_port, HTTP_PROBE_URL):
                return False
            if not self._curl(socks_port, HTTPS_PROBE_URL):
                return False
            exits = []
            for url in EXIT_IP_URLS:
                try:
                    exits.append(str(ipaddress.ip_address(self._curl(socks_port, url))))
                except ValueError:
                    return False
            return len(set(exits)) == 1 and secrets.compare_digest(exits[0], self.expected_egress_ip)
        except BuilderStop:
            return False
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
            try:
                cfg.unlink()
            except FileNotFoundError:
                pass

    def verify(self, route: Route, material: RouteMaterial, rounds: int = 3) -> bool:
        if rounds < 1:
            raise ValueError("rounds must be >= 1")
        return all(self._verify_round(route, material, idx) for idx in range(1, rounds + 1))


def write_client_bundle(directory: Path, host: str, ports: Ports, runtime: RuntimePrivateInput, materials: Mapping[Route, RouteMaterial]) -> list[Path]:
    ensure_private_dir(directory)
    written: list[Path] = []
    for route in (Route.I, Route.II, Route.III):
        material = materials[route]
        if route in {Route.I, Route.II}:
            text = render_xray_client_config(route, host, ports.for_route(route), material, runtime.cover_hostname, 10808)
            suffix = "json"
        else:
            text = render_hysteria_client_config(host, ports.route_iii_udp, material, 10808)
            suffix = "yaml"
        config_path = directory / f"{slugify(runtime.profile_name)}-{route.value}.{suffix}"
        uri_path = directory / f"{slugify(runtime.profile_name)}-{route.value}.uri"
        write_private(config_path, text)
        write_private(uri_path, render_share_uri(route, host, ports.for_route(route), material, runtime.cover_hostname, runtime.profile_name) + "\n")
        written.extend([config_path, uri_path])
    manifest = directory / "manifest.json"
    write_private(manifest, json.dumps({
        "builder_version": BUILDER_VERSION,
        "profile_name": runtime.profile_name,
        "routes": [r.value for r in (Route.I, Route.II, Route.III)],
        "files": [p.name for p in written],
    }, ensure_ascii=False, indent=2) + "\n")
    written.append(manifest)
    return written


class DeploymentEngine:
    def __init__(self, executor: StageExecutor, verifier: ClientVerifier, bundle_dir: Path, host: str, ports: Ports, runtime: RuntimePrivateInput):
        self.executor = executor
        self.verifier = verifier
        self.bundle_dir = bundle_dir
        self.host = host
        self.ports = ports
        self.runtime = runtime
        self.state = State.PREFLIGHT_PASS
        self.materials: dict[Route, RouteMaterial] = {}

    def _fail_stage(self, route: Route, error: Exception) -> None:
        self.state = transition(self.state, State.STAGE_FAIL)
        try:
            self.executor.rollback(route)
        except Exception as rollback_error:
            self.state = transition(self.state, State.STOPPED)
            raise BuilderStop("ROLLBACK_VERIFICATION_FAIL=STOP") from rollback_error
        self.state = transition(self.state, State.ROLLED_BACK)
        self.state = transition(self.state, State.STOPPED)
        raise BuilderStop(f"STAGE_{route.value}_FAIL=STOP") from error

    def _apply_and_accept(self, route: Route, applying: State, accepted: State) -> None:
        self.state = transition(self.state, applying)
        try:
            self.executor.apply(route)
            self.executor.verify_server(route)
            material = self.executor.fetch_material(route)
            if not self.verifier.verify(route, material, rounds=3):
                raise BuilderStop("CLIENT_ACCEPTANCE_FAIL=STOP")
            self.materials[route] = material
            if route is Route.II:
                if not self.verifier.verify(Route.I, self.materials[Route.I], rounds=3):
                    raise BuilderStop("REGRESSION_I_FAIL=STOP")
                self.state = transition(self.state, State.REGRESSION_I_PASS)
            self.state = transition(self.state, accepted)
        except Exception as exc:
            self._fail_stage(route, exc)

    def run(self) -> State:
        self._apply_and_accept(Route.I, State.I_APPLYING, State.I_PASS)
        self._apply_and_accept(Route.II, State.II_APPLYING, State.II_PASS)
        self._apply_and_accept(Route.III, State.III_APPLYING, State.III_PASS)
        # Regression I+II is still part of the III transaction.  A regression
        # failure means III is not accepted and only III is rolled back.
        try:
            if not self.verifier.verify(Route.I, self.materials[Route.I], rounds=3):
                raise BuilderStop("FINAL_REGRESSION_I_FAIL=STOP")
            if not self.verifier.verify(Route.II, self.materials[Route.II], rounds=3):
                raise BuilderStop("FINAL_REGRESSION_II_FAIL=STOP")
        except Exception as exc:
            self._fail_stage(Route.III, exc)
        self.state = transition(self.state, State.FINAL_REGRESSION_PASS)
        # From here all server stages are accepted.  A local bundle/finalize
        # failure stops the run but does not destroy an accepted route.
        try:
            write_client_bundle(self.bundle_dir, self.host, self.ports, self.runtime, self.materials)
            self.state = transition(self.state, State.CLIENT_BUNDLE_READY)
            self.executor.finalize()
            self.state = transition(self.state, State.PASS)
            return self.state
        except Exception as exc:
            self.state = State.STOPPED
            raise BuilderStop("FINALIZATION_FAIL=STOP") from exc


def perform_preflight(args: argparse.Namespace) -> PreflightContext:
    prereq = local_prerequisites()
    if not all(prereq.values()):
        raise BuilderStop("LOCAL_PREREQUISITES=FAIL")
    name = args.profile_name or input("Profile name: ").strip()
    slug = slugify(name)
    host = getpass.getpass("Target VPS IP/hostname: ").strip()
    user = input("SSH login: ").strip()
    fingerprint = getpass.getpass("Expected SSH ED25519 fingerprint (SHA256:...): ").strip()
    raw_port = input("SSH port [22]: ").strip()
    if raw_port and (not raw_port.isdigit() or not 1 <= int(raw_port) <= 65535):
        raise BuilderStop("SSH_PORT_INVALID=STOP")
    port = int(raw_port or 22)
    private = private_root() / slug
    known = pin_host_key(host, port, fingerprint, private)
    session = RemoteSession(validate_host(host), validate_user(user), port, known)
    inv = remote_inventory(session.host, session.user, session.port, session.known_hosts)
    checks = assert_inventory(inv)
    ports = select_ports(inv)
    state_dir = state_root() / slug
    write_private(state_dir / "state.json", json.dumps({
        "builder_version": BUILDER_VERSION,
        "display_name": name,
        "slug": slug,
        "state": State.PREFLIGHT_PASS.value,
        "route_ports": asdict(ports),
    }, ensure_ascii=False, indent=2) + "\n")
    return PreflightContext(name, slug, session, inv, ports, private, state_dir, checks)


def run_preflight(args: argparse.Namespace) -> int:
    context = perform_preflight(args)
    report = public_report({
        "builder_version": BUILDER_VERSION, "phase": "PRECHECK", "host_key_match": True, **context.checks,
        "route_i": "NOT_STARTED", "route_ii": "NOT_STARTED", "route_iii": "NOT_STARTED",
        "regression": "NOT_STARTED", "client_bundle": "NOT_READY", "verdict": "PREFLIGHT_PASS", "error": None,
    })
    for key, value in report.items():
        if value is not None:
            print(f"{key.upper()}={value}")
    return 0


def run_deployment_after_gate(args: argparse.Namespace) -> int:
    """Complete one-run orchestration, intentionally unreachable from CLI.

    A future R3-SERVER checkpoint may wire --apply to this function after code
    review.  Sensitive target/cover values are collected interactively and are
    never placed in command-line arguments or public reports.
    """
    context = perform_preflight(args)
    cover = validate_cover_hostname(getpass.getpass("REALITY cover hostname (private): ").strip())
    remote_cover_probe(context.session, cover)
    runtime = RuntimePrivateInput(context.profile_name, cover)
    artifacts = prepare_artifacts(cache_root() / context.slug)
    executor = SSHStageExecutor(context.session, context.ports, runtime, artifacts, context.private_dir)
    verifier = LocalClientVerifier(
        context.session.host, context.ports, runtime, context.inventory.egress_ip, artifacts, context.private_dir / "verify"
    )
    engine = DeploymentEngine(
        executor, verifier, context.private_dir / "client-bundle", context.session.host, context.ports, runtime
    )
    final_state = engine.run()
    write_private(context.state_dir / "state.json", json.dumps({
        "builder_version": BUILDER_VERSION, "display_name": context.profile_name, "slug": context.slug,
        "state": final_state.value, "route_ports": asdict(context.ports),
    }, ensure_ascii=False, indent=2) + "\n")
    report = public_report({
        "builder_version": BUILDER_VERSION, "phase": "FINAL", "host_key_match": True, **context.checks,
        "route_i": "PASS", "route_ii": "PASS", "route_iii": "PASS",
        "regression": "PASS", "client_bundle": "READY", "verdict": "PASS", "error": None,
    })
    for key, value in report.items():
        if value is not None:
            print(f"{key.upper()}={value}")
    return 0


def render_check() -> int:
    dummy_i = RouteMaterial(Route.I, uuid="123e4567-e89b-12d3-a456-426614174000", public_key="A" * 43, short_id="aabbccddeeff0011")
    dummy_ii = RouteMaterial(Route.II, uuid="123e4567-e89b-12d3-a456-426614174001", public_key="B" * 43, short_id="1122334455667788", xhttp_path="/0123456789abcdef")
    dummy_iii = RouteMaterial(Route.III, auth="a" * 64, pin_sha256="b" * 64)
    render_xray_server_config(Route.I, 23451, dummy_i, "cover.example", "C" * 43)
    render_xray_server_config(Route.II, 23452, dummy_ii, "cover.example", "D" * 43)
    render_xray_client_config(Route.I, "192.0.2.10", 23451, dummy_i, "cover.example", 10808)
    render_xray_client_config(Route.II, "192.0.2.10", 23452, dummy_ii, "cover.example", 10808)
    render_hysteria_server_config(23453, dummy_iii.auth or "", "/tmp/cert", "/tmp/key")
    render_hysteria_client_config("192.0.2.10", 23453, dummy_iii, 10808)
    if shutil.which("bash"):
        for script in (stage_i_apply_script(23451), stage_ii_apply_script(23452), stage_iii_apply_script(23453), server_verify_script(Route.I, 23451), rollback_script(Route.III)):
            proc = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True)
            if proc.returncode:
                print("RENDER_CHECK=FAIL")
                return 2
    print("RENDER_CHECK=PASS")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pp-build")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local-check", action="store_true")
    mode.add_argument("--render-check", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--apply", action="store_true", help="disabled until a separate reviewed R3-SERVER checkpoint")
    parser.add_argument("--profile-name")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    os.umask(0o077)
    args = build_parser().parse_args(argv)
    try:
        if args.local_check:
            result = local_prerequisites()
            for key in sorted(result):
                print(f"LOCAL_{key.upper()}={'PASS' if result[key] else 'FAIL'}")
            print(f"LOCAL_CHECK={'PASS' if all(result.values()) else 'FAIL'}")
            return 0 if all(result.values()) else 2
        if args.render_check:
            return render_check()
        if args.apply:
            print("APPLY=DISABLED")
            print("R3_SERVER=REQUIRED_AFTER_IMPLEMENTATION_REVIEW")
            print("VERDICT=STOP")
            return 3
        return run_preflight(args)
    except BuilderStop as exc:
        print(sanitize_error(str(exc)))
        print("VERDICT=STOP")
        return 2
    except KeyboardInterrupt:
        print("INTERRUPTED=STOP")
        return 130
    except Exception as exc:
        print(f"UNEXPECTED={sanitize_error(str(exc))}")
        print("VERDICT=STOP")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
