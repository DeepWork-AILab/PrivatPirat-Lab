import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock

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
PYTHON3=1
UFW_STATE=inactive
NFT_NONEMPTY=0
RELEVANT_FOUND=0
LISTEN_TCP=22,80
LISTEN_UDP=53
EGRESS_A=192.0.2.44
EGRESS_B=192.0.2.44
"""

I = pp.RouteMaterial(
    pp.Route.I,
    uuid="123e4567-e89b-12d3-a456-426614174000",
    public_key="A" * 43,
    short_id="aabbccddeeff0011",
)
II = pp.RouteMaterial(
    pp.Route.II,
    uuid="123e4567-e89b-12d3-a456-426614174001",
    public_key="B" * 43,
    short_id="1122334455667788",
    xhttp_path="/0123456789abcdef",
)
III = pp.RouteMaterial(pp.Route.III, auth="a" * 64, pin_sha256="b" * 64)
PORTS = pp.Ports(23451, 23452, 23453)
RUNTIME = pp.RuntimePrivateInput("Foxy Test", "cover.example")


class FakeExecutor:
    def __init__(self, fail_apply=None, fail_verify=None, fail_rollback=None, fail_finalize=False):
        self.fail_apply = fail_apply
        self.fail_verify = fail_verify
        self.fail_rollback = fail_rollback
        self.fail_finalize = fail_finalize
        self.events = []
        self.materials = {pp.Route.I: I, pp.Route.II: II, pp.Route.III: III}

    def apply(self, route):
        self.events.append(("apply", route))
        if route == self.fail_apply:
            raise pp.BuilderStop("apply")

    def verify_server(self, route):
        self.events.append(("verify_server", route))
        if route == self.fail_verify:
            raise pp.BuilderStop("verify")

    def fetch_material(self, route):
        self.events.append(("fetch", route))
        return self.materials[route]

    def rollback(self, route):
        self.events.append(("rollback", route))
        if route == self.fail_rollback:
            raise pp.BuilderStop("rollback")

    def finalize(self):
        self.events.append(("finalize", None))
        if self.fail_finalize:
            raise pp.BuilderStop("finalize")


class FakeVerifier:
    def __init__(self, false_on_calls=()):
        self.false_on_calls = set(false_on_calls)
        self.calls = []

    def verify(self, route, material, rounds=3):
        self.calls.append((route, rounds))
        return len(self.calls) not in self.false_on_calls


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
        self.assertEqual(pp.public_report({"phase": "PRECHECK", "verdict": "PASS"})["verdict"], "PASS")
        with self.assertRaises(ValueError):
            pp.public_report({"server_ip": "203.0.113.1"})

    def test_state_machine(self):
        self.assertEqual(pp.transition(pp.State.NEW, pp.State.PREFLIGHT_PASS), pp.State.PREFLIGHT_PASS)
        with self.assertRaises(pp.BuilderStop):
            pp.transition(pp.State.NEW, pp.State.III_PASS)

    def test_inventory_pass(self):
        inv = pp.parse_inventory(GOOD)
        checks = pp.assert_inventory(inv)
        self.assertTrue(all(checks.values()))
        self.assertEqual(inv.egress_ip, "192.0.2.44")
        self.assertIn(22, inv.listen_tcp)

    def test_existing_service_stops(self):
        inv = pp.parse_inventory(GOOD.replace("RELEVANT_FOUND=0", "RELEVANT_FOUND=1"))
        with self.assertRaises(pp.BuilderStop):
            pp.assert_inventory(inv)

    def test_firewall_stops(self):
        inv = pp.parse_inventory(GOOD.replace("UFW_STATE=inactive", "UFW_STATE=active"))
        with self.assertRaises(pp.BuilderStop):
            pp.assert_inventory(inv)

    def test_egress_mismatch_stops(self):
        inv = pp.parse_inventory(GOOD.replace("EGRESS_B=192.0.2.44", "EGRESS_B=192.0.2.45"))
        with self.assertRaises(pp.BuilderStop):
            pp.assert_inventory(inv)

    def test_python3_is_required(self):
        inv = pp.parse_inventory(GOOD.replace("PYTHON3=1", "PYTHON3=0"))
        with self.assertRaises(pp.BuilderStop):
            pp.assert_inventory(inv)

    def test_ports_unique_and_free(self):
        inv = pp.parse_inventory(GOOD)
        ports = pp.select_ports(inv)
        values = set(pp.asdict(ports).values())
        self.assertEqual(len(values), 3)
        self.assertTrue(values.isdisjoint(inv.listen_tcp | inv.listen_udp))

    def test_artifact_hashes(self):
        self.assertEqual(len(pp.ARTIFACT_SHA256), 4)
        for digest in pp.ARTIFACT_SHA256.values():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(pp.XRAY_VERSION, "26.3.27")
        self.assertEqual(pp.HYSTERIA_VERSION, "2.12.1")

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
        options = {o for action in pp.build_parser()._actions for o in action.option_strings}
        self.assertNotIn("--host", options)
        self.assertNotIn("--expected-host-key", options)
        self.assertNotIn("--ssh-port", options)
        self.assertNotIn("--sni", options)
        self.assertNotIn("--cover", options)

    def test_apply_hard_disabled(self):
        with mock.patch.object(pp, "run_deployment_after_gate") as runner:
            self.assertEqual(pp.main(["--apply"]), 3)
            runner.assert_not_called()

    def test_cover_validation(self):
        self.assertEqual(pp.validate_cover_hostname("Cover.Example."), "cover.example")
        for bad in ("192.0.2.1", "localhost", "bad host.example", "-x.example"):
            with self.assertRaises(pp.BuilderStop):
                pp.validate_cover_hostname(bad)

    def test_ipv6_authority(self):
        self.assertEqual(pp._authority("2001:db8::1", 443), "[2001:db8::1]:443")
        self.assertEqual(pp._scp_host("2001:db8::1"), "[2001:db8::1]")

    def test_route_material_validation(self):
        pp.RouteMaterial.from_mapping({"route": "I", "uuid": I.uuid, "public_key": I.public_key, "short_id": I.short_id})
        pp.RouteMaterial.from_mapping({"route": "II", "uuid": II.uuid, "public_key": II.public_key, "short_id": II.short_id, "xhttp_path": II.xhttp_path})
        pp.RouteMaterial.from_mapping({"route": "III", "auth": III.auth, "pin_sha256": III.pin_sha256})
        with self.assertRaises(pp.BuilderStop):
            pp.RouteMaterial.from_mapping({"route": "I", "private_key": "secret"})

    def test_route_i_server_renderer(self):
        cfg = json.loads(pp.render_xray_server_config(pp.Route.I, 23451, I, "cover.example", "C" * 43))
        inbound = cfg["inbounds"][0]
        self.assertEqual(inbound["streamSettings"]["network"], "raw")
        self.assertEqual(inbound["settings"]["clients"][0]["flow"], "xtls-rprx-vision")
        self.assertEqual(inbound["streamSettings"]["realitySettings"]["target"], "cover.example:443")

    def test_route_ii_server_renderer(self):
        cfg = json.loads(pp.render_xray_server_config(pp.Route.II, 23452, II, "cover.example", "D" * 43))
        inbound = cfg["inbounds"][0]
        self.assertEqual(inbound["streamSettings"]["network"], "xhttp")
        self.assertNotIn("flow", inbound["settings"]["clients"][0])
        self.assertEqual(inbound["streamSettings"]["xhttpSettings"]["path"], II.xhttp_path)

    def test_xray_client_renderers_use_firefox(self):
        for route, material, port in ((pp.Route.I, I, 23451), (pp.Route.II, II, 23452)):
            cfg = json.loads(pp.render_xray_client_config(route, "192.0.2.10", port, material, "cover.example", 10808))
            reality = cfg["outbounds"][0]["streamSettings"]["realitySettings"]
            self.assertEqual(reality["fingerprint"], "firefox")
            self.assertEqual(reality["serverName"], "cover.example")
            self.assertNotIn("privateKey", reality)

    def test_hysteria_renderers_pin_and_password(self):
        server = pp.render_hysteria_server_config(23453, III.auth, "/tmp/cert", "/tmp/key")
        self.assertIn("type: password", server)
        client = pp.render_hysteria_client_config("192.0.2.10", 23453, III, 10808)
        self.assertIn("insecure: true", client)
        self.assertIn(f"pinSHA256: {III.pin_sha256}", client)

    def test_share_uris_are_route_specific(self):
        i_uri = pp.render_share_uri(pp.Route.I, "192.0.2.10", 23451, I, "cover.example", "Foxy")
        ii_uri = pp.render_share_uri(pp.Route.II, "192.0.2.10", 23452, II, "cover.example", "Foxy")
        iii_uri = pp.render_share_uri(pp.Route.III, "192.0.2.10", 23453, III, "cover.example", "Foxy")
        self.assertIn("flow=xtls-rprx-vision", i_uri)
        self.assertIn("type=xhttp", ii_uri)
        self.assertIn("pinSHA256=", iii_uri)
        self.assertNotIn("privateKey", i_uri + ii_uri + iii_uri)

    def test_bundle_permissions_and_manifest_has_no_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = pp.write_client_bundle(Path(tmp) / "bundle", "192.0.2.10", PORTS, RUNTIME, {pp.Route.I: I, pp.Route.II: II, pp.Route.III: III})
            self.assertEqual(len(files), 7)
            for path in files:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            manifest = json.loads((Path(tmp) / "bundle" / "manifest.json").read_text())
            manifest_text = json.dumps(manifest)
            self.assertNotIn(I.uuid, manifest_text)
            self.assertNotIn(III.auth, manifest_text)
            self.assertNotIn("192.0.2.10", manifest_text)

    def test_all_shell_renderers_parse_with_bash(self):
        import shutil
        import subprocess
        if not shutil.which("bash"):
            self.skipTest("bash unavailable")
        scripts = [
            pp.stage_i_apply_script(23451),
            pp.stage_ii_apply_script(23452),
            pp.stage_iii_apply_script(23453),
            pp.server_verify_script(pp.Route.I, 23451),
            pp.server_verify_script(pp.Route.II, 23452),
            pp.server_verify_script(pp.Route.III, 23453),
            pp.rollback_script(pp.Route.I, 23451),
            pp.rollback_script(pp.Route.II, 23452),
            pp.rollback_script(pp.Route.III, 23453),
            pp.finalize_remote_script(),
        ]
        for script in scripts:
            proc = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_stage_scripts_have_native_validation_and_scoped_hash_checks(self):
        i = pp.stage_i_apply_script(23451)
        ii = pp.stage_ii_apply_script(23452)
        iii = pp.stage_iii_apply_script(23453)
        self.assertIn("run -test -config", i)
        self.assertIn("run -test -config", ii)
        self.assertIn("server -c", iii)
        self.assertIn("I_HASH_BEFORE", ii)
        self.assertIn("I_HASH_BEFORE", iii)
        self.assertIn("II_HASH_BEFORE", iii)
        self.assertNotIn("pp-lab-i.service; rm", pp.rollback_script(pp.Route.II, 23452))

    def test_explicit_rollback_verifies_listener_absent(self):
        self.assertIn("! ss -H -ltn", pp.rollback_script(pp.Route.I, 23451))
        self.assertIn(":23451$", pp.rollback_script(pp.Route.I, 23451))
        self.assertIn("! ss -H -lun", pp.rollback_script(pp.Route.III, 23453))

    def test_static_safety_guards(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("sshpass", source)
        self.assertNotIn("StrictHostKeyChecking=no", source)
        self.assertNotIn("UserKnownHostsFile=/dev/null", source)
        self.assertNotRegex(source, r"curl\s+[^\n|]*\|\s*(?:sh|bash)")
        self.assertIn("StrictHostKeyChecking=yes", source)

    def test_render_check(self):
        self.assertEqual(pp.render_check(), 0)

    def test_engine_all_pass(self):
        executor = FakeExecutor()
        verifier = FakeVerifier()
        with tempfile.TemporaryDirectory() as tmp:
            engine = pp.DeploymentEngine(executor, verifier, Path(tmp) / "bundle", "192.0.2.10", PORTS, RUNTIME)
            self.assertEqual(engine.run(), pp.State.PASS)
        self.assertEqual([event for event in executor.events if event[0] == "rollback"], [])
        self.assertEqual(executor.events[-1], ("finalize", None))
        self.assertEqual(verifier.calls, [
            (pp.Route.I, 3),
            (pp.Route.II, 3), (pp.Route.I, 3),
            (pp.Route.III, 3),
            (pp.Route.I, 3), (pp.Route.II, 3),
        ])

    def test_engine_ii_regression_failure_rolls_back_only_ii(self):
        executor = FakeExecutor()
        verifier = FakeVerifier(false_on_calls={3})
        with tempfile.TemporaryDirectory() as tmp:
            engine = pp.DeploymentEngine(executor, verifier, Path(tmp) / "bundle", "192.0.2.10", PORTS, RUNTIME)
            with self.assertRaisesRegex(pp.BuilderStop, "STAGE_II_FAIL"):
                engine.run()
            self.assertEqual(engine.state, pp.State.STOPPED)
        self.assertEqual([event for event in executor.events if event[0] == "rollback"], [("rollback", pp.Route.II)])
        self.assertFalse(any(event == ("apply", pp.Route.III) for event in executor.events))

    def test_engine_iii_server_failure_rolls_back_only_iii(self):
        executor = FakeExecutor(fail_verify=pp.Route.III)
        verifier = FakeVerifier()
        with tempfile.TemporaryDirectory() as tmp:
            engine = pp.DeploymentEngine(executor, verifier, Path(tmp) / "bundle", "192.0.2.10", PORTS, RUNTIME)
            with self.assertRaisesRegex(pp.BuilderStop, "STAGE_III_FAIL"):
                engine.run()
        self.assertEqual([event for event in executor.events if event[0] == "rollback"], [("rollback", pp.Route.III)])

    def test_engine_final_regression_failure_rolls_back_iii(self):
        executor = FakeExecutor()
        verifier = FakeVerifier(false_on_calls={5})
        with tempfile.TemporaryDirectory() as tmp:
            engine = pp.DeploymentEngine(executor, verifier, Path(tmp) / "bundle", "192.0.2.10", PORTS, RUNTIME)
            with self.assertRaisesRegex(pp.BuilderStop, "STAGE_III_FAIL"):
                engine.run()
        self.assertEqual([event for event in executor.events if event[0] == "rollback"], [("rollback", pp.Route.III)])
        self.assertNotIn(("finalize", None), executor.events)

    def test_engine_rollback_failure_stops(self):
        executor = FakeExecutor(fail_verify=pp.Route.II, fail_rollback=pp.Route.II)
        verifier = FakeVerifier()
        with tempfile.TemporaryDirectory() as tmp:
            engine = pp.DeploymentEngine(executor, verifier, Path(tmp) / "bundle", "192.0.2.10", PORTS, RUNTIME)
            with self.assertRaisesRegex(pp.BuilderStop, "ROLLBACK_VERIFICATION_FAIL"):
                engine.run()
            self.assertEqual(engine.state, pp.State.STOPPED)

    def test_engine_finalize_failure_does_not_rollback_accepted_routes(self):
        executor = FakeExecutor(fail_finalize=True)
        verifier = FakeVerifier()
        with tempfile.TemporaryDirectory() as tmp:
            engine = pp.DeploymentEngine(executor, verifier, Path(tmp) / "bundle", "192.0.2.10", PORTS, RUNTIME)
            with self.assertRaisesRegex(pp.BuilderStop, "FINALIZATION_FAIL"):
                engine.run()
        self.assertEqual([event for event in executor.events if event[0] == "rollback"], [])


if __name__ == "__main__":
    unittest.main()
