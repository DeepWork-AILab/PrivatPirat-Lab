#!/usr/bin/env python3
"""PrivatPirat Reproducible Node Builder v0.1 foundation.

This checkpoint implements only safe foundation/preflight behavior.  Remote
mutation is intentionally disabled until deployment stages are separately
implemented, reviewed, and authorized by R3-SERVER.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import ipaddress
import json
import os
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from typing import Mapping, Sequence

BUILDER_VERSION = "0.1.0-foundation"
SUPPORTED_OS = ("ubuntu", "24.04", "x86_64")
MIN_MEMORY_KIB = 512 * 1024
MIN_ROOT_FREE_KIB = 1024 * 1024
PORT_MIN, PORT_MAX = 20000, 60000

# Public upstream release metadata pinned for the accepted baseline.
ARTIFACT_SHA256 = {
    "Xray-linux-64.zip": "23cd9af937744d97776ee35ecad4972cf4b2109d1e0fe6be9930467608f7c8ae",
    "Xray-android-arm64-v8a.zip": "57149ffd48b629c07bf76938e73ab2729fde5910091497eab3e93d1c190f4c1b",
    "hysteria-linux-amd64": "ffc032c7ca6b78676d337097ca7f61bebc3a90a4f3a656693adf368f304cdbc7",
    "hysteria-android-arm64": "92728ca71dee10508040939c0c99e69f8800519fcedb6ec35eed92b90f1b2a5f",
}


class BuilderStop(RuntimeError):
    pass


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
    State.FINAL_REGRESSION_PASS: {State.CLIENT_BUNDLE_READY, State.STAGE_FAIL},
    State.CLIENT_BUNDLE_READY: {State.PASS, State.STAGE_FAIL},
    State.STAGE_FAIL: {State.ROLLED_BACK, State.STOPPED},
    State.ROLLED_BACK: {State.STOPPED},
    State.PASS: set(),
    State.STOPPED: set(),
}

PUBLIC_FIELDS = frozenset({
    "builder_version", "phase", "host_key_match", "os_supported",
    "arch_supported", "resources_supported", "clean_room", "firewall_clear",
    "route_i", "route_ii", "route_iii", "regression", "client_bundle",
    "verdict", "error",
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
    ufw_state: str
    nft_nonempty: bool
    relevant_found: bool
    listen_tcp: frozenset[int]
    listen_udp: frozenset[int]


@dataclass(frozen=True)
class Ports:
    route_i_tcp: int
    route_ii_tcp: int
    route_iii_udp: int


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
for d in /etc/xray /usr/local/etc/xray /etc/hysteria /etc/hysteria2 /etc/privatpirat /usr/local/lib/privatpirat; do [ -e "$d" ] && r=1 || true; done
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files --no-legend --no-pager 2>/dev/null | grep -Eiq '(xray|hysteria|privatpirat)'; then r=1; fi
printf 'RELEVANT_FOUND=%s\n' "$r"
if command -v ss >/dev/null 2>&1; then
  tcp="$(ss -H -ltn 2>/dev/null | awk '{print $4}' | sed -E 's/.*:([0-9]+)$/\1/' | grep -E '^[0-9]+$' | sort -nu | paste -sd, - || true)"
  udp="$(ss -H -lun 2>/dev/null | awk '{print $4}' | sed -E 's/.*:([0-9]+)$/\1/' | grep -E '^[0-9]+$' | sort -nu | paste -sd, - || true)"
else tcp=""; udp=""; fi
printf 'LISTEN_TCP=%s\n' "$tcp"
printf 'LISTEN_UDP=%s\n' "$udp"
'''


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
        try: os.unlink(tmp)
        except FileNotFoundError: pass
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
    required = {"OS_ID","OS_VERSION","ARCH","UID","CPU_COUNT","MEM_KIB","ROOT_FREE_KIB","SYSTEMD","SS","OPENSSL","SHA256SUM","UFW_STATE","NFT_NONEMPTY","RELEVANT_FOUND","LISTEN_TCP","LISTEN_UDP"}
    if required - values.keys():
        raise BuilderStop("INVENTORY_MISSING_FIELDS=STOP")
    try:
        return Inventory(values["OS_ID"].lower(), values["OS_VERSION"], values["ARCH"], int(values["UID"]), int(values["CPU_COUNT"]), int(values["MEM_KIB"]), int(values["ROOT_FREE_KIB"]), values["SYSTEMD"] == "1", values["SS"] == "1", values["OPENSSL"] == "1", values["SHA256SUM"] == "1", values["UFW_STATE"], values["NFT_NONEMPTY"] == "1", values["RELEVANT_FOUND"] == "1", parse_ports(values["LISTEN_TCP"]), parse_ports(values["LISTEN_UDP"]))
    except ValueError as exc:
        raise BuilderStop("INVENTORY_PARSE_FAIL=STOP") from exc


def evaluate_inventory(inv: Inventory) -> dict[str, bool]:
    os_ok = (inv.os_id, inv.os_version) == SUPPORTED_OS[:2]
    arch_ok = inv.arch == SUPPORTED_OS[2]
    resources_ok = inv.cpu_count >= 1 and inv.mem_kib >= MIN_MEMORY_KIB and inv.root_free_kib >= MIN_ROOT_FREE_KIB
    clean = inv.uid == 0 and inv.systemd and inv.ss and inv.openssl and inv.sha256sum and not inv.relevant_found
    firewall = inv.ufw_state in {"absent", "inactive"} and not inv.nft_nonempty
    return {"os_supported": os_ok, "arch_supported": arch_ok, "resources_supported": resources_ok, "clean_room": clean, "firewall_clear": firewall}


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
    try: ipaddress.ip_address(host); return host
    except ValueError: pass
    if not re.fullmatch(r"(?i)[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", host):
        raise BuilderStop("TARGET_HOST_INVALID=STOP")
    return host


def validate_user(user: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,31}", user.strip()):
        raise BuilderStop("SSH_USER_INVALID=STOP")
    return user.strip()


def validate_fingerprint(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"SHA256:[A-Za-z0-9+/]{43}=?", value):
        raise BuilderStop("HOST_KEY_FINGERPRINT_INVALID=STOP")
    return value


def pin_host_key(host: str, port: int, expected: str, directory: Path) -> Path:
    host, expected = validate_host(host), validate_fingerprint(expected)
    ensure_private_dir(directory)
    candidate, known = directory / "known_hosts.candidate", directory / "known_hosts"
    try:
        scan = subprocess.run(["ssh-keyscan","-T","8","-p",str(port),"-t","ed25519",host], text=True, capture_output=True, timeout=12)
        if scan.returncode or not scan.stdout.strip(): raise BuilderStop("HOST_KEY_SCAN_FAIL=STOP")
        write_private(candidate, scan.stdout)
        fp = subprocess.run(["ssh-keygen","-lf",str(candidate)], text=True, capture_output=True, timeout=8)
        match = re.search(r"\b(SHA256:[A-Za-z0-9+/]{43}=?)\b", fp.stdout) if not fp.returncode else None
        if not match: raise BuilderStop("HOST_KEY_PARSE_FAIL=STOP")
        if not secrets.compare_digest(match.group(1), expected): raise BuilderStop("HOST_KEY_MISMATCH=STOP")
        write_private(known, scan.stdout)
        return known
    finally:
        try: candidate.unlink()
        except FileNotFoundError: pass


def remote_inventory(host: str, user: str, port: int, known_hosts: Path) -> Inventory:
    cmd = ["ssh","-T","-p",str(port),"-o","StrictHostKeyChecking=yes","-o",f"UserKnownHostsFile={known_hosts}","-o","LogLevel=ERROR",f"{validate_user(user)}@{validate_host(host)}","sh","-s"]
    try:
        proc = subprocess.run(cmd, input=INVENTORY_SCRIPT, text=True, capture_output=True, timeout=45)
    except subprocess.TimeoutExpired as exc:
        raise BuilderStop("SSH_INVENTORY_TIMEOUT=STOP") from exc
    if proc.returncode:
        raise BuilderStop("SSH_INVENTORY_FAIL=STOP")
    return parse_inventory(proc.stdout)


def local_prerequisites() -> dict[str, bool]:
    result = {name: shutil.which(name) is not None for name in ("ssh","ssh-keyscan","ssh-keygen","scp","sftp")}
    result["python"] = sys.version_info >= (3, 11)
    return result


def run_preflight(args: argparse.Namespace) -> int:
    prereq = local_prerequisites()
    if not all(prereq.values()): raise BuilderStop("LOCAL_PREREQUISITES=FAIL")
    name = args.profile_name or input("Profile name: ").strip()
    slug = slugify(name)
    host = getpass.getpass("Target VPS IP/hostname: ").strip()
    user = input("SSH login: ").strip()
    fingerprint = getpass.getpass("Expected SSH ED25519 fingerprint (SHA256:...): ").strip()
    raw_port = input("SSH port [22]: ").strip()
    if raw_port and (not raw_port.isdigit() or not 1 <= int(raw_port) <= 65535): raise BuilderStop("SSH_PORT_INVALID=STOP")
    port = int(raw_port or 22)
    private = private_root() / slug
    known = pin_host_key(host, port, fingerprint, private)
    inv = remote_inventory(host, user, port, known)
    checks = assert_inventory(inv)
    ports = select_ports(inv)
    state_dir = state_root() / slug
    write_private(state_dir / "state.json", json.dumps({"builder_version":BUILDER_VERSION,"display_name":name,"slug":slug,"state":State.PREFLIGHT_PASS.value,"route_ports":asdict(ports)}, ensure_ascii=False, indent=2) + "\n")
    report = public_report({"builder_version":BUILDER_VERSION,"phase":"PRECHECK","host_key_match":True,**checks,"route_i":"NOT_STARTED","route_ii":"NOT_STARTED","route_iii":"NOT_STARTED","regression":"NOT_STARTED","client_bundle":"NOT_READY","verdict":"PREFLIGHT_PASS","error":None})
    for key, value in report.items():
        if value is not None: print(f"{key.upper()}={value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pp-build")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local-check", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--apply", action="store_true", help="disabled until a later reviewed checkpoint")
    parser.add_argument("--profile-name")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    os.umask(0o077)
    args = build_parser().parse_args(argv)
    try:
        if args.local_check:
            result = local_prerequisites()
            for key in sorted(result): print(f"LOCAL_{key.upper()}={'PASS' if result[key] else 'FAIL'}")
            print(f"LOCAL_CHECK={'PASS' if all(result.values()) else 'FAIL'}")
            return 0 if all(result.values()) else 2
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
