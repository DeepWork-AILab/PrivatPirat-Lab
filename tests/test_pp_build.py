import importlib.util
from pathlib import Path
import stat
import sys
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "pp-build.py"
spec = importlib.util.spec_from_file_location("pp_build", MODULE_PATH)
pp = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pp
assert spec.loader is not None
spec.loader.exec_module(pp)

GOOD = """OS_ID=ubuntu
OS_VERSION=24.04
ARCH=x86_64
UID=0
CPU_COUNT=2
MEM_KIB=2097152
ROOT_FREE_KIB=50000000
SYSTEMD=1
SS=1
OPENSSL=1
SHA256SUM=1
UFW_STATE=inactive
NFT_NONEMPTY=0
RELEVANT_FOUND=0
LISTEN_TCP=22,80
LISTEN_UDP=53
"""

class Tests(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(pp.slugify("Foxy 🦊 Baby"), "foxy-baby")
        self.assertRegex(pp.slugify("Лиса"), r"^node-[0-9a-f]{10}$")

    def test_sanitizer(self):
        raw = "https://example.invalid/x 203.0.113.7 123e4567-e89b-12d3-a456-426614174000 ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcd"
        safe = pp.sanitize_error(raw)
        self.assertNotIn("203.0.113.7", safe)
        self.assertNotIn("123e4567", safe)
        self.assertIn("[URI REDACTED]", safe)

    def test_public_allowlist(self):
        self.assertEqual(pp.public_report({"phase":"PRECHECK","verdict":"PASS"})["verdict"], "PASS")
        with self.assertRaises(ValueError): pp.public_report({"server_ip":"203.0.113.1"})

    def test_state_machine(self):
        self.assertEqual(pp.transition(pp.State.NEW, pp.State.PREFLIGHT_PASS), pp.State.PREFLIGHT_PASS)
        with self.assertRaises(pp.BuilderStop): pp.transition(pp.State.NEW, pp.State.III_PASS)

    def test_inventory_pass(self):
        inv = pp.parse_inventory(GOOD)
        self.assertTrue(all(pp.assert_inventory(inv).values()))
        self.assertIn(22, inv.listen_tcp)

    def test_existing_service_stops(self):
        inv = pp.parse_inventory(GOOD.replace("RELEVANT_FOUND=0", "RELEVANT_FOUND=1"))
        with self.assertRaises(pp.BuilderStop): pp.assert_inventory(inv)

    def test_firewall_stops(self):
        inv = pp.parse_inventory(GOOD.replace("UFW_STATE=inactive", "UFW_STATE=active"))
        with self.assertRaises(pp.BuilderStop): pp.assert_inventory(inv)

    def test_ports_unique_and_free(self):
        inv = pp.parse_inventory(GOOD)
        ports = pp.select_ports(inv)
        values = set(pp.asdict(ports).values())
        self.assertEqual(len(values), 3)
        self.assertTrue(values.isdisjoint(inv.listen_tcp | inv.listen_udp))

    def test_artifact_hashes(self):
        self.assertEqual(len(pp.ARTIFACT_SHA256), 4)
        for digest in pp.ARTIFACT_SHA256.values(): self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x"
            path.write_bytes(b"abc")
            self.assertTrue(pp.verify_sha256(path, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"))

    def test_private_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d" / "x"
            pp.write_private(path, "x")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)

    def test_sensitive_target_not_cli(self):
        options = {o for a in pp.build_parser()._actions for o in a.option_strings}
        self.assertNotIn("--host", options)
        self.assertNotIn("--expected-host-key", options)
        self.assertNotIn("--ssh-port", options)

    def test_apply_hard_disabled(self):
        self.assertEqual(pp.main(["--apply"]), 3)

if __name__ == "__main__": unittest.main()
