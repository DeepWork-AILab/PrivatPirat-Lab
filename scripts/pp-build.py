#!/usr/bin/env python3
"""PrivatPirat Reproducible Node Builder v0.1.

R3-CODE-3 checkpoint. The deployment engine is implemented behind a hard
CLI gate. This revision adds OpenSSH multiplexing, durable Builder-owned
resume state, explicit restart/isolation acceptance, network-aware formal
verdicts, and independent HTTP/HTTPS probes. No public CLI path can perform
server writes until a separate R3-SERVER change enables it.
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
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Mapping, Protocol, Sequence

BUILDER_VERSION = "0.1.0-r3-code-3"
SUPPORTED_OS = ("ubuntu", "24.04", "x86_64")
MIN_MEMORY_KIB = 512 * 1024
MIN_ROOT_FREE_KIB = 1024 * 1024
PORT_MIN, PORT_MAX = 20000, 60000
XRAY_VERSION = "26.3.27"
HYSTERIA_VERSION = "2.12.1"
REMOTE_ROOT = "/var/lib/privatpirat-builder"
XRAY_INSTALL = f"/usr/local/lib/privatpirat/xray-{XRAY_VERSION}/xray"
HYSTERIA_INSTALL = f"/usr/local/lib/privatpirat/hysteria-{HYSTERIA_VERSION}/hysteria"

# Independent transfer endpoints. Exit IP uses two more independent services.
HTTP_PROBE_URL = "http://example.com/"
HTTPS_PROBE_URL = "https://httpbin.org/get"
EXIT_IP_URLS = ("https://api.ipify.org", "https://icanhazip.com")
REQUIRED_NETWORKS = frozenset({"wifi", "mobile"})


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
ARTIFACT_SHA256 = {spec.name: spec.sha256 for spec in ARTIFACTS.values()}


class BuilderStop(RuntimeError):
    pass


class Route(str, Enum):
    I = "I"
    II = "II"
    III = "III"


class NetworkClass(str, Enum):
    WIFI = "wifi"
    MOBILE = "mobile"


class Verdict(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"


class State(str, Enum):
    NEW = "NEW"
    PREFLIGHT_PASS = "PREFLIGHT_PASS"
    I_APPLYING = "I_APPLYING"
    I_PASS = "I_PASS"
    II_APPLYING = "II_APPLYING"
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
    State.II_APPLYING: {State.II_PASS, State.STAGE_FAIL},
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
    "client_bundle", "formal_acceptance", "verdict", "error",
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
        return {Route.I: self.route_i_tcp, Route.II: self.route_ii_tcp, Route.III: self.route_iii_udp}[route]


@dataclass(frozen=True)
class RemoteSession:
    host: str
    user: str
    port: int
    known_hosts: Path
    control_path: Path | None = None


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
    target_binding: str


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
        allowed = {"route", "uuid", "public_key", "short_id", "xhttp_path", "auth", "pin_sha256"}
        if set(values) - allowed:
            raise BuilderStop("CLIENT_MATERIAL_UNKNOWN_FIELD=STOP")
        try:
            material = cls(
                route=Route(str(values["route"])),
                uuid=_optional_text(values.get("uuid")),
                public_key=_optional_text(values.get("public_key")),
                short_id=_optional_text(values.get("short_id")),
                xhttp_path=_optional_text(values.get("xhttp_path")),
                auth=_optional_text(values.get("auth")),
                pin_sha256=_optional_text(values.get("pin_sha256")),
            )
        except (KeyError, ValueError) as exc:
            raise BuilderStop("CLIENT_MATERIAL_ROUTE_INVALID=STOP") from exc
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


@dataclass
class AcceptanceLedger:
    data_path: dict[str, set[str]] = field(default_factory=lambda: {r.value: set() for r in Route})
    restart: dict[str, bool] = field(default_factory=lambda: {r.value: False for r in Route})
    isolation: dict[str, bool] = field(default_factory=lambda: {r.value: False for r in Route})
    dns_leak_checkpoint: dict[str, bool] = field(default_factory=lambda: {r.value: False for r in Route})
    regression: dict[str, set[str]] = field(default_factory=dict)
    failed_routes: set[str] = field(default_factory=set)

    def mark_data_path(self, route: Route, network: NetworkClass) -> None:
        self.data_path[route.value].add(network.value)

    def mark_regression(self, after: Route, prior: Route, network: NetworkClass) -> None:
        self.regression.setdefault(f"{after.value}>{prior.value}", set()).add(network.value)

    def route_verdict(self, route: Route) -> Verdict:
        if route.value in self.failed_routes:
            return Verdict.FAIL
        base = (
            REQUIRED_NETWORKS.issubset(self.data_path[route.value])
            and self.restart[route.value]
            and self.isolation[route.value]
            and self.dns_leak_checkpoint[route.value]
        )
        if not base:
            return Verdict.PARTIAL
        if route is Route.II and not REQUIRED_NETWORKS.issubset(self.regression.get("II>I", set())):
            return Verdict.PARTIAL
        if route is Route.III:
            if not REQUIRED_NETWORKS.issubset(self.regression.get("III>I", set())):
                return Verdict.PARTIAL
            if not REQUIRED_NETWORKS.issubset(self.regression.get("III>II", set())):
                return Verdict.PARTIAL
        return Verdict.PASS

    def final_verdict(self) -> Verdict:
        values = [self.route_verdict(route) for route in Route]
        if Verdict.FAIL in values:
            return Verdict.FAIL
        if all(value is Verdict.PASS for value in values):
            return Verdict.PASS
        return Verdict.PARTIAL

    def reset_route_evidence(self, route: Route) -> None:
        self.data_path[route.value] = set()
        self.restart[route.value] = False
        self.isolation[route.value] = False
        self.dns_leak_checkpoint[route.value] = False
        for key in list(self.regression):
            if key.startswith(route.value + ">"):
                self.regression.pop(key, None)

    def validate(self) -> None:
        allowed_routes = {r.value for r in Route}
        if not self.failed_routes.issubset(allowed_routes):
            raise BuilderStop("RESUME_LEDGER_INVALID=STOP")
        for networks in self.data_path.values():
            if not set(networks).issubset(REQUIRED_NETWORKS):
                raise BuilderStop("RESUME_LEDGER_INVALID=STOP")
        allowed_regressions = {"II>I", "III>I", "III>II"}
        if set(self.regression) - allowed_regressions:
            raise BuilderStop("RESUME_LEDGER_INVALID=STOP")
        for networks in self.regression.values():
            if not set(networks).issubset(REQUIRED_NETWORKS):
                raise BuilderStop("RESUME_LEDGER_INVALID=STOP")

    def to_jsonable(self) -> dict[str, object]:
        return {
            "data_path": {k: sorted(v) for k, v in self.data_path.items()},
            "restart": self.restart,
            "isolation": self.isolation,
            "dns_leak_checkpoint": self.dns_leak_checkpoint,
            "regression": {k: sorted(v) for k, v in self.regression.items()},
            "failed_routes": sorted(self.failed_routes),
        }

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "AcceptanceLedger":
        ledger = cls()
        for key in (r.value for r in Route):
            ledger.data_path[key] = set(str(x) for x in dict(values.get("data_path", {})).get(key, []))
            ledger.restart[key] = bool(dict(values.get("restart", {})).get(key, False))
            ledger.isolation[key] = bool(dict(values.get("isolation", {})).get(key, False))
            ledger.dns_leak_checkpoint[key] = bool(dict(values.get("dns_leak_checkpoint", {})).get(key, False))
        ledger.regression = {str(k): set(str(x) for x in v) for k, v in dict(values.get("regression", {})).items()}
        ledger.failed_routes = set(str(x) for x in values.get("failed_routes", []))
        return ledger


@dataclass(frozen=True)
class PersistentState:
    builder_version: str
    run_id: str
    target_binding: str
    accepted_routes: tuple[str, ...]
    ports: Ports
    ledger: AcceptanceLedger
    last_failed_route: str | None = None

    def pending_route(self) -> Route | None:
        if self.accepted_routes == ("I", "II", "III"):
            return None
        candidate = list(Route)[len(self.accepted_routes)]
        evidence = (
            bool(self.ledger.data_path[candidate.value])
            or self.ledger.restart[candidate.value]
            or self.ledger.isolation[candidate.value]
            or self.ledger.dns_leak_checkpoint[candidate.value]
            or any(k.startswith(candidate.value + ">") for k in self.ledger.regression)
        )
        return candidate if evidence else None

    def to_jsonable(self) -> dict[str, object]:
        return {
            "builder_version": self.builder_version,
            "run_id": self.run_id,
            "target_binding": self.target_binding,
            "accepted_routes": list(self.accepted_routes),
            "ports": asdict(self.ports),
            "ledger": self.ledger.to_jsonable(),
            "last_failed_route": self.last_failed_route,
        }

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "PersistentState":
        try:
            ports_raw = dict(values["ports"])
            accepted = tuple(str(x) for x in values.get("accepted_routes", []))
            if accepted not in ((), ("I",), ("I", "II"), ("I", "II", "III")):
                raise ValueError("invalid accepted route prefix")
            state = cls(
                builder_version=str(values["builder_version"]),
                run_id=str(values["run_id"]),
                target_binding=str(values["target_binding"]),
                accepted_routes=accepted,
                ports=Ports(int(ports_raw["route_i_tcp"]), int(ports_raw["route_ii_tcp"]), int(ports_raw["route_iii_udp"])),
                ledger=AcceptanceLedger.from_mapping(dict(values.get("ledger", {}))),
                last_failed_route=None if values.get("last_failed_route") is None else str(values["last_failed_route"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise BuilderStop("RESUME_STATE_INVALID=STOP") from exc
        if not re.fullmatch(r"[0-9a-f]{32}", state.run_id):
            raise BuilderStop("RESUME_RUN_ID_INVALID=STOP")
        if state.builder_version != BUILDER_VERSION:
            raise BuilderStop("RESUME_BUILDER_VERSION_MISMATCH=STOP")
        if not re.fullmatch(r"[0-9a-f]{64}", state.target_binding):
            raise BuilderStop("RESUME_TARGET_BINDING_INVALID=STOP")
        port_values = tuple(asdict(state.ports).values())
        if len(set(port_values)) != 3 or any(not 1 <= int(port) <= 65535 for port in port_values):
            raise BuilderStop("RESUME_PORTS_INVALID=STOP")
        state.ledger.validate()
        for route_value in state.accepted_routes:
            if state.ledger.route_verdict(Route(route_value)) is not Verdict.PASS:
                raise BuilderStop("RESUME_ACCEPTED_ROUTE_NOT_PASS=STOP")
        return state


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
    safe = str(message or "unknown error").replace(str(Path.home()), "%HOME%")
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


def save_state(path: Path, state: PersistentState) -> None:
    write_private(path, json.dumps(state.to_jsonable(), ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def load_state(path: Path) -> PersistentState:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise BuilderStop("RESUME_STATE_UNAVAILABLE=STOP") from exc
    if not isinstance(raw, dict):
        raise BuilderStop("RESUME_STATE_INVALID=STOP")
    return PersistentState.from_mapping(raw)


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


def evaluate_inventory(inv: Inventory, *, require_clean: bool = True) -> dict[str, bool]:
    os_ok = (inv.os_id, inv.os_version) == SUPPORTED_OS[:2]
    arch_ok = inv.arch == SUPPORTED_OS[2]
    resources_ok = inv.cpu_count >= 1 and inv.mem_kib >= MIN_MEMORY_KIB and inv.root_free_kib >= MIN_ROOT_FREE_KIB
    clean = inv.uid == 0 and inv.systemd and inv.ss and inv.openssl and inv.sha256sum and inv.python3
    if require_clean:
        clean = clean and not inv.relevant_found
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


def assert_inventory(inv: Inventory, *, require_clean: bool = True) -> dict[str, bool]:
    result = evaluate_inventory(inv, require_clean=require_clean)
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


def target_binding(host: str, user: str, port: int, fingerprint: str) -> str:
    payload = "\0".join((validate_host(host), validate_user(user), str(port), validate_fingerprint(fingerprint)))
    return hashlib.sha256(payload.encode()).hexdigest()


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


def _ssh_common(session: RemoteSession, *, multiplex: bool) -> list[str]:
    opts = [
        "-p", str(session.port),
        "-o", "StrictHostKeyChecking=yes",
        "-o", f"UserKnownHostsFile={session.known_hosts}",
        "-o", "LogLevel=ERROR",
    ]
    if multiplex:
        if session.control_path is None:
            raise BuilderStop("SSH_CONTROLMASTER_REQUIRED=STOP")
        opts += ["-S", str(session.control_path), "-o", "ControlMaster=no", "-o", "BatchMode=yes"]
    return opts


def _ssh_base(session: RemoteSession) -> list[str]:
    return ["ssh", "-T"] + _ssh_common(session, multiplex=session.control_path is not None) + [f"{validate_user(session.user)}@{validate_host(session.host)}"]


def _scp_base(session: RemoteSession) -> list[str]:
    common = _ssh_common(session, multiplex=session.control_path is not None)
    converted: list[str] = []
    it = iter(common)
    for item in it:
        if item == "-p":
            converted.extend(["-P", next(it)])
        else:
            converted.append(item)
    return ["scp", "-q"] + converted


def control_socket_path(slug: str) -> Path:
    base = Path(os.environ.get("TMPDIR", tempfile.gettempdir())) / ("ppb-" + hashlib.sha256(slug.encode()).hexdigest()[:10])
    ensure_private_dir(base)
    return base / "ctl"


class SSHControlMaster:
    """One interactive OpenSSH authentication, reused by all ssh/scp calls."""

    def __init__(self, session: RemoteSession, slug: str):
        self.original = session
        self.path = control_socket_path(slug)
        self.session = replace(session, control_path=self.path)
        self.opened = False

    def __enter__(self) -> RemoteSession:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        cmd = [
            "ssh", "-M", "-N", "-f", "-S", str(self.path),
            "-p", str(self.original.port),
            "-o", "StrictHostKeyChecking=yes",
            "-o", f"UserKnownHostsFile={self.original.known_hosts}",
            "-o", "ControlPersist=no",
            "-o", "LogLevel=ERROR",
            f"{validate_user(self.original.user)}@{validate_host(self.original.host)}",
        ]
        try:
            proc = subprocess.run(cmd, timeout=60)
        except subprocess.TimeoutExpired as exc:
            raise BuilderStop("SSH_MASTER_TIMEOUT=STOP") from exc
        if proc.returncode:
            raise BuilderStop("SSH_MASTER_OPEN_FAIL=STOP")
        check = subprocess.run(
            ["ssh", "-p", str(self.original.port), "-S", str(self.path), "-O", "check", f"{self.original.user}@{self.original.host}"],
            text=True, capture_output=True, timeout=10,
        )
        if check.returncode:
            self.close()
            raise BuilderStop("SSH_MASTER_CHECK_FAIL=STOP")
        self.opened = True
        return self.session

    def close(self) -> None:
        if self.path.exists():
            try:
                subprocess.run(
                    ["ssh", "-p", str(self.original.port), "-S", str(self.path), "-O", "exit", f"{self.original.user}@{self.original.host}"],
                    text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
                )
            except (subprocess.TimeoutExpired, OSError):
                pass
        self.opened = False
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def remote_inventory(session: RemoteSession) -> Inventory:
    try:
        proc = subprocess.run(_ssh_base(session) + ["sh", "-s"], input=INVENTORY_SCRIPT, text=True, capture_output=True, timeout=55)
    except subprocess.TimeoutExpired as exc:
        raise BuilderStop("SSH_INVENTORY_TIMEOUT=STOP") from exc
    if proc.returncode:
        raise BuilderStop("SSH_INVENTORY_FAIL=STOP")
    return parse_inventory(proc.stdout)


def remote_cover_probe(session: RemoteSession, cover_hostname: str) -> None:
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
        proc = subprocess.run(_ssh_base(session) + ["python3", "-"], input=payload, text=True, capture_output=True, timeout=15)
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
        req = urllib.request.Request(spec.url, headers={"User-Agent": f"PrivatPirat-Builder/{BUILDER_VERSION}"})
        with urllib.request.urlopen(req, timeout=60) as response, tmp.open("wb") as out:
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
    client: dict[str, object] = {"id": material.uuid}
    if route is Route.I:
        client["flow"] = "xtls-rprx-vision"
    stream: dict[str, object] = {
        "network": "raw" if route is Route.I else "xhttp",
        "security": "reality",
        "realitySettings": {
            "show": False, "target": f"{cover}:443", "serverNames": [cover],
            "privateKey": private_key, "shortIds": [material.short_id],
        },
    }
    if route is Route.II:
        stream["xhttpSettings"] = {"path": material.xhttp_path, "mode": "auto"}
    cfg = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "listen": "0.0.0.0", "port": port, "protocol": "vless",
            "settings": {"clients": [client], "decryption": "none"}, "streamSettings": stream,
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
        "network": "raw" if route is Route.I else "xhttp", "security": "reality",
        "realitySettings": {
            "fingerprint": "firefox", "serverName": cover, "password": material.public_key,
            "shortId": material.short_id, "spiderX": "/",
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
    return f"listen: :{port}\ntls:\n  cert: {cert}\n  key: {key}\nauth:\n  type: password\n  password: {auth}\n"


def render_hysteria_client_config(host: str, port: int, material: RouteMaterial, socks_port: int) -> str:
    if material.route is not Route.III:
        raise ValueError("hysteria route required")
    material.validate()
    return (
        f"server: {_authority(host, port)}\nauth: {material.auth}\n"
        "tls:\n  insecure: true\n"
        f"  pinSHA256: {material.pin_sha256}\n"
        f"socks5:\n  listen: 127.0.0.1:{socks_port}\n"
    )


def render_share_uri(route: Route, host: str, port: int, material: RouteMaterial, cover_hostname: str, profile_name: str) -> str:
    label = urllib.parse.quote(f"{profile_name}-{route.value}", safe="")
    authority = _authority(host, port)
    if route in {Route.I, Route.II}:
        material.validate()
        query: dict[str, str | None] = {
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
ROOT={REMOTE_ROOT!r}; CFG=/etc/privatpirat/pp-lab-i/config.json; MAT="$ROOT/material-I.json"; XRAY={XRAY_INSTALL!r}
rollback() {{ systemctl disable --now pp-lab-i.service >/dev/null 2>&1 || true; rm -f /etc/systemd/system/pp-lab-i.service; rm -rf /etc/privatpirat/pp-lab-i; userdel pp-lab-i >/dev/null 2>&1 || true; rm -rf /usr/local/lib/privatpirat/xray-{XRAY_VERSION}; rm -f "$MAT"; systemctl daemon-reload >/dev/null 2>&1 || true; }}
trap 'rollback' ERR HUP INT TERM
[ "$(id -u)" = 0 ]; [ -f "$ROOT/{archive.name}" ] && [ -f "$ROOT/runtime.json" ]; ! id pp-lab-i >/dev/null 2>&1
! ss -H -ltn | awk '{{print $4}}' | grep -Eq ':{port}$'
printf '%s  %s\n' {archive.sha256!r} "$ROOT/{archive.name}" | sha256sum -c - >/dev/null
install -d -m 0755 /usr/local/lib/privatpirat/xray-{XRAY_VERSION}
python3 - "$ROOT/{archive.name}" "$XRAY" <<'__PP_EXTRACT__'
import os,pathlib,sys,tempfile,zipfile
src,dst=sys.argv[1:]
with zipfile.ZipFile(src) as z:
 h=[n for n in z.namelist() if pathlib.PurePosixPath(n).name=="xray" and not n.endswith("/")]
 if len(h)!=1: raise SystemExit(31)
 data=z.read(h[0])
fd,tmp=tempfile.mkstemp(dir=str(pathlib.Path(dst).parent));
with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
os.chmod(tmp,0o755); os.replace(tmp,dst)
__PP_EXTRACT__
useradd --system --user-group --home /nonexistent --shell /usr/sbin/nologin pp-lab-i
install -d -m 0750 -o root -g pp-lab-i /etc/privatpirat/pp-lab-i; umask 077
python3 - <<'__PP_UUID__' > "$ROOT/i.uuid"
import uuid; print(uuid.uuid4())
__PP_UUID__
"$XRAY" x25519 > "$ROOT/i.keys"; openssl rand -hex 8 > "$ROOT/i.sid"
python3 - "$ROOT/runtime.json" "$ROOT/i.uuid" "$ROOT/i.keys" "$ROOT/i.sid" "$CFG" "$MAT" {port} <<'__PP_CFG__'
import json,pathlib,sys
runtime,uf,kf,sf,cfgf,matf,port=sys.argv[1:]
cover=json.load(open(runtime))["cover_hostname"]; u=pathlib.Path(uf).read_text().strip(); sid=pathlib.Path(sf).read_text().strip(); lines=pathlib.Path(kf).read_text().splitlines()
priv=next(x.split(": ",1)[1] for x in lines if x.startswith("PrivateKey: ")); pub=next(x.split(": ",1)[1] for x in lines if x.startswith("Password (PublicKey): "))
cfg={{"log":{{"loglevel":"warning"}},"inbounds":[{{"listen":"0.0.0.0","port":int(port),"protocol":"vless","settings":{{"clients":[{{"id":u,"flow":"xtls-rprx-vision"}}],"decryption":"none"}},"streamSettings":{{"network":"raw","security":"reality","realitySettings":{{"show":False,"target":cover+":443","serverNames":[cover],"privateKey":priv,"shortIds":[sid]}}}}}}],"outbounds":[{{"protocol":"freedom","tag":"direct"}}]}}
pathlib.Path(cfgf).write_text(json.dumps(cfg,indent=2)+"\n"); pathlib.Path(matf).write_text(json.dumps({{"route":"I","uuid":u,"public_key":pub,"short_id":sid}})+"\n")
__PP_CFG__
chown root:pp-lab-i "$CFG"; chmod 0640 "$CFG"; chmod 0600 "$MAT"; rm -f "$ROOT/i.uuid" "$ROOT/i.keys" "$ROOT/i.sid"
"$XRAY" run -test -config "$CFG" >/dev/null 2>&1
cat > /etc/systemd/system/pp-lab-i.service <<'__PP_UNIT__'
{unit}__PP_UNIT__
systemctl daemon-reload; systemctl enable --now pp-lab-i.service >/dev/null
for _ in $(seq 1 25); do systemctl is-active --quiet pp-lab-i.service && ss -H -ltn | awk '{{print $4}}' | grep -Eq ':{port}$' && break; sleep .2; done
systemctl is-active --quiet pp-lab-i.service; ss -H -ltn | awk '{{print $4}}' | grep -Eq ':{port}$'
trap - ERR HUP INT TERM; printf 'STAGE_I_APPLY=PASS\n'
'''


def stage_ii_apply_script(port: int) -> str:
    unit = _systemd_unit("pp-lab-ii", f"{XRAY_INSTALL} run -config /etc/privatpirat/pp-lab-ii/config.json")
    return f'''set -euo pipefail
ROOT={REMOTE_ROOT!r}; CFG=/etc/privatpirat/pp-lab-ii/config.json; MAT="$ROOT/material-II.json"; XRAY={XRAY_INSTALL!r}
rollback() {{ systemctl disable --now pp-lab-ii.service >/dev/null 2>&1 || true; rm -f /etc/systemd/system/pp-lab-ii.service; rm -rf /etc/privatpirat/pp-lab-ii; userdel pp-lab-ii >/dev/null 2>&1 || true; rm -f "$MAT" "$ROOT"/ii.*; systemctl daemon-reload >/dev/null 2>&1 || true; }}
trap 'rollback' ERR HUP INT TERM
[ -x "$XRAY" ] && [ -f "$ROOT/runtime.json" ]; systemctl is-active --quiet pp-lab-i.service
I_HASH_BEFORE="$(sha256sum /etc/privatpirat/pp-lab-i/config.json | awk '{{print $1}}')"; ! id pp-lab-ii >/dev/null 2>&1; ! ss -H -ltn | awk '{{print $4}}' | grep -Eq ':{port}$'
useradd --system --user-group --home /nonexistent --shell /usr/sbin/nologin pp-lab-ii; install -d -m 0750 -o root -g pp-lab-ii /etc/privatpirat/pp-lab-ii; umask 077
python3 - <<'__PP_UUID__' > "$ROOT/ii.uuid"
import uuid; print(uuid.uuid4())
__PP_UUID__
"$XRAY" x25519 > "$ROOT/ii.keys"; openssl rand -hex 8 > "$ROOT/ii.sid"; printf '/%s\n' "$(openssl rand -hex 12)" > "$ROOT/ii.path"
python3 - "$ROOT/runtime.json" "$ROOT/ii.uuid" "$ROOT/ii.keys" "$ROOT/ii.sid" "$ROOT/ii.path" "$CFG" "$MAT" {port} <<'__PP_CFG__'
import json,pathlib,sys
runtime,uf,kf,sf,pf,cfgf,matf,port=sys.argv[1:]; cover=json.load(open(runtime))["cover_hostname"]; u=pathlib.Path(uf).read_text().strip(); sid=pathlib.Path(sf).read_text().strip(); path=pathlib.Path(pf).read_text().strip(); lines=pathlib.Path(kf).read_text().splitlines()
priv=next(x.split(": ",1)[1] for x in lines if x.startswith("PrivateKey: ")); pub=next(x.split(": ",1)[1] for x in lines if x.startswith("Password (PublicKey): "))
cfg={{"log":{{"loglevel":"warning"}},"inbounds":[{{"listen":"0.0.0.0","port":int(port),"protocol":"vless","settings":{{"clients":[{{"id":u}}],"decryption":"none"}},"streamSettings":{{"network":"xhttp","security":"reality","realitySettings":{{"show":False,"target":cover+":443","serverNames":[cover],"privateKey":priv,"shortIds":[sid]}},"xhttpSettings":{{"path":path,"mode":"auto"}}}}}}],"outbounds":[{{"protocol":"freedom","tag":"direct"}}]}}
pathlib.Path(cfgf).write_text(json.dumps(cfg,indent=2)+"\n"); pathlib.Path(matf).write_text(json.dumps({{"route":"II","uuid":u,"public_key":pub,"short_id":sid,"xhttp_path":path}})+"\n")
__PP_CFG__
chown root:pp-lab-ii "$CFG"; chmod 0640 "$CFG"; chmod 0600 "$MAT"; rm -f "$ROOT"/ii.uuid "$ROOT"/ii.keys "$ROOT"/ii.sid "$ROOT"/ii.path
"$XRAY" run -test -config "$CFG" >/dev/null 2>&1
cat > /etc/systemd/system/pp-lab-ii.service <<'__PP_UNIT__'
{unit}__PP_UNIT__
systemctl daemon-reload; systemctl enable --now pp-lab-ii.service >/dev/null
for _ in $(seq 1 25); do systemctl is-active --quiet pp-lab-ii.service && ss -H -ltn | awk '{{print $4}}' | grep -Eq ':{port}$' && break; sleep .2; done
systemctl is-active --quiet pp-lab-i.service; systemctl is-active --quiet pp-lab-ii.service; [ "$I_HASH_BEFORE" = "$(sha256sum /etc/privatpirat/pp-lab-i/config.json | awk '{{print $1}}')" ]; ss -H -ltn | awk '{{print $4}}' | grep -Eq ':{port}$'
trap - ERR HUP INT TERM; printf 'STAGE_II_APPLY=PASS\n'
'''


def stage_iii_apply_script(port: int) -> str:
    spec = ARTIFACTS["hysteria-linux-amd64"]
    unit = _systemd_unit("pp-lab-iii", f"{HYSTERIA_INSTALL} server -c /etc/privatpirat/pp-lab-iii/config.yaml")
    return f'''set -euo pipefail
ROOT={REMOTE_ROOT!r}; DIR=/etc/privatpirat/pp-lab-iii; CFG="$DIR/config.yaml"; MAT="$ROOT/material-III.json"; HY={HYSTERIA_INSTALL!r}
rollback() {{ if [ -n "${{TEST_PID:-}}" ]; then kill "$TEST_PID" >/dev/null 2>&1 || true; fi; systemctl disable --now pp-lab-iii.service >/dev/null 2>&1 || true; rm -f /etc/systemd/system/pp-lab-iii.service; rm -rf "$DIR"; userdel pp-lab-iii >/dev/null 2>&1 || true; rm -rf /usr/local/lib/privatpirat/hysteria-{HYSTERIA_VERSION}; rm -f "$MAT" "$ROOT/{spec.name}" "$ROOT/iii.auth" "$ROOT/iii-validate.log"; systemctl daemon-reload >/dev/null 2>&1 || true; }}
trap 'rollback' ERR HUP INT TERM
systemctl is-active --quiet pp-lab-i.service; systemctl is-active --quiet pp-lab-ii.service
I_HASH_BEFORE="$(sha256sum /etc/privatpirat/pp-lab-i/config.json | awk '{{print $1}}')"; II_HASH_BEFORE="$(sha256sum /etc/privatpirat/pp-lab-ii/config.json | awk '{{print $1}}')"
! id pp-lab-iii >/dev/null 2>&1; ! ss -H -lun | awk '{{print $4}}' | grep -Eq ':{port}$'; printf '%s  %s\n' {spec.sha256!r} "$ROOT/{spec.name}" | sha256sum -c - >/dev/null
install -d -m 0755 /usr/local/lib/privatpirat/hysteria-{HYSTERIA_VERSION}; install -m 0755 "$ROOT/{spec.name}" "$HY"; useradd --system --user-group --home /nonexistent --shell /usr/sbin/nologin pp-lab-iii; install -d -m 0750 -o root -g pp-lab-iii "$DIR"; umask 077
openssl rand -hex 32 > "$ROOT/iii.auth"; openssl req -x509 -newkey rsa:2048 -sha256 -days 825 -nodes -subj '/CN=privatpirat.local' -keyout "$DIR/server.key" -out "$DIR/server.crt" >/dev/null 2>&1
AUTH="$(cat "$ROOT/iii.auth")"; cat > "$CFG" <<__PP_HY__
listen: :{port}
tls:
  cert: $DIR/server.crt
  key: $DIR/server.key
auth:
  type: password
  password: $AUTH
__PP_HY__
unset AUTH; chown root:pp-lab-iii "$CFG" "$DIR/server.crt" "$DIR/server.key"; chmod 0640 "$CFG" "$DIR/server.crt" "$DIR/server.key"
"$HY" server -c "$CFG" > "$ROOT/iii-validate.log" 2>&1 & TEST_PID=$!; SEEN=0
for _ in $(seq 1 30); do if ss -H -lun | awk '{{print $4}}' | grep -Eq ':{port}$'; then SEEN=1; break; fi; kill -0 "$TEST_PID" >/dev/null 2>&1 || break; sleep .2; done
kill "$TEST_PID" >/dev/null 2>&1 || true; wait "$TEST_PID" >/dev/null 2>&1 || true; [ "$SEEN" = 1 ]; rm -f "$ROOT/iii-validate.log"
PIN="$(openssl x509 -in "$DIR/server.crt" -outform DER | sha256sum | awk '{{print $1}}')"; python3 - "$ROOT/iii.auth" "$PIN" "$MAT" <<'__PP_MAT__'
import json,pathlib,sys
authf,pin,matf=sys.argv[1:]; pathlib.Path(matf).write_text(json.dumps({{"route":"III","auth":pathlib.Path(authf).read_text().strip(),"pin_sha256":pin}})+"\n")
__PP_MAT__
chmod 0600 "$MAT"; rm -f "$ROOT/iii.auth"
cat > /etc/systemd/system/pp-lab-iii.service <<'__PP_UNIT__'
{unit}__PP_UNIT__
systemctl daemon-reload; systemctl enable --now pp-lab-iii.service >/dev/null
for _ in $(seq 1 25); do systemctl is-active --quiet pp-lab-iii.service && ss -H -lun | awk '{{print $4}}' | grep -Eq ':{port}$' && break; sleep .2; done
systemctl is-active --quiet pp-lab-i.service; systemctl is-active --quiet pp-lab-ii.service; systemctl is-active --quiet pp-lab-iii.service
[ "$I_HASH_BEFORE" = "$(sha256sum /etc/privatpirat/pp-lab-i/config.json | awk '{{print $1}}')" ]; [ "$II_HASH_BEFORE" = "$(sha256sum /etc/privatpirat/pp-lab-ii/config.json | awk '{{print $1}}')" ]; ss -H -lun | awk '{{print $4}}' | grep -Eq ':{port}$'
trap - ERR HUP INT TERM; printf 'STAGE_III_APPLY=PASS\n'
'''


def server_action_script(route: Route, port: int, action: str) -> str:
    if action not in {"health", "restart", "stop", "start"}:
        raise ValueError("invalid server action")
    unit = {Route.I: "pp-lab-i.service", Route.II: "pp-lab-ii.service", Route.III: "pp-lab-iii.service"}[route]
    flag = "-ltn" if route in {Route.I, Route.II} else "-lun"
    prior = [Route.I] if route is Route.II else ([Route.I, Route.II] if route is Route.III else [])
    prior_checks = "\n".join(f"systemctl is-active --quiet pp-lab-{p.value.lower()}.service" for p in prior)
    if action == "stop":
        body = f'''systemctl stop "$UNIT"
! systemctl is-active --quiet "$UNIT"
! ss -H {flag} | awk '{{print $4}}' | grep -Eq ':{port}$'
{prior_checks}'''
    else:
        if action == "health":
            command = ""
            pid_check = ""
        elif action == "restart":
            command = 'OLD_PID="$(systemctl show -p MainPID --value "$UNIT")"\nsystemctl restart "$UNIT"'
            pid_check = 'NEW_PID="$(systemctl show -p MainPID --value "$UNIT")"\n[ "$NEW_PID" != "0" ]\n[ "$OLD_PID" != "$NEW_PID" ]'
        else:
            command = f"systemctl {action} \"$UNIT\""
            pid_check = ""
        body = f'''{command}
for _ in $(seq 1 25); do systemctl is-active --quiet "$UNIT" && ss -H {flag} | awk '{{print $4}}' | grep -Eq ':{port}$' && break; sleep .2; done
systemctl is-active --quiet "$UNIT"
ss -H {flag} | awk '{{print $4}}' | grep -Eq ':{port}$'
{pid_check}
{prior_checks}'''
    marker = f"SERVER_{action.upper()}_{route.value}=PASS"
    return f"set -euo pipefail\nUNIT={unit!r}\n{body}\nprintf '{marker}\\n'\n"


def rollback_script(route: Route, port: int | None = None) -> str:
    if route is Route.I:
        body = f'''systemctl disable --now pp-lab-i.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/pp-lab-i.service; rm -rf /etc/privatpirat/pp-lab-i; userdel pp-lab-i >/dev/null 2>&1 || true; rm -rf /usr/local/lib/privatpirat/xray-{XRAY_VERSION}; rm -rf {REMOTE_ROOT}; systemctl daemon-reload >/dev/null 2>&1 || true
! id pp-lab-i >/dev/null 2>&1'''
    elif route is Route.II:
        body = f'''systemctl disable --now pp-lab-ii.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/pp-lab-ii.service; rm -rf /etc/privatpirat/pp-lab-ii; userdel pp-lab-ii >/dev/null 2>&1 || true; rm -f {REMOTE_ROOT}/material-II.json {REMOTE_ROOT}/ii.*; systemctl daemon-reload >/dev/null 2>&1 || true
systemctl is-active --quiet pp-lab-i.service; ! id pp-lab-ii >/dev/null 2>&1'''
    else:
        body = f'''systemctl disable --now pp-lab-iii.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/pp-lab-iii.service; rm -rf /etc/privatpirat/pp-lab-iii; userdel pp-lab-iii >/dev/null 2>&1 || true; rm -rf /usr/local/lib/privatpirat/hysteria-{HYSTERIA_VERSION}; rm -f {REMOTE_ROOT}/material-III.json {REMOTE_ROOT}/{ARTIFACTS["hysteria-linux-amd64"].name} {REMOTE_ROOT}/iii.*; systemctl daemon-reload >/dev/null 2>&1 || true
systemctl is-active --quiet pp-lab-i.service; systemctl is-active --quiet pp-lab-ii.service; ! id pp-lab-iii >/dev/null 2>&1'''
    listener = ""
    if port is not None:
        if not 1 <= int(port) <= 65535:
            raise ValueError("invalid port")
        flag = "-ltn" if route in {Route.I, Route.II} else "-lun"
        listener = f"\n! ss -H {flag} | awk '{{print $4}}' | grep -Eq ':{int(port)}$'"
    return f"set -euo pipefail\n{body}{listener}\nprintf 'ROLLBACK_{route.value}=PASS\\n'\n"


def owner_initialize_script(run_id: str, ports: Ports) -> str:
    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise ValueError("invalid run id")
    payload = json.dumps({"run_id": run_id, "ports": asdict(ports), "accepted": [], "config_sha256": {}}, separators=(",", ":"))
    return f'''set -euo pipefail
install -d -m 0700 {REMOTE_ROOT}
[ ! -e {REMOTE_ROOT}/owner.json ]
umask 077
cat > {REMOTE_ROOT}/owner.json <<'__PP_OWNER__'
{payload}
__PP_OWNER__
chmod 0600 {REMOTE_ROOT}/owner.json
printf 'OWNER_INIT=PASS\n'
'''


def owner_checkpoint_script(run_id: str, route: Route) -> str:
    paths = {Route.I: "/etc/privatpirat/pp-lab-i/config.json", Route.II: "/etc/privatpirat/pp-lab-ii/config.json", Route.III: "/etc/privatpirat/pp-lab-iii/config.yaml"}
    return f'''set -euo pipefail
python3 - {REMOTE_ROOT}/owner.json {run_id!r} {route.value!r} {paths[route]!r} <<'__PP_CHECKPOINT__'
import hashlib,json,os,pathlib,sys,tempfile
p=pathlib.Path(sys.argv[1]); expected,route,cfg=sys.argv[2:]; d=json.loads(p.read_text())
if d.get("run_id")!=expected: raise SystemExit(40)
accepted=d.get("accepted",[]); expected_prefix={{"I":[],"II":["I"],"III":["I","II"]}}[route]
h=hashlib.sha256(pathlib.Path(cfg).read_bytes()).hexdigest()
if accepted==expected_prefix+[route]:
 if d.get("config_sha256",{{}}).get(route)!=h: raise SystemExit(42)
 raise SystemExit(0)
if accepted!=expected_prefix: raise SystemExit(41)
d.setdefault("config_sha256",{{}})[route]=h; d["accepted"]=accepted+[route]
fd,tmp=tempfile.mkstemp(dir=str(p.parent),prefix=".owner-")
with os.fdopen(fd,"w") as f: json.dump(d,f,separators=(",",":")); f.write("\n"); f.flush(); os.fsync(f.fileno())
os.chmod(tmp,0o600); os.replace(tmp,p)
__PP_CHECKPOINT__
printf 'OWNER_CHECKPOINT_{route.value}=PASS\n'
'''


def resume_probe_script(state: PersistentState) -> str:
    accepted = list(state.accepted_routes)
    pending = state.pending_route()
    pending_value = None if pending is None else pending.value
    expected_json = json.dumps(
        {"run_id": state.run_id, "ports": asdict(state.ports), "accepted": accepted, "pending": pending_value},
        separators=(",", ":"),
    )
    checks: list[str] = []
    cfg_dirs = {Route.I: "/etc/privatpirat/pp-lab-i", Route.II: "/etc/privatpirat/pp-lab-ii", Route.III: "/etc/privatpirat/pp-lab-iii"}
    for route in Route:
        unit = f"pp-lab-{route.value.lower()}.service"
        port = state.ports.for_route(route)
        flag = "-ltn" if route in {Route.I, Route.II} else "-lun"
        if route.value in accepted or route is pending:
            checks += [
                f"systemctl is-active --quiet {unit}",
                f"[ -e /etc/systemd/system/{unit} ]",
                f"[ -e {cfg_dirs[route]} ]",
                f"ss -H {flag} | awk '{{print $4}}' | grep -Eq ':{port}$'",
            ]
        else:
            checks += [
                f"! systemctl is-active --quiet {unit} 2>/dev/null || false",
                f"[ ! -e /etc/systemd/system/{unit} ]",
                f"[ ! -e {cfg_dirs[route]} ]",
                f"! ss -H {flag} | awk '{{print $4}}' | grep -Eq ':{port}$'",
            ]
    return f'''set -euo pipefail
python3 - {REMOTE_ROOT}/owner.json {expected_json!r} <<'__PP_RESUME__'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]); expected=json.loads(sys.argv[2]); d=json.loads(p.read_text())
if d.get("run_id")!=expected["run_id"] or d.get("ports")!=expected["ports"]: raise SystemExit(50)
paths={{"I":"/etc/privatpirat/pp-lab-i/config.json","II":"/etc/privatpirat/pp-lab-ii/config.json","III":"/etc/privatpirat/pp-lab-iii/config.yaml"}}
local_accepted=expected["accepted"]; pending=expected.get("pending")
remote_accepted=d.get("accepted",[])
allowed=[local_accepted]
if pending is not None: allowed.append(local_accepted+[pending])
if remote_accepted not in allowed: raise SystemExit(51)
for r in remote_accepted:
 actual=hashlib.sha256(pathlib.Path(paths[r]).read_bytes()).hexdigest()
 if actual!=d.get("config_sha256",{{}}).get(r): raise SystemExit(52)
__PP_RESUME__
{chr(10).join(checks)}
printf 'RESUME_PROBE=PASS\n'
'''


def finalize_remote_script() -> str:
    return f'''set -euo pipefail
systemctl is-active --quiet pp-lab-i.service; systemctl is-active --quiet pp-lab-ii.service; systemctl is-active --quiet pp-lab-iii.service
rm -f {REMOTE_ROOT}/runtime.json {REMOTE_ROOT}/material-I.json {REMOTE_ROOT}/material-II.json {REMOTE_ROOT}/material-III.json
rm -f {REMOTE_ROOT}/{ARTIFACTS["xray-linux-amd64"].name} {REMOTE_ROOT}/{ARTIFACTS["hysteria-linux-amd64"].name}
printf 'REMOTE_FINALIZE=PASS\n'
'''


class StageExecutor(Protocol):
    def initialize_owner(self, run_id: str) -> None: ...
    def apply(self, route: Route) -> None: ...
    def action(self, route: Route, action: str) -> None: ...
    def fetch_material(self, route: Route) -> RouteMaterial: ...
    def checkpoint(self, run_id: str, route: Route) -> None: ...
    def rollback(self, route: Route) -> None: ...
    def finalize(self) -> None: ...


class ClientVerifier(Protocol):
    def verify(self, route: Route, material: RouteMaterial, rounds: int = 3) -> bool: ...
    def unavailable(self, route: Route, material: RouteMaterial) -> bool: ...


class SSHStageExecutor:
    """Concrete remote executor; unreachable from CLI until R3-SERVER."""

    def __init__(self, session: RemoteSession, ports: Ports, runtime: RuntimePrivateInput, artifacts: Mapping[str, Path], private_dir: Path):
        if session.control_path is None:
            raise BuilderStop("SSH_CONTROLMASTER_REQUIRED=STOP")
        self.session, self.ports, self.runtime, self.artifacts, self.private_dir = session, ports, runtime, artifacts, private_dir
        ensure_private_dir(private_dir)

    def _run(self, script: str, marker: str, timeout: int = 90) -> None:
        try:
            proc = subprocess.run(_ssh_base(self.session) + ["bash", "-s"], input=script, text=True, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise BuilderStop("REMOTE_STAGE_TIMEOUT=STOP") from exc
        if proc.returncode or marker not in proc.stdout.splitlines():
            raise BuilderStop(f"REMOTE_STAGE_FAILED={marker}")

    def _scp_to(self, local: Path, remote: str) -> None:
        cmd = _scp_base(self.session) + [str(local), f"{self.session.user}@{_scp_host(self.session.host)}:{remote}"]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=90)
        if proc.returncode:
            raise BuilderStop("SCP_UPLOAD_FAIL=STOP")

    def _scp_from(self, remote: str, local: Path) -> None:
        ensure_private_dir(local.parent)
        cmd = _scp_base(self.session) + [f"{self.session.user}@{_scp_host(self.session.host)}:{remote}", str(local)]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=90)
        if proc.returncode:
            raise BuilderStop("SCP_DOWNLOAD_FAIL=STOP")
        os.chmod(local, 0o600)

    def initialize_owner(self, run_id: str) -> None:
        self._run(owner_initialize_script(run_id, self.ports), "OWNER_INIT=PASS")
        runtime = self.private_dir / "runtime.json"
        write_private(runtime, json.dumps({"cover_hostname": validate_cover_hostname(self.runtime.cover_hostname)}) + "\n")
        self._scp_to(runtime, f"{REMOTE_ROOT}/runtime.json")
        self._run(f"set -eu\nchmod 0600 {REMOTE_ROOT}/runtime.json\nprintf 'RUNTIME=PASS\\n'\n", "RUNTIME=PASS")

    def apply(self, route: Route) -> None:
        if route is Route.I:
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

    def action(self, route: Route, action: str) -> None:
        self._run(server_action_script(route, self.ports.for_route(route), action), f"SERVER_{action.upper()}_{route.value}=PASS")

    def fetch_material(self, route: Route) -> RouteMaterial:
        local = self.private_dir / f"material-{route.value}.json"; remote = f"{REMOTE_ROOT}/material-{route.value}.json"
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

    def checkpoint(self, run_id: str, route: Route) -> None:
        self._run(owner_checkpoint_script(run_id, route), f"OWNER_CHECKPOINT_{route.value}=PASS")

    def rollback(self, route: Route) -> None:
        self._run(rollback_script(route, self.ports.for_route(route)), f"ROLLBACK_{route.value}=PASS")
        try:
            (self.private_dir / f"material-{route.value}.json").unlink()
        except FileNotFoundError:
            pass

    def finalize(self) -> None:
        self._run(finalize_remote_script(), "REMOTE_FINALIZE=PASS")


class LocalClientVerifier:
    """Ephemeral local clients. DNS resolution uses SOCKS hostname resolution.

    This proves route-level DNS resolution, not Android/Happ browser leak
    behavior. Formal leak-oriented acceptance remains a separate checkpoint.
    """

    def __init__(self, host: str, ports: Ports, runtime: RuntimePrivateInput, expected_egress_ip: str, artifacts: Mapping[str, Path], private_dir: Path):
        self.host = validate_host(host); self.ports = ports; self.runtime = runtime
        self.expected_egress_ip = str(ipaddress.ip_address(expected_egress_ip)); self.artifacts = artifacts; self.private_dir = private_dir
        ensure_private_dir(private_dir)

    @staticmethod
    def _free_local_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0)); return int(sock.getsockname()[1])

    @staticmethod
    def _wait_socks(port: int, proc: subprocess.Popen[str]) -> bool:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if proc.poll() is not None: return False
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.2): return True
            except OSError: time.sleep(.15)
        return False

    @staticmethod
    def _curl_status_body(socks_port: int, url: str) -> tuple[int, str]:
        cmd = ["curl", "--silent", "--show-error", "--max-time", "20", "--socks5-hostname", f"127.0.0.1:{socks_port}", "--write-out", "\\n%{http_code}", url]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=25)
        if proc.returncode or "\n" not in proc.stdout:
            raise BuilderStop("CLIENT_DATA_PATH_FAIL=STOP")
        body, raw_status = proc.stdout.rsplit("\n", 1)
        try: status = int(raw_status)
        except ValueError as exc: raise BuilderStop("CLIENT_HTTP_STATUS_INVALID=STOP") from exc
        if not body.strip() or not 200 <= status < 400:
            raise BuilderStop("CLIENT_HTTP_BODY_OR_STATUS_FAIL=STOP")
        return status, body

    @staticmethod
    def _curl_text(socks_port: int, url: str) -> str:
        cmd = ["curl", "--fail", "--silent", "--show-error", "--max-time", "20", "--socks5-hostname", f"127.0.0.1:{socks_port}", url]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=25)
        if proc.returncode or not proc.stdout.strip(): raise BuilderStop("CLIENT_DATA_PATH_FAIL=STOP")
        return proc.stdout.strip()

    def _command(self, route: Route, material: RouteMaterial, socks_port: int, cfg: Path) -> list[str]:
        if route in {Route.I, Route.II}:
            write_private(cfg, render_xray_client_config(route, self.host, self.ports.for_route(route), material, self.runtime.cover_hostname, socks_port))
            return [str(self.artifacts["client_xray"]), "run", "-config", str(cfg)]
        write_private(cfg, render_hysteria_client_config(self.host, self.ports.route_iii_udp, material, socks_port))
        return [str(self.artifacts["client_hysteria"]), "client", "-c", str(cfg)]

    def _verify_round(self, route: Route, material: RouteMaterial, index: int) -> bool:
        socks = self._free_local_port(); cfg = self.private_dir / f"verify-{route.value}-{index}.conf"; cmd = self._command(route, material, socks, cfg)
        proc = subprocess.Popen(cmd, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            if not self._wait_socks(socks, proc): return False
            self._curl_status_body(socks, HTTP_PROBE_URL); self._curl_status_body(socks, HTTPS_PROBE_URL)
            exits = []
            for url in EXIT_IP_URLS:
                exits.append(str(ipaddress.ip_address(self._curl_text(socks, url))))
            return len(set(exits)) == 1 and secrets.compare_digest(exits[0], self.expected_egress_ip)
        except (BuilderStop, ValueError):
            return False
        finally:
            proc.terminate()
            try: proc.wait(timeout=3)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=3)
            try: cfg.unlink()
            except FileNotFoundError: pass

    def verify(self, route: Route, material: RouteMaterial, rounds: int = 3) -> bool:
        if rounds < 1: raise ValueError("rounds must be >= 1")
        return all(self._verify_round(route, material, idx) for idx in range(1, rounds + 1))

    def unavailable(self, route: Route, material: RouteMaterial) -> bool:
        return not self._verify_round(route, material, 0)


def write_client_bundle(directory: Path, host: str, ports: Ports, runtime: RuntimePrivateInput, materials: Mapping[Route, RouteMaterial]) -> list[Path]:
    ensure_private_dir(directory); written: list[Path] = []
    for route in Route:
        material = materials[route]
        if route in {Route.I, Route.II}:
            text = render_xray_client_config(route, host, ports.for_route(route), material, runtime.cover_hostname, 10808); suffix = "json"
        else:
            text = render_hysteria_client_config(host, ports.route_iii_udp, material, 10808); suffix = "yaml"
        config_path = directory / f"{slugify(runtime.profile_name)}-{route.value}.{suffix}"
        uri_path = directory / f"{slugify(runtime.profile_name)}-{route.value}.uri"
        write_private(config_path, text); write_private(uri_path, render_share_uri(route, host, ports.for_route(route), material, runtime.cover_hostname, runtime.profile_name) + "\n")
        written.extend([config_path, uri_path])
    manifest = directory / "manifest.json"
    write_private(manifest, json.dumps({"builder_version": BUILDER_VERSION, "profile_name": runtime.profile_name, "routes": [r.value for r in Route], "files": [p.name for p in written]}, ensure_ascii=False, indent=2) + "\n")
    written.append(manifest); return written


def load_materials(private_dir: Path, accepted: Sequence[str]) -> dict[Route, RouteMaterial]:
    result: dict[Route, RouteMaterial] = {}
    for value in accepted:
        route = Route(value); path = private_dir / f"material-{route.value}.json"
        try: raw = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc: raise BuilderStop("RESUME_MATERIAL_MISSING=STOP") from exc
        if not isinstance(raw, dict): raise BuilderStop("RESUME_MATERIAL_INVALID=STOP")
        result[route] = RouteMaterial.from_mapping(raw)
    return result


class DeploymentEngine:
    """Server-stage engine with restart/data-path and stop/start isolation.

    Formal multi-network acceptance is tracked separately by AcceptanceLedger;
    this engine never upgrades missing network or DNS-leak evidence to PASS.
    """

    def __init__(self, executor: StageExecutor, verifier: ClientVerifier, bundle_dir: Path, host: str, ports: Ports, runtime: RuntimePrivateInput, run_id: str, ledger: AcceptanceLedger | None = None, accepted_materials: Mapping[Route, RouteMaterial] | None = None, accepted_routes: Sequence[Route] | None = None, on_state=None):
        self.executor, self.verifier, self.bundle_dir, self.host, self.ports, self.runtime = executor, verifier, bundle_dir, host, ports, runtime
        self.run_id = run_id; self.ledger = ledger or AcceptanceLedger(); self.materials = dict(accepted_materials or {})
        self.accepted = list(accepted_routes) if accepted_routes is not None else [r for r in Route if r in self.materials]
        if any(route not in self.materials for route in self.accepted):
            raise BuilderStop("ACCEPTED_MATERIAL_MISSING=STOP")
        self.on_state = on_state
        self.state = {0: State.PREFLIGHT_PASS, 1: State.I_PASS, 2: State.II_PASS, 3: State.III_PASS}[len(self.accepted)]

    def _persist(self, failed: Route | None = None) -> None:
        if self.on_state is not None: self.on_state(tuple(r.value for r in self.accepted), self.ledger, failed)

    def initialize(self) -> None:
        if not self.accepted: self.executor.initialize_owner(self.run_id)

    def _previous(self, route: Route) -> list[Route]:
        return {Route.I: [], Route.II: [Route.I], Route.III: [Route.I, Route.II]}[route]

    def _fail(self, route: Route, error: Exception) -> None:
        self.ledger.reset_route_evidence(route); self.ledger.failed_routes.add(route.value); self.state = State.STAGE_FAIL
        try: self.executor.rollback(route)
        except Exception as rollback_error:
            self.state = State.STOPPED; self._persist(route); raise BuilderStop("ROLLBACK_VERIFICATION_FAIL=STOP") from rollback_error
        self.state = State.ROLLED_BACK; self._persist(route); self.state = State.STOPPED
        raise BuilderStop(f"STAGE_{route.value}_FAIL=STOP") from error

    def _accept_current_network(self, route: Route, network: NetworkClass) -> None:
        material = self.materials[route]
        if not self.verifier.verify(route, material, rounds=3): raise BuilderStop("CLIENT_ACCEPTANCE_FAIL=STOP")
        self.ledger.mark_data_path(route, network)
        for prior in self._previous(route):
            if not self.verifier.verify(prior, self.materials[prior], rounds=3): raise BuilderStop(f"REGRESSION_{prior.value}_FAIL=STOP")
            self.ledger.mark_regression(route, prior, network)

    def _restart_and_isolation(self, route: Route) -> None:
        material = self.materials[route]
        self.executor.action(route, "restart")
        if not self.verifier.verify(route, material, rounds=1): raise BuilderStop("RESTART_DATA_PATH_FAIL=STOP")
        self.ledger.restart[route.value] = True
        self.executor.action(route, "stop")
        if not self.verifier.unavailable(route, material): raise BuilderStop("STOP_ISOLATION_ROUTE_STILL_AVAILABLE=STOP")
        for prior in self._previous(route):
            if not self.verifier.verify(prior, self.materials[prior], rounds=1): raise BuilderStop("STOP_ISOLATION_REGRESSION_FAIL=STOP")
        self.executor.action(route, "start")
        if not self.verifier.verify(route, material, rounds=1): raise BuilderStop("START_RECOVERY_DATA_PATH_FAIL=STOP")
        self.ledger.isolation[route.value] = True

    def build_route(self, route: Route, network: NetworkClass) -> None:
        expected_index = len(self.accepted)
        if expected_index >= len(Route) or list(Route)[expected_index] is not route:
            raise BuilderStop("ROUTE_ORDER_INVALID=STOP")
        previous = self._previous(route)
        if previous and self.route_verdict(previous[-1]) is not Verdict.PASS:
            raise BuilderStop("PREVIOUS_ROUTE_NOT_FORMALLY_ACCEPTED=STOP")
        self.ledger.reset_route_evidence(route)
        self.ledger.failed_routes.discard(route.value)
        self.state = {Route.I: State.I_APPLYING, Route.II: State.II_APPLYING, Route.III: State.III_APPLYING}[route]
        try:
            self.executor.apply(route); self.executor.action(route, "health"); material = self.executor.fetch_material(route); self.materials[route] = material
            self._accept_current_network(route, network); self._restart_and_isolation(route)
            # The route is installed but deliberately not durable/accepted yet.
            # Formal acceptance requires the second target network and the
            # leak-oriented DNS checkpoint before owner checkpointing.
            self._persist()
        except KeyboardInterrupt as exc:
            self.materials.pop(route, None); self._fail(route, exc)
        except Exception as exc:
            self.materials.pop(route, None); self._fail(route, exc)

    def accept_network(self, route: Route, network: NetworkClass) -> None:
        if route not in self.materials: raise BuilderStop("ROUTE_NOT_BUILT=STOP")
        try:
            if not self.verifier.verify(route, self.materials[route], rounds=3):
                raise BuilderStop("NETWORK_ACCEPTANCE_FAIL=STOP")
            self.ledger.mark_data_path(route, network)
            for prior in self._previous(route):
                if not self.verifier.verify(prior, self.materials[prior], rounds=3):
                    raise BuilderStop("NETWORK_REGRESSION_FAIL=STOP")
                self.ledger.mark_regression(route, prior, network)
            self._persist()
        except Exception as exc:
            if route not in self.accepted:
                self.materials.pop(route, None)
                self._fail(route, exc)
            self.ledger.failed_routes.add(route.value); self._persist(route); raise

    def mark_dns_leak_checkpoint(self, route: Route, passed: bool) -> None:
        if route not in self.materials:
            raise BuilderStop("ROUTE_NOT_BUILT=STOP")
        if passed:
            self.ledger.dns_leak_checkpoint[route.value] = True
            self._persist()
        else:
            self.abandon_pending(route, failed=True)
            raise BuilderStop("DNS_LEAK_CHECKPOINT_FAIL=STOP")

    def abandon_pending(self, route: Route, *, failed: bool) -> None:
        if route in self.accepted or route not in self.materials:
            raise BuilderStop("NO_PENDING_ROUTE_TO_ROLLBACK=STOP")
        self.ledger.reset_route_evidence(route)
        if failed:
            self.ledger.failed_routes.add(route.value)
        else:
            self.ledger.failed_routes.discard(route.value)
        try:
            self.executor.rollback(route)
        except Exception as exc:
            self.state = State.STOPPED; self._persist(route); raise BuilderStop("ROLLBACK_VERIFICATION_FAIL=STOP") from exc
        self.materials.pop(route, None); self.state = State.STOPPED; self._persist(route if failed else None)

    def accept_route(self, route: Route) -> None:
        if route in self.accepted:
            return
        if route not in self.materials:
            raise BuilderStop("ROUTE_NOT_BUILT=STOP")
        if self.route_verdict(route) is not Verdict.PASS:
            raise BuilderStop("ROUTE_FORMAL_ACCEPTANCE_PARTIAL=STOP")
        try:
            self.executor.checkpoint(self.run_id, route)
        except Exception as exc:
            self.materials.pop(route, None); self._fail(route, exc)
        self.accepted.append(route); self.ledger.failed_routes.discard(route.value)
        self.state = {Route.I: State.I_PASS, Route.II: State.II_PASS, Route.III: State.III_PASS}[route]; self._persist()

    def route_verdict(self, route: Route) -> Verdict:
        return self.ledger.route_verdict(route)

    def can_advance(self, route: Route) -> bool:
        return route in self.accepted and self.route_verdict(route) is Verdict.PASS

    def finalize(self) -> Verdict:
        if len(self.accepted) != 3: raise BuilderStop("FINALIZE_ROUTES_INCOMPLETE=STOP")
        formal = self.ledger.final_verdict()
        if formal is not Verdict.PASS:
            self._persist(); return formal
        self.state = State.FINAL_REGRESSION_PASS
        write_client_bundle(self.bundle_dir, self.host, self.ports, self.runtime, self.materials)
        self.state = State.CLIENT_BUNDLE_READY; self.executor.finalize(); self.state = State.PASS; self._persist(); return Verdict.PASS


def perform_target_inputs(args: argparse.Namespace) -> tuple[str, str, str, int, str, str, Path]:
    name = args.profile_name or input("Profile name: ").strip(); slug = slugify(name)
    host = getpass.getpass("Target VPS IP/hostname: ").strip(); user = input("SSH login: ").strip()
    fingerprint = getpass.getpass("Expected SSH ED25519 fingerprint (SHA256:...): ").strip(); raw_port = input("SSH port [22]: ").strip()
    if raw_port and (not raw_port.isdigit() or not 1 <= int(raw_port) <= 65535): raise BuilderStop("SSH_PORT_INVALID=STOP")
    port = int(raw_port or 22); private = private_root() / slug; known = pin_host_key(host, port, fingerprint, private)
    return name, slug, validate_host(host), port, validate_user(user), validate_fingerprint(fingerprint), known


def preflight_session(name: str, slug: str, host: str, port: int, user: str, fingerprint: str, session: RemoteSession, *, resume: PersistentState | None = None) -> PreflightContext:
    inv = remote_inventory(session)
    if resume is None:
        checks = assert_inventory(inv, require_clean=True); ports = select_ports(inv)
    else:
        binding = target_binding(host, user, port, fingerprint)
        if not secrets.compare_digest(binding, resume.target_binding): raise BuilderStop("RESUME_TARGET_MISMATCH=STOP")
        checks = assert_inventory(inv, require_clean=False); ports = resume.ports
        proc = subprocess.run(_ssh_base(session) + ["bash", "-s"], input=resume_probe_script(resume), text=True, capture_output=True, timeout=45)
        if proc.returncode or "RESUME_PROBE=PASS" not in proc.stdout.splitlines(): raise BuilderStop("RESUME_REMOTE_STATE_MISMATCH=STOP")
    return PreflightContext(name, slug, session, inv, ports, private_root()/slug, state_root()/slug, checks, target_binding(host,user,port,fingerprint))


def run_preflight(args: argparse.Namespace) -> int:
    if not all(local_prerequisites().values()): raise BuilderStop("LOCAL_PREREQUISITES=FAIL")
    name,slug,host,port,user,fp,known=perform_target_inputs(args); base=RemoteSession(host,user,port,known)
    with SSHControlMaster(base, slug) as session:
        context=preflight_session(name,slug,host,port,user,fp,session)
    report=public_report({"builder_version":BUILDER_VERSION,"phase":"PRECHECK","host_key_match":True,**context.checks,"route_i":"NOT_STARTED","route_ii":"NOT_STARTED","route_iii":"NOT_STARTED","regression":"NOT_STARTED","client_bundle":"NOT_READY","formal_acceptance":"NOT_STARTED","verdict":"PREFLIGHT_PASS","error":None})
    for k,v in report.items():
        if v is not None: print(f"{k.upper()}={v}")
    return 0


def _confirm_network(network: NetworkClass) -> NetworkClass:
    expected = network.value.upper()
    answer = input(f"Switch the phone to {expected}, then type {expected}: ").strip().upper()
    if answer != expected:
        raise BuilderStop("NETWORK_CLASS_NOT_CONFIRMED=STOP")
    return network


def _dns_checkpoint(engine: DeploymentEngine, route: Route) -> None:
    answer = input(
        f"Leak-oriented DNS checkpoint for route {route.value} [PASS/SKIP/FAIL]: "
    ).strip().upper()
    if answer == "PASS":
        engine.mark_dns_leak_checkpoint(route, True)
        return
    if answer == "SKIP":
        engine.abandon_pending(route, failed=False)
        raise BuilderStop("FORMAL_ACCEPTANCE_PARTIAL_DNS_CHECKPOINT_MISSING=STOP")
    if answer == "FAIL":
        engine.mark_dns_leak_checkpoint(route, False)
    raise BuilderStop("DNS_LEAK_CHECKPOINT_INPUT_INVALID=STOP")


def _write_acceptance_profile(directory: Path, host: str, ports: Ports, runtime: RuntimePrivateInput, route: Route, material: RouteMaterial) -> Path:
    ensure_private_dir(directory)
    path = directory / f"{slugify(runtime.profile_name)}-{route.value}.uri"
    write_private(path, render_share_uri(route, host, ports.for_route(route), material, runtime.cover_hostname, runtime.profile_name) + "\n")
    return path


def _load_runtime(private_dir: Path, profile_name: str) -> RuntimePrivateInput:
    try:
        raw = json.loads((private_dir / "runtime.json").read_text(encoding="utf-8"))
        cover = validate_cover_hostname(str(raw["cover_hostname"]))
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as exc:
        raise BuilderStop("RESUME_RUNTIME_PRIVATE_INPUT_MISSING=STOP") from exc
    return RuntimePrivateInput(profile_name, cover)


def run_deployment_after_gate(args: argparse.Namespace) -> int:
    """Complete Builder run, deliberately unreachable while --apply is gated.

    The only human actions are private target input, physical Wi-Fi/mobile
    switching, and leak-oriented DNS acceptance. No route-by-route server
    configuration is delegated to the human.
    """
    if not all(local_prerequisites().values()):
        raise BuilderStop("LOCAL_PREREQUISITES=FAIL")
    name, slug, host, port, user, fp, known = perform_target_inputs(args)
    base = RemoteSession(host, user, port, known)
    state_path = state_root() / slug / "state.json"
    existing: PersistentState | None = None
    if state_path.exists():
        existing = load_state(state_path)
        if existing.accepted_routes == ("I", "II", "III") and existing.ledger.final_verdict() is Verdict.PASS:
            raise BuilderStop("COMPLETED_RUN_REUSE_FORBIDDEN=STOP")
        if not existing.accepted_routes and existing.last_failed_route == "I":
            # Route I rollback restores the clean-room server; that failed run
            # cannot be resumed because the remote owner marker is gone.
            raise BuilderStop("FAILED_I_REQUIRES_NEW_CLEAN_RUN_STATE=STOP")

    with SSHControlMaster(base, slug) as session:
        if existing is None:
            context = preflight_session(name, slug, host, port, user, fp, session)
            cover = validate_cover_hostname(getpass.getpass("REALITY cover hostname (private): ").strip())
            remote_cover_probe(session, cover)
            runtime = RuntimePrivateInput(name, cover)
            write_private(context.private_dir / "runtime.json", json.dumps({"cover_hostname": cover}) + "\n")
            state = PersistentState(
                BUILDER_VERSION, secrets.token_hex(16), context.target_binding, (),
                context.ports, AcceptanceLedger(), None,
            )
            save_state(state_path, state)
        else:
            context = preflight_session(name, slug, host, port, user, fp, session, resume=existing)
            runtime = _load_runtime(context.private_dir, name)
            state = existing

        artifacts = prepare_artifacts(cache_root() / slug)
        material_routes = list(state.accepted_routes)
        pending = state.pending_route()
        if pending is not None:
            material_routes.append(pending.value)
        accepted_materials = load_materials(context.private_dir, material_routes)
        executor = SSHStageExecutor(session, context.ports, runtime, artifacts, context.private_dir)
        verifier = LocalClientVerifier(host, context.ports, runtime, context.inventory.egress_ip, artifacts, context.private_dir / "verify")

        def persist(accepted: tuple[str, ...], ledger: AcceptanceLedger, failed: Route | None) -> None:
            nonlocal state
            state = PersistentState(
                BUILDER_VERSION, state.run_id, context.target_binding, accepted,
                context.ports, ledger, None if failed is None else failed.value,
            )
            save_state(state_path, state)

        engine = DeploymentEngine(
            executor, verifier, context.private_dir / "client-bundle", host,
            context.ports, runtime, state.run_id, state.ledger,
            accepted_materials=accepted_materials, accepted_routes=[Route(value) for value in state.accepted_routes], on_state=persist,
        )
        if existing is None:
            engine.initialize()
        current_network: NetworkClass | None = None

        def ensure_network(target: NetworkClass) -> NetworkClass:
            nonlocal current_network
            if current_network is not target:
                current_network = _confirm_network(target)
            return current_network

        # Minimal-switch formal acceptance sequence:
        # Wi-Fi: I build + DNS; mobile: I acceptance + II build;
        # Wi-Fi: II acceptance + DNS + III build + DNS;
        # mobile: III acceptance + final regressions.
        if Route.I not in engine.materials:
            ensure_network(NetworkClass.WIFI)
            engine.build_route(Route.I, NetworkClass.WIFI)
            _write_acceptance_profile(context.private_dir / "acceptance", host, context.ports, runtime, Route.I, engine.materials[Route.I])
        if not engine.ledger.dns_leak_checkpoint["I"]:
            if NetworkClass.WIFI.value not in engine.ledger.data_path["I"]:
                ensure_network(NetworkClass.WIFI)
                engine.accept_network(Route.I, NetworkClass.WIFI)
            ensure_network(NetworkClass.WIFI)
            _dns_checkpoint(engine, Route.I)
        if NetworkClass.MOBILE.value not in engine.ledger.data_path["I"]:
            ensure_network(NetworkClass.MOBILE)
            engine.accept_network(Route.I, NetworkClass.MOBILE)
        engine.accept_route(Route.I)
        if not engine.can_advance(Route.I):
            raise BuilderStop("ROUTE_I_FORMAL_ACCEPTANCE_PARTIAL=STOP")

        if Route.II not in engine.materials:
            ensure_network(NetworkClass.MOBILE)
            engine.build_route(Route.II, NetworkClass.MOBILE)
            _write_acceptance_profile(context.private_dir / "acceptance", host, context.ports, runtime, Route.II, engine.materials[Route.II])
        if NetworkClass.WIFI.value not in engine.ledger.data_path["II"]:
            ensure_network(NetworkClass.WIFI)
            engine.accept_network(Route.II, NetworkClass.WIFI)
        if not engine.ledger.dns_leak_checkpoint["II"]:
            ensure_network(NetworkClass.WIFI)
            _dns_checkpoint(engine, Route.II)
        engine.accept_route(Route.II)
        if not engine.can_advance(Route.II):
            raise BuilderStop("ROUTE_II_FORMAL_ACCEPTANCE_PARTIAL=STOP")

        if Route.III not in engine.materials:
            ensure_network(NetworkClass.WIFI)
            engine.build_route(Route.III, NetworkClass.WIFI)
            _write_acceptance_profile(context.private_dir / "acceptance", host, context.ports, runtime, Route.III, engine.materials[Route.III])
        if not engine.ledger.dns_leak_checkpoint["III"]:
            ensure_network(NetworkClass.WIFI)
            _dns_checkpoint(engine, Route.III)
        if NetworkClass.MOBILE.value not in engine.ledger.data_path["III"]:
            ensure_network(NetworkClass.MOBILE)
            engine.accept_network(Route.III, NetworkClass.MOBILE)
        engine.accept_route(Route.III)

        formal = engine.finalize()
        report = public_report({
            "builder_version": BUILDER_VERSION, "phase": "FINAL", "host_key_match": True,
            **context.checks,
            "route_i": engine.route_verdict(Route.I).value,
            "route_ii": engine.route_verdict(Route.II).value,
            "route_iii": engine.route_verdict(Route.III).value,
            "regression": "PASS" if formal is Verdict.PASS else "PARTIAL",
            "client_bundle": "READY" if formal is Verdict.PASS else "NOT_READY",
            "formal_acceptance": formal.value,
            "verdict": formal.value,
            "error": None,
        })
        for key, value in report.items():
            if value is not None:
                print(f"{key.upper()}={value}")
        return 0 if formal is Verdict.PASS else 4


def render_check() -> int:
    i=RouteMaterial(Route.I,uuid="123e4567-e89b-12d3-a456-426614174000",public_key="A"*43,short_id="aabbccddeeff0011")
    ii=RouteMaterial(Route.II,uuid="123e4567-e89b-12d3-a456-426614174001",public_key="B"*43,short_id="1122334455667788",xhttp_path="/0123456789abcdef")
    iii=RouteMaterial(Route.III,auth="a"*64,pin_sha256="b"*64)
    render_xray_server_config(Route.I,23451,i,"cover.example","C"*43); render_xray_server_config(Route.II,23452,ii,"cover.example","D"*43)
    render_xray_client_config(Route.I,"192.0.2.10",23451,i,"cover.example",10808); render_xray_client_config(Route.II,"192.0.2.10",23452,ii,"cover.example",10808)
    render_hysteria_server_config(23453,iii.auth or "","/tmp/cert","/tmp/key"); render_hysteria_client_config("192.0.2.10",23453,iii,10808)
    if shutil.which("bash"):
        state=PersistentState(BUILDER_VERSION,"a"*32,"b"*64,("I",),Ports(23451,23452,23453),AcceptanceLedger())
        scripts=[stage_i_apply_script(23451),stage_ii_apply_script(23452),stage_iii_apply_script(23453),server_action_script(Route.I,23451,"restart"),server_action_script(Route.II,23452,"stop"),rollback_script(Route.III,23453),owner_initialize_script("a"*32,Ports(23451,23452,23453)),owner_checkpoint_script("a"*32,Route.I),resume_probe_script(state),finalize_remote_script()]
        for script in scripts:
            proc=subprocess.run(["bash","-n"],input=script,text=True,capture_output=True)
            if proc.returncode: print("RENDER_CHECK=FAIL"); return 2
    print("RENDER_CHECK=PASS"); return 0


def build_parser() -> argparse.ArgumentParser:
    parser=argparse.ArgumentParser(prog="pp-build"); mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local-check",action="store_true"); mode.add_argument("--render-check",action="store_true"); mode.add_argument("--preflight-only",action="store_true"); mode.add_argument("--apply",action="store_true",help="execute reviewed deployment flow after explicit R3-SERVER authorization")
    parser.add_argument("--profile-name"); return parser


def main(argv: Sequence[str] | None = None) -> int:
    os.umask(0o077); args=build_parser().parse_args(argv)
    try:
        if args.local_check:
            result=local_prerequisites()
            for key in sorted(result): print(f"LOCAL_{key.upper()}={'PASS' if result[key] else 'FAIL'}")
            print(f"LOCAL_CHECK={'PASS' if all(result.values()) else 'FAIL'}"); return 0 if all(result.values()) else 2
        if args.render_check: return render_check()
        if args.apply:
            return run_deployment_after_gate(args)
        return run_preflight(args)
    except BuilderStop as exc:
        print(sanitize_error(str(exc))); print("VERDICT=STOP"); return 2
    except KeyboardInterrupt:
        print("INTERRUPTED=STOP"); return 130
    except Exception as exc:
        print(f"UNEXPECTED={sanitize_error(str(exc))}"); print("VERDICT=STOP"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
