import importlib.util
import hashlib
import json
import os
import subprocess
from contextlib import nullcontext
from pathlib import Path
import re
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
I = pp.RouteMaterial(pp.Route.I, uuid="123e4567-e89b-12d3-a456-426614174000", public_key="A"*43, short_id="aabbccddeeff0011")
II = pp.RouteMaterial(pp.Route.II, uuid="123e4567-e89b-12d3-a456-426614174001", public_key="B"*43, short_id="1122334455667788", xhttp_path="/0123456789abcdef")
III = pp.RouteMaterial(pp.Route.III, auth="a"*64, pin_sha256="b"*64)
PORTS = pp.Ports(23451,23452,23453)
RUNTIME = pp.RuntimePrivateInput("Foxy Test","cover.example")


class FakeExecutor:
    def __init__(self, fail=None):
        self.fail=fail; self.events=[]; self.materials={pp.Route.I:I,pp.Route.II:II,pp.Route.III:III}
    def _event(self, name, route=None):
        self.events.append((name,route))
        if self.fail == (name,route): raise pp.BuilderStop("fake")
    def initialize_owner(self, run_id): self._event("initialize_owner",None)
    def apply(self, route): self._event("apply",route)
    def action(self, route, action): self._event(action,route)
    def fetch_material(self, route): self._event("fetch",route); return self.materials[route]
    def checkpoint(self, run_id, route): self._event("checkpoint",route)
    def capture_diagnostics(self, route): self._event("capture",route); return False
    def snapshot_route_i_config(self, destination): self._event("snapshot",pp.Route.I)
    def rollback(self, route): self._event("rollback",route)
    def finalize(self): self._event("finalize",None)


class FakeVerifier:
    def __init__(self, fail_verify_calls=(), unavailable=True):
        self.fail=set(fail_verify_calls); self.calls=[]; self.unavailable_result=unavailable
    def verify(self, route, material, rounds=3):
        self.calls.append(("verify",route,rounds)); return len(self.calls) not in self.fail
    def unavailable(self, route, material):
        self.calls.append(("unavailable",route,1)); return self.unavailable_result


class Tests(unittest.TestCase):
    def test_slug_and_sanitizer(self):
        self.assertEqual(pp.slugify("Foxy 🦊 Baby"),"foxy-baby")
        raw="https://example.invalid/x 203.0.113.7 123e4567-e89b-12d3-a456-426614174000 ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcd"
        safe=pp.sanitize_error(raw)
        self.assertNotIn("203.0.113.7",safe); self.assertNotIn("123e4567",safe); self.assertIn("[URI REDACTED]",safe)
        self.assertEqual(pp.format_builder_stop("HOST_KEY_FINGERPRINT_INVALID=STOP"),"HOST_KEY_FINGERPRINT_INVALID=STOP")
        self.assertEqual(pp.format_builder_stop("SSH_PASSWORDLESS_SUDO_REQUIRED=STOP"),"SSH_PASSWORDLESS_SUDO_REQUIRED=STOP")

    def test_public_allowlist(self):
        self.assertEqual(pp.public_report({"phase":"PRECHECK","verdict":"PASS"})["verdict"],"PASS")
        with self.assertRaises(ValueError): pp.public_report({"server_ip":"203.0.113.1"})

    def test_inventory_and_ports(self):
        inv=pp.parse_inventory(GOOD); self.assertTrue(all(pp.assert_inventory(inv).values())); self.assertEqual(inv.egress_ip,"192.0.2.44")
        values=set(pp.asdict(pp.select_ports(inv)).values()); self.assertEqual(len(values),3); self.assertTrue(values.isdisjoint(inv.listen_tcp|inv.listen_udp))

    def test_requested_ports_distinguish_tcp_and_udp(self):
        inv=pp.parse_inventory(GOOD)
        requested=pp.parse_requested_ports("443,8443,443")
        self.assertEqual(pp.select_ports(inv,requested),pp.Ports(443,8443,443))
        with self.assertRaisesRegex(pp.BuilderStop,"REQUESTED_PORT_OCCUPIED"):
            pp.select_ports(pp.parse_inventory(GOOD.replace("LISTEN_UDP=53","LISTEN_UDP=53,443")),requested)
        with self.assertRaisesRegex(pp.BuilderStop,"REQUESTED_PORT_OCCUPIED"):
            pp.select_ports(pp.parse_inventory(GOOD.replace("LISTEN_TCP=22,80","LISTEN_TCP=22,80,8443")),requested)
        for invalid in ("443,443,444", "443,8443", "0,8443,443", "443,8443,65536"):
            with self.assertRaisesRegex(pp.BuilderStop,"REQUESTED_PORTS_INVALID"):
                pp.parse_requested_ports(invalid)

    def test_explicit_ssh_identity_requires_private_permissions_and_reaches_ssh_scp(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / "id_ed25519"
            key.write_text("fixture", encoding="utf-8")
            key.chmod(0o600)
            validated = pp.validated_identity_file(key)
            session = pp.RemoteSession("192.0.2.10", "root", 22, Path(tmp) / "known_hosts", identity_file=validated)
            for command in (pp._ssh_base(session), pp._scp_base(session)):
                self.assertIn("-i", command)
                self.assertEqual(command[command.index("-i") + 1], str(validated))
                self.assertIn("IdentitiesOnly=yes", command)
            key.chmod(0o644)
            with self.assertRaisesRegex(pp.BuilderStop, "SSH_IDENTITY_FILE_PERMISSIONS"):
                pp.validated_identity_file(key)

    def test_fresh_vs_resume_inventory_clean_requirement(self):
        inv=pp.parse_inventory(GOOD.replace("RELEVANT_FOUND=0","RELEVANT_FOUND=1"))
        with self.assertRaises(pp.BuilderStop): pp.assert_inventory(inv,require_clean=True)
        self.assertTrue(all(pp.assert_inventory(inv,require_clean=False).values()))

    def test_firewall_and_egress_stop(self):
        with self.assertRaises(pp.BuilderStop): pp.assert_inventory(pp.parse_inventory(GOOD.replace("UFW_STATE=inactive","UFW_STATE=active")))
        with self.assertRaises(pp.BuilderStop): pp.assert_inventory(pp.parse_inventory(GOOD.replace("EGRESS_B=192.0.2.44","EGRESS_B=192.0.2.45")))

    def test_artifact_hashes_and_versions(self):
        self.assertEqual(len(pp.ARTIFACT_SHA256),4); self.assertEqual(pp.XRAY_VERSION,"26.3.27"); self.assertEqual(pp.HYSTERIA_VERSION,"2.12.1")
        for d in pp.ARTIFACT_SHA256.values(): self.assertRegex(d,r"^[0-9a-f]{64}$")

    def test_embedded_python_in_stage_scripts_compiles(self):
        scripts = (
            pp.stage_i_apply_script(PORTS.route_i_tcp),
            pp.stage_ii_apply_script(PORTS.route_ii_tcp),
            pp.stage_iii_apply_script(PORTS.route_iii_udp),
        )
        pattern = re.compile(
            r"python3[^\n]*<<'(?P<tag>[^']+)'[^\n]*\n(?P<body>.*?)\n(?P=tag)",
            re.DOTALL,
        )
        bodies = []
        for script in scripts:
            for match in pattern.finditer(script):
                bodies.append(match.group("body"))
                compile(match.group("body"), f"<{match.group('tag')}>", "exec")
        self.assertGreaterEqual(len(bodies), 6)

    def test_private_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"d"/"x"; pp.write_private(p,"x"); self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600); self.assertEqual(stat.S_IMODE(p.parent.stat().st_mode),0o700)

    def test_persistent_state_round_trip_and_no_raw_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger=pp.AcceptanceLedger(); ledger.data_path["I"]={"wifi","mobile"}; ledger.restart["I"]=ledger.isolation["I"]=ledger.dns_leak_checkpoint["I"]=True
            state=pp.PersistentState(pp.BUILDER_VERSION,"a"*32,"b"*64,("I",),PORTS,ledger,"II")
            p=Path(tmp)/"state.json"; pp.save_state(p,state); loaded=pp.load_state(p)
            self.assertEqual(loaded.accepted_routes,("I",)); self.assertEqual(loaded.ledger.data_path["I"],{"wifi","mobile"})
            text=p.read_text(); self.assertNotIn("192.0.2.",text); self.assertNotIn("cover.example",text)

    def test_invalid_resume_prefix_stops(self):
        bad={"builder_version":pp.BUILDER_VERSION,"run_id":"a"*32,"target_binding":"b"*64,"accepted_routes":["II"],"ports":pp.asdict(PORTS),"ledger":{}}
        with self.assertRaises(pp.BuilderStop): pp.PersistentState.from_mapping(bad)

    def test_target_binding_changes_with_identity(self):
        fp="SHA256:"+"A"*43
        a=pp.target_binding("example.com","root",22,fp); b=pp.target_binding("example.com","ubuntu",22,fp)
        self.assertRegex(a,r"^[0-9a-f]{64}$"); self.assertNotEqual(a,b)

    def test_verified_and_tofu_host_key_pinning(self):
        fp="SHA256:"+"A"*43
        scan="example.invalid ssh-ed25519 AAAATEST\n"
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(pp,"observe_host_key",return_value=(fp,scan)):
            directory=Path(tmp)/"trust"
            known=pp.pin_host_key("example.invalid",22,fp,directory)
            self.assertEqual(known.read_text(),scan)
            self.assertEqual(stat.S_IMODE(known.stat().st_mode),0o600)
            observed,tofu_known=pp.pin_current_host_key("example.invalid",22,directory)
            self.assertEqual(observed,fp); self.assertEqual(tofu_known.read_text(),scan)
            with self.assertRaisesRegex(pp.BuilderStop,"HOST_KEY_MISMATCH"):
                pp.pin_host_key("example.invalid",22,"SHA256:"+"B"*43,directory)

    def test_operator_metadata_cli_and_secrets_boundary(self):
        opts={o for a in pp.build_parser()._actions for o in a.option_strings}
        for expected in ("--target-host","--ssh-user","--ssh-port","--host-fingerprint","--trust-current-host-key"): self.assertIn(expected,opts)
        for bad in ("--sni","--cover","--password","--private-key"): self.assertNotIn(bad,opts)
        with self.assertRaises(SystemExit):
            pp.build_parser().parse_args(["--apply","--host-fingerprint","SHA256:"+"A"*43,"--trust-current-host-key"])

    def test_target_inputs_accept_owner_approved_metadata(self):
        fp="SHA256:"+"A"*43
        args=pp.build_parser().parse_args([
            "--apply","--profile-name","Foxy Baby","--target-host","192.0.2.10",
            "--ssh-user","vps","--ssh-port","22","--host-fingerprint",fp,
        ])
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(pp,"private_root",return_value=Path(tmp)), mock.patch.object(pp,"pin_host_key",return_value=Path(tmp)/"known_hosts") as pin:
            values=pp.perform_target_inputs(args)
        self.assertEqual(values[2:6],("192.0.2.10",22,"vps",fp))
        pin.assert_called_once()

    def test_explicit_tofu_pins_observed_key_without_printing_it(self):
        fp="SHA256:"+"B"*43
        args=pp.build_parser().parse_args([
            "--apply","--profile-name","Foxy Baby","--target-host","192.0.2.10",
            "--ssh-user","vps","--ssh-port","22","--trust-current-host-key",
        ])
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(pp,"private_root",return_value=Path(tmp)), mock.patch.object(pp,"pin_current_host_key",return_value=(fp,Path(tmp)/"known_hosts")), mock.patch("builtins.print") as output:
            values=pp.perform_target_inputs(args)
        self.assertEqual(values[2:6],("192.0.2.10",22,"vps",fp))
        output.assert_called_once_with("HOST_KEY_TOFU_PINNED=PASS")

    def test_apply_dispatches_to_reviewed_deployment_engine(self):
        with mock.patch.object(pp,"run_deployment_after_gate", return_value=0) as runner:
            self.assertEqual(pp.main(["--apply"]),0)
            runner.assert_called_once()
            self.assertTrue(runner.call_args.args[0].apply)

    def test_independent_http_https_hosts(self):
        from urllib.parse import urlparse
        self.assertEqual(urlparse(pp.HTTP_PROBE_URL).scheme,"http"); self.assertEqual(urlparse(pp.HTTPS_PROBE_URL).scheme,"https")
        self.assertNotEqual(urlparse(pp.HTTP_PROBE_URL).hostname,urlparse(pp.HTTPS_PROBE_URL).hostname)

    def test_controlmaster_is_explicit_and_secondary_is_batch(self):
        session=pp.RemoteSession("example.com","root",22,Path("/tmp/kh"),Path("/tmp/ctl"))
        ssh=pp._ssh_base(session); scp=pp._scp_base(session)
        joined=" ".join(ssh+scp)
        self.assertIn("BatchMode=yes",joined); self.assertIn("ControlMaster=no",joined); self.assertIn("/tmp/ctl",joined)
        source=MODULE_PATH.read_text()
        self.assertIn('"-M", "-N", "-f"',source); self.assertIn('"-O", "check"',source); self.assertIn('"-O", "exit"',source)

    def test_controlmaster_required_for_concrete_executor(self):
        s=pp.RemoteSession("example.com","root",22,Path("/tmp/kh"))
        with self.assertRaises(pp.BuilderStop): pp.SSHStageExecutor(s,PORTS,RUNTIME,{},Path("/tmp/x"))

    def test_privilege_resolution_root_and_passwordless_sudo(self):
        base=pp.RemoteSession("example.com","vps",22,Path("/tmp/kh"),Path("/tmp/ctl"))
        root_result=mock.Mock(returncode=0,stdout="0\n")
        with mock.patch.object(pp.subprocess,"run",return_value=root_result) as run:
            resolved=pp.resolve_privilege(base)
        self.assertFalse(resolved.use_sudo)
        self.assertNotIn("sudo", " ".join(run.call_args.args[0]))

        responses=[
            mock.Mock(returncode=0,stdout="1000\n"),
            mock.Mock(returncode=0,stdout="0\n"),
        ]
        with mock.patch.object(pp.subprocess,"run",side_effect=responses) as run:
            resolved=pp.resolve_privilege(base)
        self.assertTrue(resolved.use_sudo)
        self.assertIn("sudo -n bash -s", " ".join(run.call_args_list[1].args[0]))

    def test_privilege_resolution_rejects_non_nopasswd_sudo(self):
        base=pp.RemoteSession("example.com","vps",22,Path("/tmp/kh"),Path("/tmp/ctl"))
        responses=[
            mock.Mock(returncode=0,stdout="1000\n"),
            mock.Mock(returncode=1,stdout=""),
        ]
        with mock.patch.object(pp.subprocess,"run",side_effect=responses):
            with self.assertRaisesRegex(pp.BuilderStop,"SSH_PASSWORDLESS_SUDO_REQUIRED"):
                pp.resolve_privilege(base)

    def test_sudo_inventory_and_stage_use_privileged_bash(self):
        s=pp.RemoteSession("example.com","vps",22,Path("/tmp/kh"),Path("/tmp/ctl"),True)
        inventory_result=mock.Mock(returncode=0,stdout=GOOD)
        with mock.patch.object(pp.subprocess,"run",return_value=inventory_result) as run:
            inv=pp.remote_inventory(s)
        self.assertEqual(inv.uid,0)
        self.assertIn("sudo -n bash -s"," ".join(run.call_args.args[0]))

        with tempfile.TemporaryDirectory() as tmp:
            ex=pp.SSHStageExecutor(s,PORTS,RUNTIME,{},Path(tmp)/"private")
            stage_result=mock.Mock(returncode=0,stdout="MARK=PASS\n")
            with mock.patch.object(pp.subprocess,"run",return_value=stage_result) as run:
                ex._run("true\n","MARK=PASS")
            self.assertIn("sudo -n bash -s"," ".join(run.call_args.args[0]))

    def test_stream_upload_keeps_payload_out_of_argv(self):
        s=pp.RemoteSession("example.com","vps",22,Path("/tmp/kh"),Path("/tmp/ctl"),True)
        with tempfile.TemporaryDirectory() as tmp:
            ex=pp.SSHStageExecutor(s,PORTS,RUNTIME,{},Path(tmp)/"private")
            local=Path(tmp)/"secret.bin"; local.write_bytes(b"TOP_SECRET_PAYLOAD")
            result=mock.Mock(returncode=0,stdout=b"",stderr=b"")
            with mock.patch.object(pp.subprocess,"run",return_value=result) as run:
                ex._scp_to(local,"/var/lib/privatpirat-builder/runtime.json")
            argv=" ".join(run.call_args.args[0])
            self.assertIn("sudo -n bash -c",argv)
            self.assertIn("BatchMode=yes",argv)
            self.assertNotIn("/tmp/ctl",argv)
            self.assertNotIn("TOP_SECRET_PAYLOAD",argv)
            self.assertNotIn("scp ",argv)
        source=MODULE_PATH.read_text()
        self.assertNotIn("sshpass",source)
        self.assertNotIn("sudo -S",source)

    def test_stream_upload_failure_preserves_full_stderr_privately(self):
        session=pp.RemoteSession('example.com','root',22,Path('/tmp/kh'),Path('/tmp/ctl'))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'runtime.json'; source.write_bytes(b'private payload')
            ex=pp.SSHStageExecutor(session,PORTS,RUNTIME,{},root/'private',diagnostic_run_id='a'*32)
            stderr=b'private diagnostic\xff\n' * 100
            result=mock.Mock(returncode=255,stderr=stderr)
            with mock.patch.object(pp.subprocess,'run',return_value=result) as run:
                for _ in range(2):
                    with self.assertRaisesRegex(pp.BuilderStop,'^SSH_STREAM_UPLOAD_FAIL=STOP$'):
                        ex._scp_to(source,'/var/lib/privatpirat-builder/runtime.json')
            self.assertEqual(run.call_count,2)
            directory=root/'private'/'diagnostics'/('a'*32)
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode),0o700)
            records=list(directory.glob('ssh-upload-*.json')); self.assertEqual(len(records),2)
            for path in records:
                record=json.loads(path.read_text())
                self.assertEqual(record['ssh_returncode'],255); self.assertFalse(record['timed_out'])
                self.assertEqual((directory/record['stderr_file']).read_bytes(),stderr)
            for path in directory.iterdir(): self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)

    def test_stream_upload_timeout_preserves_partial_stderr(self):
        session=pp.RemoteSession('example.com','root',22,Path('/tmp/kh'),Path('/tmp/ctl'))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'runtime.json'; source.write_bytes(b'fixture')
            ex=pp.SSHStageExecutor(session,PORTS,RUNTIME,{},root/'private',diagnostic_run_id='b'*32)
            error=pp.subprocess.TimeoutExpired(['ssh'],90,stderr=b'partial diagnostic\xff')
            with mock.patch.object(pp.subprocess,'run',side_effect=error):
                with self.assertRaisesRegex(pp.BuilderStop,'^SSH_STREAM_UPLOAD_TIMEOUT=STOP$'):
                    ex._scp_to(source,'/var/lib/privatpirat-builder/runtime.json')
            directory=root/'private'/'diagnostics'/('b'*32)
            record=json.loads(next(directory.glob('*.json')).read_text())
            self.assertIsNone(record['ssh_returncode']); self.assertTrue(record['timed_out'])
            self.assertEqual((directory/record['stderr_file']).read_bytes(),error.stderr)

    def test_stream_upload_diagnostic_write_failure_is_controlled(self):
        session=pp.RemoteSession('example.com','root',22,Path('/tmp/kh'),Path('/tmp/ctl'))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'runtime.json'; source.write_bytes(b'fixture')
            ex=pp.SSHStageExecutor(session,PORTS,RUNTIME,{},root/'private',diagnostic_run_id='c'*32)
            with mock.patch.object(pp.subprocess,'run',return_value=mock.Mock(returncode=255,stderr=b'private')),mock.patch.object(pp,'ensure_private_dir',side_effect=OSError('fixture')):
                with self.assertRaisesRegex(pp.BuilderStop,'^SSH_UPLOAD_DIAGNOSTIC_SAVE_FAIL=STOP$'):
                    ex._scp_to(source,'/var/lib/privatpirat-builder/runtime.json')

    def test_route_renderers(self):
        i=json.loads(pp.render_xray_server_config(pp.Route.I,23451,I,"cover.example","C"*43)); ii=json.loads(pp.render_xray_server_config(pp.Route.II,23452,II,"cover.example","D"*43))
        self.assertEqual(i["inbounds"][0]["streamSettings"]["network"],"raw"); self.assertEqual(ii["inbounds"][0]["streamSettings"]["network"],"xhttp")
        ci=json.loads(pp.render_xray_client_config(pp.Route.I,"192.0.2.10",23451,I,"cover.example",10808)); reality=ci["outbounds"][0]["streamSettings"]["realitySettings"]
        self.assertEqual(reality["fingerprint"],"firefox"); self.assertEqual(reality["spiderX"],"")
        hy=pp.render_hysteria_client_config("192.0.2.10",23453,III,10808); self.assertIn("pinSHA256",hy); self.assertIn("insecure: true",hy)

    def test_bundle_permissions_and_manifest_sanitized(self):
        with tempfile.TemporaryDirectory() as tmp:
            files=pp.write_client_bundle(Path(tmp)/"bundle","192.0.2.10",PORTS,RUNTIME,{pp.Route.I:I,pp.Route.II:II,pp.Route.III:III})
            self.assertEqual(len(files),7)
            for p in files: self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
            m=(Path(tmp)/"bundle"/"manifest.json").read_text(); self.assertNotIn(I.uuid,m); self.assertNotIn(III.auth,m); self.assertNotIn("192.0.2.10",m)

    def test_verifier_uses_parser_specific_config_suffixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            verifier = pp.LocalClientVerifier(
                "192.0.2.10", PORTS, RUNTIME, "192.0.2.10",
                {"client_xray": Path("/bin/true"), "client_hysteria": Path("/bin/true")},
                Path(tmp),
            )
            process = mock.Mock()
            process.poll.return_value = 1
            with mock.patch.object(verifier, "_free_local_port", return_value=10808), mock.patch.object(verifier, "_wait_socks", return_value=False), mock.patch.object(pp.subprocess, "Popen", return_value=process) as popen:
                with self.assertRaisesRegex(pp.BuilderStop, "CLIENT_VERIFIER_PROCESS_EXIT"):
                    verifier._verify_round(pp.Route.I, I, 1)
                self.assertTrue(str(popen.call_args.args[0][-1]).endswith(".json"))
                with self.assertRaisesRegex(pp.BuilderStop, "CLIENT_VERIFIER_PROCESS_EXIT"):
                    verifier._verify_round(pp.Route.III, III, 1)
                self.assertTrue(str(popen.call_args.args[0][-1]).endswith(".yaml"))

    def test_unavailable_rejects_local_client_exit_before_socks(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp)
            verifier = pp.LocalClientVerifier(
                "192.0.2.10", PORTS, RUNTIME, "192.0.2.10",
                {"client_xray": Path("/bin/true")}, private,
            )
            process = mock.Mock()
            process.poll.return_value = 1
            with mock.patch.object(verifier, "_free_local_port", return_value=10808), mock.patch.object(verifier, "_wait_socks", return_value=False), mock.patch.object(pp.subprocess, "Popen", return_value=process), mock.patch.object(pp.subprocess, "run") as run:
                with self.assertRaisesRegex(pp.BuilderStop, "CLIENT_VERIFIER_PROCESS_EXIT"):
                    verifier.unavailable(pp.Route.I, I)
            run.assert_not_called()
            self.assertFalse((private / "verify-I-0.json").exists())
            log = private / "verify-I-0.log"
            self.assertTrue(log.exists())
            self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)

    def test_unavailable_requires_two_explicit_socks_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp)
            verifier = pp.LocalClientVerifier(
                "192.0.2.10", PORTS, RUNTIME, "192.0.2.10",
                {"client_xray": Path("/bin/true")}, private,
            )
            process = mock.Mock()
            process.poll.return_value = None
            process.wait.return_value = 0
            rejected = [
                mock.Mock(returncode=97, stdout="", stderr=""),
                mock.Mock(returncode=97, stdout="", stderr=""),
            ]
            with mock.patch.object(verifier, "_free_local_port", return_value=10808), mock.patch.object(verifier, "_wait_socks", return_value=True), mock.patch.object(pp.subprocess, "Popen", return_value=process), mock.patch.object(pp.subprocess, "run", side_effect=rejected) as run:
                self.assertTrue(verifier.unavailable(pp.Route.I, I))
            self.assertEqual(run.call_count, 2)
            self.assertFalse((private / "verify-I-0.json").exists())
            self.assertFalse((private / "verify-I-0.log").exists())

    def test_unavailable_rejects_ambiguous_probe_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp)
            verifier = pp.LocalClientVerifier(
                "192.0.2.10", PORTS, RUNTIME, "192.0.2.10",
                {"client_xray": Path("/bin/true")}, private,
            )
            process = mock.Mock()
            process.poll.return_value = None
            process.wait.return_value = 0
            ambiguous = mock.Mock(returncode=28, stdout="", stderr="timeout")
            with mock.patch.object(verifier, "_free_local_port", return_value=10808), mock.patch.object(verifier, "_wait_socks", return_value=True), mock.patch.object(pp.subprocess, "Popen", return_value=process), mock.patch.object(pp.subprocess, "run", return_value=ambiguous):
                with self.assertRaisesRegex(pp.BuilderStop, "CLIENT_UNAVAILABILITY_AMBIGUOUS"):
                    verifier.unavailable(pp.Route.I, I)
            self.assertFalse((private / "verify-I-0.json").exists())
            self.assertTrue((private / "verify-I-0.log").exists())

    def test_unavailable_is_false_when_data_path_still_responds(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp)
            verifier = pp.LocalClientVerifier(
                "192.0.2.10", PORTS, RUNTIME, "192.0.2.10",
                {"client_xray": Path("/bin/true")}, private,
            )
            process = mock.Mock()
            process.poll.return_value = None
            process.wait.return_value = 0
            reachable = [
                mock.Mock(returncode=0, stdout="", stderr=""),
                mock.Mock(returncode=0, stdout="", stderr=""),
            ]
            with mock.patch.object(verifier, "_free_local_port", return_value=10808), mock.patch.object(verifier, "_wait_socks", return_value=True), mock.patch.object(pp.subprocess, "Popen", return_value=process), mock.patch.object(pp.subprocess, "run", side_effect=reachable):
                self.assertFalse(verifier.unavailable(pp.Route.I, I))
            self.assertFalse((private / "verify-I-0.log").exists())

    def test_verify_round_passes_and_removes_transient_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp)
            verifier = pp.LocalClientVerifier(
                "192.0.2.10", PORTS, RUNTIME, "192.0.2.10",
                {"client_xray": Path("/bin/true")}, private,
            )
            process = mock.Mock()
            process.poll.return_value = None
            process.wait.return_value = 0
            with mock.patch.object(verifier, "_free_local_port", return_value=10808), mock.patch.object(verifier, "_wait_socks", return_value=True), mock.patch.object(pp.subprocess, "Popen", return_value=process), mock.patch.object(verifier, "_curl_status_body", return_value=(200, "ok")) as status, mock.patch.object(verifier, "_curl_text", return_value="192.0.2.10") as text:
                self.assertTrue(verifier._verify_round(pp.Route.I, I, 1))
            self.assertEqual(status.call_count, 2)
            self.assertEqual(text.call_count, 2)
            self.assertFalse((private / "verify-I-1.json").exists())
            self.assertFalse((private / "verify-I-1.log").exists())

    def test_verify_round_data_path_failure_is_classified_and_keeps_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp)
            verifier = pp.LocalClientVerifier(
                "192.0.2.10", PORTS, RUNTIME, "192.0.2.10",
                {"client_xray": Path("/bin/true")}, private,
            )
            process = mock.Mock()
            process.poll.return_value = None
            process.wait.return_value = 0
            failure = pp.BuilderStop("CLIENT_DATA_PATH_FAIL=STOP")
            with mock.patch.object(verifier, "_free_local_port", return_value=10808), mock.patch.object(verifier, "_wait_socks", return_value=True), mock.patch.object(pp.subprocess, "Popen", return_value=process), mock.patch.object(verifier, "_curl_status_body", side_effect=failure):
                with self.assertRaisesRegex(pp.BuilderStop, "CLIENT_HTTP_PROBE_FAIL"):
                    verifier._verify_round(pp.Route.I, I, 1)
            self.assertFalse((private / "verify-I-1.json").exists())
            log = private / "verify-I-1.log"
            self.assertTrue(log.exists())
            self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)

    def test_curl_transport_exit_is_reported_without_stderr(self):
        result=mock.Mock(returncode=28,stdout="",stderr="sensitive diagnostic")
        with mock.patch.object(pp.subprocess,"run",return_value=result):
            with self.assertRaisesRegex(pp.BuilderStop,"CLIENT_CURL_EXIT_28=STOP") as caught:
                pp.LocalClientVerifier._curl_status_body(10808,"http://example.com/")
        self.assertNotIn("sensitive",str(caught.exception))

    def test_external_tcp_probe_classifies_provider_path_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            verifier=pp.LocalClientVerifier("192.0.2.10",PORTS,RUNTIME,"192.0.2.10",{},Path(tmp),verify_external_tcp=True)
            with mock.patch.object(pp.socket,"create_connection",side_effect=OSError("sensitive endpoint")):
                with self.assertRaisesRegex(pp.BuilderStop,"CLIENT_TCP_PORT_UNREACHABLE=STOP") as caught:
                    verifier._verify_round(pp.Route.I,I,1)
            self.assertNotIn("sensitive",str(caught.exception))

    def test_engine_preserves_controlled_verifier_failure_code(self):
        ex = FakeExecutor()
        verifier = FakeVerifier()
        verifier.verify = mock.Mock(
            side_effect=pp.BuilderStop("CLIENT_HTTP_PROBE_FAIL=STOP")
        )
        with tempfile.TemporaryDirectory() as tmp:
            engine = pp.DeploymentEngine(
                ex, verifier, Path(tmp) / "bundle", "192.0.2.10",
                PORTS, RUNTIME, "a" * 32,
            )
            with self.assertRaisesRegex(
                pp.BuilderStop,
                "STAGE_I_FAIL_CLIENT_HTTP_PROBE_FAIL=STOP",
            ):
                engine.build_route(pp.Route.I, pp.NetworkClass.WIFI)
        self.assertIn(("rollback", pp.Route.I), ex.events)

    def test_diagnostic_capture_precedes_rollback_even_when_capture_fails(self):
        for capture_fails in (False, True):
            ex = FakeExecutor(fail=("capture", pp.Route.I) if capture_fails else None)
            if not capture_fails:
                def capture(route):
                    ex._event("capture", route)
                    return True
                ex.capture_diagnostics = capture
            verifier = FakeVerifier()
            verifier.verify = mock.Mock(side_effect=pp.BuilderStop("CLIENT_CURL_EXIT_56=STOP"))
            with tempfile.TemporaryDirectory() as tmp:
                engine = pp.DeploymentEngine(ex, verifier, Path(tmp) / "bundle", "192.0.2.10", PORTS, RUNTIME, "a" * 32)
                with mock.patch("builtins.print") as printed:
                    with self.assertRaisesRegex(pp.BuilderStop, "STAGE_I_FAIL_CLIENT_CURL_EXIT_56=STOP"):
                        engine.build_route(pp.Route.I, pp.NetworkClass.OPERATOR)
            self.assertLess(ex.events.index(("capture", pp.Route.I)), ex.events.index(("rollback", pp.Route.I)))
            self.assertEqual(printed.call_args.args[0], f"DIAGNOSTIC_CAPTURE_I={'FAIL' if capture_fails else 'SAVED'}")

    def test_diagnostic_server_log_is_private_and_stdout_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp) / "private"
            session = pp.RemoteSession("192.0.2.10", "root", 22, Path(tmp) / "known_hosts", control_path=Path(tmp) / "control")
            executor = pp.SSHStageExecutor(session, PORTS, RUNTIME, {}, private, diagnostic_run_id="a" * 32)
            client_log = private / "verify" / ("a" * 32) / "verify-I-1-1.log"
            pp.write_private(client_log, "private client handshake detail\n")
            remote_log = "REALITY: processed invalid connection from private-address\n"
            result = mock.Mock(returncode=0, stdout=remote_log, stderr="")
            with mock.patch.object(pp.subprocess, "run", return_value=result) as run, mock.patch("builtins.print") as printed:
                self.assertTrue(executor.capture_diagnostics(pp.Route.I))
            printed.assert_not_called()
            self.assertIn("StrictHostKeyChecking=yes", run.call_args.args[0])
            server_log = private / "diagnostics" / ("a" * 32) / "server-I.log"
            status = json.loads((server_log.parent / "status-I.json").read_text())
            self.assertEqual(server_log.read_text(), remote_log)
            self.assertEqual(stat.S_IMODE(server_log.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE((server_log.parent / "status-I.json").stat().st_mode), 0o600)
            self.assertEqual(status["client_logs_saved"], 1)
            self.assertEqual(status["server_invalid_connection_count"], 1)
            self.assertNotIn("private-address", json.dumps(status))

    def test_diagnostic_client_logs_are_private_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp)
            verifier = pp.LocalClientVerifier(
                "192.0.2.10", PORTS, RUNTIME, "192.0.2.10",
                {"client_xray": Path("/bin/true")}, private, preserve_logs=True,
            )
            process = mock.Mock()
            process.poll.return_value = None
            process.wait.return_value = 0
            with mock.patch.object(verifier, "_free_local_port", return_value=10808), \
                 mock.patch.object(verifier, "_wait_socks", return_value=True), \
                 mock.patch.object(pp.subprocess, "Popen", return_value=process), \
                 mock.patch.object(verifier, "_curl_status_body", return_value=(200, "ok")), \
                 mock.patch.object(verifier, "_curl_text", return_value="192.0.2.10"):
                self.assertTrue(verifier._verify_round(pp.Route.I, I, 1))
                self.assertTrue(verifier._verify_round(pp.Route.I, I, 1))
            logs = sorted(private.glob("verify-I-1-*.log"))
            self.assertEqual(len(logs), 2)
            self.assertTrue(all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in logs))
            self.assertFalse(list(private.glob("*.json")))

    def test_diagnostic_route_i_only_archives_failed_state_and_never_starts_ii(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slug = "lilfox-am"
            state_file = root / "state" / slug / "state.json"
            private = root / "private" / slug
            old = pp.PersistentState(pp.BUILDER_VERSION, "a" * 32, "b" * 64, (), PORTS, pp.AcceptanceLedger(), "I", "server_only")
            pp.save_state(state_file, old)
            pp.write_private(private / "runtime.json", json.dumps({"cover_hostname": "cover.example"}))
            session = pp.RemoteSession("192.0.2.10", "root", 22, private / "known_hosts")
            context = pp.PreflightContext("lilfox-am", slug, session, pp.parse_inventory(GOOD), PORTS, private, state_file.parent, {}, "b" * 64)
            executor = FakeExecutor()
            def capture(route):
                executor._event("capture", route)
                return True
            executor.capture_diagnostics = capture
            args = pp.build_parser().parse_args(["--apply", "--server-only", "--diagnostic-route-i", "--route-ports", "23451,23452,23453"])
            def preflight(*_args, **_kwargs):
                self.assertTrue(state_file.exists())
                return context
            with mock.patch.object(pp, "state_root", return_value=root / "state"), \
                 mock.patch.object(pp, "private_root", return_value=root / "private"), \
                 mock.patch.object(pp, "local_prerequisites", return_value={"ok": True}), \
                 mock.patch.object(pp, "perform_target_inputs", return_value=("lilfox-am", slug, session.host, 22, "root", "SHA256:" + "A" * 43, session.known_hosts)), \
                 mock.patch.object(pp, "SSHControlMaster", return_value=nullcontext(session)), \
                 mock.patch.object(pp, "preflight_session", side_effect=preflight), \
                 mock.patch.object(pp, "remote_cover_probe"), \
                 mock.patch.object(pp, "prepare_artifacts", return_value={}), \
                 mock.patch.object(pp, "SSHStageExecutor", return_value=executor), \
                 mock.patch.object(pp, "LocalClientVerifier", return_value=FakeVerifier()), \
                 mock.patch("builtins.print"):
                self.assertEqual(pp.run_deployment_after_gate(args), 0)
            self.assertTrue((state_file.parent / ("state.failed-" + old.run_id + ".json")).exists())
            self.assertEqual(pp.load_state(state_file).accepted_routes, ("I",))
            self.assertNotIn(("apply", pp.Route.II), executor.events)
            self.assertNotIn(("apply", pp.Route.III), executor.events)
            self.assertLess(executor.events.index(("capture", pp.Route.I)), executor.events.index(("checkpoint", pp.Route.I)))

    @staticmethod
    def config_pair_fixture():
        import base64
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        private = bytes(range(32))
        public = X25519PrivateKey.from_private_bytes(private).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip("=")
        material = pp.RouteMaterial(pp.Route.I, uuid=I.uuid, public_key=encode(public), short_id=I.short_id)
        server = pp.render_xray_server_config(pp.Route.I, PORTS.route_i_tcp, material, RUNTIME.cover_hostname, encode(private))
        client = pp.render_xray_client_config(pp.Route.I, "192.0.2.10", PORTS.route_i_tcp, material, RUNTIME.cover_hostname, 10808)
        return server, client, material

    def test_config_pair_matches_and_distinguishes_each_field(self):
        server_text, client_text, _ = self.config_pair_fixture()
        baseline = pp.compare_route_i_configs(server_text, client_text, "192.0.2.10", PORTS.route_i_tcp)
        self.assertEqual(set(baseline.values()), {"MATCH"})
        mutations = [
            ("DESTINATION", "client", ("outbounds", 0, "settings", "vnext", 0, "address"), "192.0.2.11"),
            ("DESTINATION", "server", ("inbounds", 0, "port"), 443),
            ("DESTINATION", "server", ("inbounds", 0, "listen"), "127.0.0.1"),
            ("UUID", "client", ("outbounds", 0, "settings", "vnext", 0, "users", 0, "id"), II.uuid),
            ("FLOW", "client", ("outbounds", 0, "settings", "vnext", 0, "users", 0, "flow"), ""),
            ("SNI", "server", ("inbounds", 0, "streamSettings", "realitySettings", "serverNames"), ["other.example"]),
            ("SNI", "server", ("inbounds", 0, "streamSettings", "realitySettings", "target"), "other.example:443"),
            ("SHORT_ID", "client", ("outbounds", 0, "streamSettings", "realitySettings", "shortId"), II.short_id),
            ("PUBLIC_KEY", "client", ("outbounds", 0, "streamSettings", "realitySettings", "password"), II.public_key),
            ("PUBLIC_KEY", "server", ("inbounds", 0, "streamSettings", "realitySettings", "privateKey"), "A" * 43),
        ]
        for field, side, path, value in mutations:
            with self.subTest(field=field, side=side, path=path):
                pair = {"server": json.loads(server_text), "client": json.loads(client_text)}
                obj = pair[side]
                for key in path[:-1]: obj = obj[key]
                obj[path[-1]] = value
                result = pp.compare_route_i_configs(json.dumps(pair["server"]), json.dumps(pair["client"]), "192.0.2.10", PORTS.route_i_tcp)
                self.assertEqual(result[field], "MISMATCH")
                self.assertEqual([key for key in result if result[key] == "MISMATCH"], [field])

    def test_config_pair_malformed_input_and_keys_never_pass(self):
        server, client, _ = self.config_pair_fixture()
        for invalid in ("private-invalid-json", "{}", "[]"):
            with self.subTest(invalid=invalid):
                result = pp.compare_route_i_configs(invalid, client, "192.0.2.10", PORTS.route_i_tcp)
                self.assertEqual(set(result.values()), {"MISMATCH"})
                self.assertNotIn("private-invalid-json", json.dumps(result))
        config = json.loads(server)
        config["inbounds"][0]["streamSettings"]["realitySettings"]["privateKey"] = "private-invalid-key"
        result = pp.compare_route_i_configs(json.dumps(config), client, "192.0.2.10", PORTS.route_i_tcp)
        self.assertEqual(result["PUBLIC_KEY"], "MISMATCH")
        del config["inbounds"][0]["settings"]["clients"][0]["id"]
        self.assertIn("MISMATCH", pp.compare_route_i_configs(json.dumps(config), client, "192.0.2.10", PORTS.route_i_tcp).values())

    def test_config_pair_snapshot_uses_actual_server_file_and_strict_ssh(self):
        server, _, _ = self.config_pair_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            session = pp.RemoteSession("192.0.2.10", "root", 22, Path(tmp) / "known_hosts", control_path=Path(tmp) / "control")
            executor = pp.SSHStageExecutor(session, PORTS, RUNTIME, {}, Path(tmp) / "private", diagnostic_run_id="a" * 32)
            destination = Path(tmp) / "private" / "verify" / "server.json"
            with mock.patch.object(pp.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=server.encode(), stderr=b"")) as run, mock.patch("builtins.print") as printed:
                executor.snapshot_route_i_config(destination)
            self.assertIn("StrictHostKeyChecking=yes", run.call_args.args[0])
            self.assertIn("/etc/privatpirat/pp-lab-i/config.json", run.call_args.args[0][-1])
            self.assertEqual(destination.read_text(), server)
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(destination.parent.stat().st_mode), 0o700)
            printed.assert_not_called()
            with mock.patch.object(executor, "_scp_from", side_effect=pp.BuilderStop("private transfer detail")):
                with self.assertRaisesRegex(pp.BuilderStop, "^SERVER_CONFIG_SNAPSHOT_FAIL=STOP$"):
                    executor.snapshot_route_i_config(destination)

    def test_config_pair_precedes_each_client_and_probe_and_retains_files(self):
        server, _, material = self.config_pair_fixture()
        events = []
        with tempfile.TemporaryDirectory() as tmp:
            def snapshot(path):
                events.append("snapshot")
                pp.write_private(path, server)
            verifier = pp.LocalClientVerifier("192.0.2.10", PORTS, RUNTIME, "192.0.2.10", {"client_xray": Path("/bin/true")}, Path(tmp), verify_external_tcp=True, preserve_logs=True, route_i_snapshot=snapshot)
            process = mock.Mock()
            process.poll.return_value = None
            def launch(cmd, **kwargs):
                events.append("launch")
                cfg = Path(cmd[-1])
                result = json.loads(cfg.with_suffix(".comparison.json").read_text())
                self.assertEqual(set(result.values()), {"MATCH"})
                return process
            def probe(_route): events.append("tcp")
            with mock.patch.object(verifier, "_free_local_port", return_value=10808), \
                 mock.patch.object(verifier, "_wait_socks", return_value=True), \
                 mock.patch.object(pp.subprocess, "Popen", side_effect=launch) as popen, \
                 mock.patch.object(verifier, "_external_tcp_probe", side_effect=probe), \
                 mock.patch.object(verifier, "_curl_status_body", return_value=(200, "ok")), \
                 mock.patch.object(verifier, "_curl_text", return_value="192.0.2.10"), \
                 mock.patch.object(verifier, "_curl_route_unavailable", return_value=True), \
                 mock.patch("builtins.print") as printed:
                self.assertTrue(verifier._verify_round(pp.Route.I, material, 1))
                self.assertTrue(verifier._verify_round(pp.Route.I, material, 1))
                self.assertTrue(verifier.unavailable(pp.Route.I, material))
            self.assertEqual(events, ["snapshot", "launch", "tcp", "snapshot", "launch", "tcp", "snapshot", "launch"])
            self.assertEqual(popen.call_count, 3)
            self.assertEqual(len(list(Path(tmp).glob("*.server.json"))), 3)
            self.assertEqual(len(list(Path(tmp).glob("*.comparison.json"))), 3)
            self.assertEqual(len(list(Path(tmp).glob("*.json"))), 9)
            self.assertTrue(all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in Path(tmp).iterdir()))
            self.assertEqual(stat.S_IMODE(Path(tmp).stat().st_mode), 0o700)
            self.assertTrue(all(re.fullmatch(r"CONFIG_PAIR_I_[A-Z_]+=MATCH", call.args[0]) for call in printed.call_args_list))

    def test_config_pair_actual_client_mismatch_stops_before_tests_and_rolls_back(self):
        server, _, material = self.config_pair_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            def snapshot(path): pp.write_private(path, server)
            verifier = pp.LocalClientVerifier("192.0.2.10", PORTS, RUNTIME, "192.0.2.10", {"client_xray": Path("/bin/true")}, Path(tmp) / "verify", verify_external_tcp=True, preserve_logs=True, route_i_snapshot=snapshot)
            original = verifier._command
            def actual_file_changed(route, mat, socks, cfg):
                cmd = original(route, mat, socks, cfg)
                config = json.loads(cfg.read_text())
                config["outbounds"][0]["settings"]["vnext"][0]["users"][0]["id"] = II.uuid
                pp.write_private(cfg, json.dumps(config))
                return cmd
            executor = FakeExecutor()
            executor.materials[pp.Route.I] = material
            engine = pp.DeploymentEngine(executor, verifier, Path(tmp) / "bundle", "192.0.2.10", PORTS, RUNTIME, "a" * 32, server_only=True)
            with mock.patch.object(verifier, "_command", side_effect=actual_file_changed), \
                 mock.patch.object(pp.subprocess, "Popen") as popen, \
                 mock.patch.object(pp.socket, "create_connection") as tcp, \
                 mock.patch.object(verifier, "_curl_status_body") as curl, \
                 mock.patch("builtins.print") as printed:
                with self.assertRaisesRegex(pp.BuilderStop, "^STAGE_I_FAIL_ROUTE_I_CONFIG_PAIR_MISMATCH=STOP$"):
                    engine.build_route(pp.Route.I, pp.NetworkClass.OPERATOR)
            popen.assert_not_called(); tcp.assert_not_called(); curl.assert_not_called()
            self.assertLess(executor.events.index(("capture", pp.Route.I)), executor.events.index(("rollback", pp.Route.I)))
            comparison = json.loads(next((Path(tmp) / "verify").glob("*.comparison.json")).read_text())
            self.assertEqual(comparison["UUID"], "MISMATCH")
            self.assertEqual(len(list((Path(tmp) / "verify").glob("*.json"))), 3)
            self.assertNotIn(material.uuid, str(printed.call_args_list))
            self.assertNotIn(material.short_id, str(printed.call_args_list))
            self.assertNotIn(material.public_key, str(printed.call_args_list))

    def test_config_pair_server_changes_and_snapshot_failure_stop_before_client(self):
        server, _, material = self.config_pair_fixture()
        for failure in ("server-changed", "snapshot-failed"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                calls = []
                def snapshot(path):
                    calls.append(path)
                    if failure == "snapshot-failed": raise pp.BuilderStop("SERVER_CONFIG_SNAPSHOT_FAIL=STOP")
                    actual = json.loads(server)
                    actual["inbounds"][0]["settings"]["clients"][0]["id"] = II.uuid
                    pp.write_private(path, json.dumps(actual))
                verifier = pp.LocalClientVerifier("192.0.2.10", PORTS, RUNTIME, "192.0.2.10", {"client_xray": Path("/bin/true")}, Path(tmp) / "verify", preserve_logs=True, route_i_snapshot=snapshot)
                executor = FakeExecutor()
                executor.materials[pp.Route.I] = material
                engine = pp.DeploymentEngine(executor, verifier, Path(tmp) / "bundle", "192.0.2.10", PORTS, RUNTIME, "a" * 32, server_only=True)
                with mock.patch.object(pp.subprocess, "Popen") as popen, mock.patch("builtins.print"):
                    with self.assertRaises(pp.BuilderStop): engine.build_route(pp.Route.I, pp.NetworkClass.OPERATOR)
                self.assertEqual(len(calls), 1)
                popen.assert_not_called()
                self.assertIn(("rollback", pp.Route.I), executor.events)
                self.assertTrue(list((Path(tmp) / "verify").glob("verify-I-1-1.json")))

    def test_config_pair_crypto_missing_stops_before_ssh(self):
        args = pp.build_parser().parse_args(["--apply", "--server-only", "--diagnostic-route-i"])
        with mock.patch.object(pp, "local_prerequisites", return_value={"ok": True}), \
             mock.patch.object(pp, "require_route_i_crypto", side_effect=pp.BuilderStop("ROUTE_I_CRYPTO_UNAVAILABLE=STOP")), \
             mock.patch.object(pp, "perform_target_inputs") as inputs:
            with self.assertRaisesRegex(pp.BuilderStop, "ROUTE_I_CRYPTO_UNAVAILABLE=STOP"):
                pp.run_deployment_after_gate(args)
        inputs.assert_not_called()

    def test_diagnostic_stage_i_uses_info_without_reality_show(self):
        ordinary = pp.stage_i_apply_script(443)
        diagnostic = pp.stage_i_apply_script(443, diagnostic=True)
        self.assertIn('"loglevel":\'warning\'', ordinary)
        self.assertIn('"loglevel":\'info\'', diagnostic)
        self.assertNotIn('date --iso-8601=seconds > "$ROOT/i.journal_since"', ordinary)
        self.assertIn("i.journal_since", diagnostic)
        self.assertIn('"show":False', diagnostic)

    def test_server_actions_are_separate(self):
        restart=pp.server_action_script(pp.Route.II,23452,"restart"); stop=pp.server_action_script(pp.Route.II,23452,"stop")
        self.assertIn("systemctl restart",restart); self.assertNotIn("systemctl stop",restart); self.assertIn("OLD_PID",restart); self.assertIn("NEW_PID",restart)
        self.assertIn("systemctl stop",stop); self.assertIn("then exit 31; fi",stop); self.assertIn("pp-lab-i.service",stop)

    def test_restart_is_followed_by_client_data_path_and_isolation_by_unavailable(self):
        ex=FakeExecutor(); ver=FakeVerifier(); ledger=pp.AcceptanceLedger()
        with tempfile.TemporaryDirectory() as tmp:
            e=pp.DeploymentEngine(ex,ver,Path(tmp)/"bundle","192.0.2.10",PORTS,RUNTIME,"a"*32,ledger)
            e.initialize(); e.build_route(pp.Route.I,pp.NetworkClass.WIFI)
        names=[x[0] for x in ex.events]
        self.assertNotIn(("checkpoint",pp.Route.I),ex.events)
        self.assertLess(names.index("restart"), names.index("stop")); self.assertLess(names.index("stop"), names.index("start"))
        self.assertIn(("unavailable",pp.Route.I,1),ver.calls)
        # initial 3-round, restart 1-round, unavailable, start 1-round
        self.assertEqual(ver.calls[0],("verify",pp.Route.I,3)); self.assertEqual(ver.calls[1],("verify",pp.Route.I,1)); self.assertEqual(ver.calls[-1],("verify",pp.Route.I,1))
        self.assertTrue(ledger.restart["I"]); self.assertTrue(ledger.isolation["I"])

    def test_stop_isolation_failure_rolls_back_current(self):
        ex=FakeExecutor(); ver=FakeVerifier(unavailable=False)
        with tempfile.TemporaryDirectory() as tmp:
            e=pp.DeploymentEngine(ex,ver,Path(tmp)/"b","192.0.2.10",PORTS,RUNTIME,"a"*32)
            with self.assertRaisesRegex(pp.BuilderStop,"STAGE_I_FAIL"): e.build_route(pp.Route.I,pp.NetworkClass.WIFI)
        self.assertIn(("rollback",pp.Route.I),ex.events)

    def test_route_verdict_partial_until_both_networks_and_dns(self):
        l=pp.AcceptanceLedger(); l.restart["I"]=True; l.isolation["I"]=True; l.mark_data_path(pp.Route.I,pp.NetworkClass.WIFI)
        self.assertIs(l.route_verdict(pp.Route.I),pp.Verdict.PARTIAL)
        l.mark_data_path(pp.Route.I,pp.NetworkClass.MOBILE); self.assertIs(l.route_verdict(pp.Route.I),pp.Verdict.PARTIAL)
        l.dns_leak_checkpoint["I"]=True; self.assertIs(l.route_verdict(pp.Route.I),pp.Verdict.PASS)

    def test_route_ii_requires_regression_both_networks(self):
        l=pp.AcceptanceLedger(); l.data_path["II"]={"wifi","mobile"}; l.restart["II"]=l.isolation["II"]=l.dns_leak_checkpoint["II"]=True
        l.regression["II>I"]={"wifi"}; self.assertIs(l.route_verdict(pp.Route.II),pp.Verdict.PARTIAL)
        l.regression["II>I"].add("mobile"); self.assertIs(l.route_verdict(pp.Route.II),pp.Verdict.PASS)

    def test_final_verdict_never_false_pass(self):
        l=pp.AcceptanceLedger(); self.assertIs(l.final_verdict(),pp.Verdict.PARTIAL)
        l.failed_routes.add("III"); self.assertIs(l.final_verdict(),pp.Verdict.FAIL)

    def test_engine_can_advance_only_formal_pass(self):
        ex=FakeExecutor(); ver=FakeVerifier(); l=pp.AcceptanceLedger()
        with tempfile.TemporaryDirectory() as tmp:
            e=pp.DeploymentEngine(ex,ver,Path(tmp)/"b","192.0.2.10",PORTS,RUNTIME,"a"*32,l)
            e.build_route(pp.Route.I,pp.NetworkClass.WIFI); self.assertFalse(e.can_advance(pp.Route.I))
            e.accept_network(pp.Route.I,pp.NetworkClass.MOBILE); self.assertFalse(e.can_advance(pp.Route.I))
            e.mark_dns_leak_checkpoint(pp.Route.I,True); self.assertFalse(e.can_advance(pp.Route.I))
            e.accept_route(pp.Route.I); self.assertTrue(e.can_advance(pp.Route.I)); self.assertIn(("checkpoint",pp.Route.I),ex.events)

    def test_engine_ii_failure_preserves_i_and_rolls_back_ii(self):
        ex=FakeExecutor(fail=("health",pp.Route.II)); ver=FakeVerifier(); l=pp.AcceptanceLedger()
        l.data_path["I"]={"wifi","mobile"}; l.restart["I"]=l.isolation["I"]=l.dns_leak_checkpoint["I"]=True
        with tempfile.TemporaryDirectory() as tmp:
            e=pp.DeploymentEngine(ex,ver,Path(tmp)/"b","192.0.2.10",PORTS,RUNTIME,"a"*32,l,accepted_materials={pp.Route.I:I})
            with self.assertRaisesRegex(pp.BuilderStop,"STAGE_II_FAIL"): e.build_route(pp.Route.II,pp.NetworkClass.WIFI)
        self.assertIn(("rollback",pp.Route.II),ex.events); self.assertNotIn(("rollback",pp.Route.I),ex.events)


    def test_second_network_failure_rolls_back_unaccepted_current_route(self):
        ex=FakeExecutor(); ver=FakeVerifier(fail_verify_calls={5}); l=pp.AcceptanceLedger()
        with tempfile.TemporaryDirectory() as tmp:
            e=pp.DeploymentEngine(ex,ver,Path(tmp)/"b","192.0.2.10",PORTS,RUNTIME,"a"*32,l)
            e.build_route(pp.Route.I,pp.NetworkClass.WIFI)
            with self.assertRaisesRegex(pp.BuilderStop,"STAGE_I_FAIL"):
                e.accept_network(pp.Route.I,pp.NetworkClass.MOBILE)
        self.assertIn(("rollback",pp.Route.I),ex.events); self.assertNotIn(pp.Route.I,e.accepted)

    def test_retry_cannot_reuse_stale_current_route_evidence(self):
        ex=FakeExecutor(); ver=FakeVerifier(); l=pp.AcceptanceLedger(); l.data_path["I"]={"wifi","mobile"}; l.restart["I"]=l.isolation["I"]=l.dns_leak_checkpoint["I"]=True; l.failed_routes.add("I")
        with tempfile.TemporaryDirectory() as tmp:
            e=pp.DeploymentEngine(ex,ver,Path(tmp)/"b","192.0.2.10",PORTS,RUNTIME,"a"*32,l)
            e.build_route(pp.Route.I,pp.NetworkClass.WIFI)
        self.assertEqual(l.data_path["I"],{"wifi"}); self.assertFalse(l.dns_leak_checkpoint["I"]); self.assertNotIn("I",l.failed_routes)

    def test_resume_rejects_accepted_route_without_formal_pass(self):
        raw={"builder_version":pp.BUILDER_VERSION,"run_id":"a"*32,"target_binding":"b"*64,"accepted_routes":["I"],"ports":pp.asdict(PORTS),"ledger":pp.AcceptanceLedger().to_jsonable()}
        with self.assertRaisesRegex(pp.BuilderStop,"ACCEPTED_ROUTE_NOT_PASS"):
            pp.PersistentState.from_mapping(raw)

    def test_engine_refuses_next_route_while_previous_partial(self):
        ex=FakeExecutor(); ver=FakeVerifier(); l=pp.AcceptanceLedger()
        with tempfile.TemporaryDirectory() as tmp:
            e=pp.DeploymentEngine(ex,ver,Path(tmp)/"b","192.0.2.10",PORTS,RUNTIME,"a"*32,l,accepted_materials={pp.Route.I:I})
            with self.assertRaisesRegex(pp.BuilderStop,"PREVIOUS_ROUTE_NOT_FORMALLY_ACCEPTED"):
                e.build_route(pp.Route.II,pp.NetworkClass.WIFI)
        self.assertNotIn(("apply",pp.Route.II),ex.events)

    def test_dns_checkpoint_requires_built_route(self):
        e=pp.DeploymentEngine(FakeExecutor(),FakeVerifier(),Path("/tmp/b"),"192.0.2.10",PORTS,RUNTIME,"a"*32)
        with self.assertRaisesRegex(pp.BuilderStop,"ROUTE_NOT_BUILT"):
            e.mark_dns_leak_checkpoint(pp.Route.I,True)

    def test_persistent_state_rejects_version_and_duplicate_ports(self):
        base={"builder_version":pp.BUILDER_VERSION,"run_id":"a"*32,"target_binding":"b"*64,"accepted_routes":[],"ports":pp.asdict(PORTS),"ledger":{}}
        bad=dict(base); bad["builder_version"]="0.0.0"
        with self.assertRaisesRegex(pp.BuilderStop,"VERSION_MISMATCH"): pp.PersistentState.from_mapping(bad)
        bad=json.loads(json.dumps(base)); bad["ports"]["route_ii_tcp"]=bad["ports"]["route_i_tcp"]
        with self.assertRaisesRegex(pp.BuilderStop,"PORTS_INVALID"): pp.PersistentState.from_mapping(bad)

    def test_privileged_port_units_receive_only_bind_capability(self):
        privileged=pp._systemd_unit("pp-lab-i","/bin/true",privileged_port=True)
        ordinary=pp._systemd_unit("pp-lab-ii","/bin/true")
        self.assertIn("AmbientCapabilities=CAP_NET_BIND_SERVICE",privileged)
        self.assertIn("CapabilityBoundingSet=CAP_NET_BIND_SERVICE",privileged)
        self.assertNotIn("AmbientCapabilities",ordinary)
        self.assertIn("AmbientCapabilities=CAP_NET_BIND_SERVICE",pp.stage_i_apply_script(443))
        self.assertIn("AmbientCapabilities=CAP_NET_BIND_SERVICE",pp.stage_iii_apply_script(443))
        self.assertNotIn("AmbientCapabilities",pp.stage_ii_apply_script(8443))

    def test_server_only_accepts_shared_tcp_udp_port_without_formal_pass(self):
        ports=pp.Ports(443,8443,443)
        ex=FakeExecutor(); ver=FakeVerifier(); ledger=pp.AcceptanceLedger()
        with tempfile.TemporaryDirectory() as tmp:
            bundle=Path(tmp)/"bundle"
            engine=pp.DeploymentEngine(ex,ver,bundle,"192.0.2.10",ports,RUNTIME,"a"*32,ledger,server_only=True)
            engine.initialize()
            for route in pp.Route:
                engine.build_route(route,pp.NetworkClass.OPERATOR)
                self.assertFalse(engine.can_advance(route))
                engine.accept_server_stage(route)
                self.assertTrue(engine.can_advance(route))
                self.assertIs(ledger.route_verdict(route),pp.Verdict.PARTIAL)
            state=pp.PersistentState(pp.BUILDER_VERSION,"a"*32,"b"*64,("I","II","III"),ports,ledger,acceptance_mode="server_only")
            loaded=pp.PersistentState.from_mapping(state.to_jsonable())
            self.assertEqual(loaded.ports,ports)
            self.assertEqual(loaded.acceptance_mode,"server_only")
            self.assertIs(engine.finalize_server_only(),pp.Verdict.PARTIAL)
            self.assertTrue((bundle/"manifest.json").exists())
        self.assertEqual([event for event in ex.events if event[0]=="checkpoint"],[("checkpoint",r) for r in pp.Route])
        self.assertEqual(ex.events[-1],("finalize",None))

    def test_server_only_route_failure_rolls_back_current_stage(self):
        ex=FakeExecutor(fail=("health",pp.Route.II)); ver=FakeVerifier()
        with tempfile.TemporaryDirectory() as tmp:
            engine=pp.DeploymentEngine(ex,ver,Path(tmp)/"bundle","192.0.2.10",pp.Ports(443,8443,443),RUNTIME,"a"*32,server_only=True)
            engine.initialize(); engine.build_route(pp.Route.I,pp.NetworkClass.OPERATOR); engine.accept_server_stage(pp.Route.I)
            with self.assertRaisesRegex(pp.BuilderStop,"STAGE_II_FAIL"):
                engine.build_route(pp.Route.II,pp.NetworkClass.OPERATOR)
        self.assertIn(("rollback",pp.Route.II),ex.events)
        self.assertNotIn(("rollback",pp.Route.I),ex.events)

    def test_finalize_partial_does_not_publish_bundle_or_finalize_remote(self):
        ex=FakeExecutor(); ver=FakeVerifier(); l=pp.AcceptanceLedger()
        with tempfile.TemporaryDirectory() as tmp:
            e=pp.DeploymentEngine(ex,ver,Path(tmp)/"bundle","192.0.2.10",PORTS,RUNTIME,"a"*32,l,accepted_materials={pp.Route.I:I,pp.Route.II:II,pp.Route.III:III})
            self.assertIs(e.finalize(),pp.Verdict.PARTIAL)
            self.assertFalse((Path(tmp)/"bundle").exists())
        self.assertNotIn(("finalize",None),ex.events)

    def test_full_formal_flow_passes_only_after_all_evidence(self):
        ex=FakeExecutor(); ver=FakeVerifier(); l=pp.AcceptanceLedger()
        with tempfile.TemporaryDirectory() as tmp:
            bundle=Path(tmp)/"bundle"
            e=pp.DeploymentEngine(ex,ver,bundle,"192.0.2.10",PORTS,RUNTIME,"a"*32,l)
            e.initialize()
            e.build_route(pp.Route.I,pp.NetworkClass.WIFI); e.mark_dns_leak_checkpoint(pp.Route.I,True); e.accept_network(pp.Route.I,pp.NetworkClass.MOBILE); e.accept_route(pp.Route.I)
            e.build_route(pp.Route.II,pp.NetworkClass.MOBILE); e.accept_network(pp.Route.II,pp.NetworkClass.WIFI); e.mark_dns_leak_checkpoint(pp.Route.II,True); e.accept_route(pp.Route.II)
            e.build_route(pp.Route.III,pp.NetworkClass.WIFI); e.mark_dns_leak_checkpoint(pp.Route.III,True); e.accept_network(pp.Route.III,pp.NetworkClass.MOBILE); e.accept_route(pp.Route.III)
            self.assertIs(e.finalize(),pp.Verdict.PASS); self.assertTrue((bundle/"manifest.json").exists())
        self.assertEqual([x for x in ex.events if x[0]=="checkpoint"],[("checkpoint",pp.Route.I),("checkpoint",pp.Route.II),("checkpoint",pp.Route.III)])
        self.assertNotIn(("rollback",pp.Route.I),ex.events); self.assertEqual(ex.events[-1],("finalize",None))
        self.assertIs(l.final_verdict(),pp.Verdict.PASS)

    def test_dns_skip_style_abandon_rolls_back_and_clears_current_evidence(self):
        ex=FakeExecutor(); ver=FakeVerifier(); l=pp.AcceptanceLedger()
        with tempfile.TemporaryDirectory() as tmp:
            e=pp.DeploymentEngine(ex,ver,Path(tmp)/"b","192.0.2.10",PORTS,RUNTIME,"a"*32,l)
            e.build_route(pp.Route.I,pp.NetworkClass.WIFI); e.abandon_pending(pp.Route.I,failed=False)
        self.assertIn(("rollback",pp.Route.I),ex.events); self.assertEqual(l.data_path["I"],set()); self.assertNotIn("I",l.failed_routes)

    def test_pending_route_is_derived_from_current_evidence(self):
        l=pp.AcceptanceLedger(); state=pp.PersistentState(pp.BUILDER_VERSION,"a"*32,"b"*64,(),PORTS,l)
        self.assertIsNone(state.pending_route())
        l.data_path["I"]={"wifi"}
        self.assertIs(state.pending_route(),pp.Route.I)
        l.data_path["I"]={"wifi","mobile"}; l.restart["I"]=l.isolation["I"]=l.dns_leak_checkpoint["I"]=True
        accepted=pp.PersistentState(pp.BUILDER_VERSION,"a"*32,"b"*64,("I",),PORTS,l)
        self.assertIsNone(accepted.pending_route())

    def test_resume_probe_allows_one_pending_and_forbids_later_routes(self):
        l=pp.AcceptanceLedger(); l.data_path["I"]={"wifi","mobile"}; l.restart["I"]=l.isolation["I"]=l.dns_leak_checkpoint["I"]=True
        l.data_path["II"]={"mobile"}; l.restart["II"]=l.isolation["II"]=True; l.regression["II>I"]={"mobile"}
        state=pp.PersistentState(pp.BUILDER_VERSION,"a"*32,"b"*64,("I",),PORTS,l)
        self.assertIs(state.pending_route(),pp.Route.II)
        script=pp.resume_probe_script(state)
        self.assertIn("pp-lab-ii.service",script); self.assertIn("[ -e /etc/privatpirat/pp-lab-ii ]",script)
        self.assertIn("[ ! -e /etc/privatpirat/pp-lab-iii ]",script)
        self.assertIn('allowed.append(local_accepted+[pending])',script)

    def test_owner_checkpoint_is_idempotent_by_hash(self):
        script=pp.owner_checkpoint_script("a"*32,pp.Route.II)
        self.assertIn("accepted==expected_prefix+[route]",script)
        self.assertIn("config_sha256",script); self.assertIn("raise SystemExit(42)",script)

    def test_engine_can_hold_pending_material_without_accepting_it(self):
        l=pp.AcceptanceLedger(); l.data_path["I"]={"wifi","mobile"}; l.restart["I"]=l.isolation["I"]=l.dns_leak_checkpoint["I"]=True
        l.data_path["II"]={"mobile"}; l.restart["II"]=l.isolation["II"]=True; l.regression["II>I"]={"mobile"}
        with tempfile.TemporaryDirectory() as tmp:
            e=pp.DeploymentEngine(FakeExecutor(),FakeVerifier(),Path(tmp)/"b","192.0.2.10",PORTS,RUNTIME,"a"*32,l,accepted_materials={pp.Route.I:I,pp.Route.II:II},accepted_routes=[pp.Route.I])
            self.assertEqual(e.accepted,[pp.Route.I]); self.assertIn(pp.Route.II,e.materials); self.assertFalse(e.can_advance(pp.Route.II))

    def test_resume_owner_scripts_bind_run_ports_and_config_hashes(self):
        l=pp.AcceptanceLedger(); l.data_path["I"]={"wifi","mobile"}; l.restart["I"]=l.isolation["I"]=l.dns_leak_checkpoint["I"]=True
        state=pp.PersistentState(pp.BUILDER_VERSION,"a"*32,"b"*64,("I",),PORTS,l)
        init=pp.owner_initialize_script(state.run_id,PORTS); cp=pp.owner_checkpoint_script(state.run_id,pp.Route.I); probe=pp.resume_probe_script(state)
        self.assertIn("owner.json",init); self.assertIn('"accepted":[]',init); self.assertIn("config_sha256",cp); self.assertIn("RESUME_PROBE=PASS",probe); self.assertNotIn("203.0.113",probe)

    def test_all_shell_renderers_parse_with_bash(self):
        import shutil, subprocess
        if not shutil.which("bash"): self.skipTest("bash unavailable")
        l=pp.AcceptanceLedger(); l.data_path["I"]={"wifi","mobile"}; l.restart["I"]=l.isolation["I"]=l.dns_leak_checkpoint["I"]=True
        state=pp.PersistentState(pp.BUILDER_VERSION,"a"*32,"b"*64,("I",),PORTS,l)
        scripts=[pp.stage_i_apply_script(23451),pp.stage_ii_apply_script(23452),pp.stage_iii_apply_script(23453)]
        for r,p in ((pp.Route.I,23451),(pp.Route.II,23452),(pp.Route.III,23453)):
            for a in ("health","restart","stop","start"): scripts.append(pp.server_action_script(r,p,a))
            scripts.append(pp.rollback_script(r,p))
        scripts += [pp.owner_initialize_script("a"*32,PORTS),pp.owner_checkpoint_script("a"*32,pp.Route.I),pp.resume_probe_script(state),pp.finalize_remote_script()]
        for script in scripts:
            proc=subprocess.run(["bash","-n"],input=script,text=True,capture_output=True); self.assertEqual(proc.returncode,0,proc.stderr)

    def test_static_safety_guards(self):
        s=MODULE_PATH.read_text()
        self.assertNotIn("sshpass",s); self.assertNotIn("StrictHostKeyChecking=no",s); self.assertNotIn("UserKnownHostsFile=/dev/null",s)
        self.assertNotRegex(s,r"curl\s+[^\n|]*\|\s*(?:sh|bash)")
        self.assertIn("StrictHostKeyChecking=yes",s); self.assertIn("BatchMode=yes",s)

    def test_saved_loopback_preserves_entire_pair_except_endpoints(self):
        server, client, _ = self.config_pair_fixture()
        s, c = json.loads(server), json.loads(client)
        s['inbounds'][0].update(listen='127.0.0.1', port=23457)
        c['inbounds'][0].update(listen='127.0.0.1', port=23458)
        c['outbounds'][0]['settings']['vnext'][0].update(address='127.0.0.1', port=23457)
        self.assertEqual(set(pp.saved_loopback_pair(server, client, json.dumps(s), json.dumps(c)).values()), {'MATCH'})
        for field in ('target', 'show', 'privateKey'):
            changed = json.loads(json.dumps(s))
            changed['inbounds'][0]['streamSettings']['realitySettings'][field] = 'CHANGED'
            with self.subTest(field=field), self.assertRaisesRegex(pp.BuilderStop, 'PRESERVATION_FAIL'):
                pp.saved_loopback_pair(server, client, json.dumps(changed), json.dumps(c))
        c['log']['loglevel'] = 'debug'
        with self.assertRaisesRegex(pp.BuilderStop, 'PRESERVATION_FAIL'):
            pp.saved_loopback_pair(server, client, json.dumps(s), json.dumps(c))

    def test_saved_loopback_scope_stops_before_ssh(self):
        for extra in ([], ['--server-only', '--diagnostic-route-i'], ['--server-only', '--trust-current-host-key']):
            args = pp.build_parser().parse_args(['--diagnostic-vps-loopback']+extra)
            with mock.patch.object(pp, 'SSHControlMaster') as ssh, self.assertRaises(pp.BuilderStop):
                pp.run_saved_vps_loopback_after_gate(args)
            ssh.assert_not_called()
        with self.assertRaises(SystemExit):
            pp.build_parser().parse_args(['--apply', '--diagnostic-vps-loopback'])

    def test_saved_loopback_transaction_cleanup_and_no_deployment(self):
        for outcome in ('pass', 'http-fail', 'mismatch'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); private = root/'private'; source = private/'lilfox-am'/'verify'/('a'*32)
                pp.ensure_private_dir(source)
                server, client, _ = self.config_pair_fixture()
                pp.write_private(source/'verify-I-1-1.server.json', server)
                pp.write_private(source/'verify-I-1-1.json', client)
                pp.write_private(private/'lilfox-am'/'known_hosts', 'synthetic pinned key')
                identity = root/'identity'; pp.write_private(identity, 'synthetic identity')
                archive = root/'cache'/'lilfox-am'/pp.ARTIFACTS['xray-linux-amd64'].name
                pp.write_private(archive, 'synthetic archive')
                fingerprint = 'SHA256:'+'A'*43
                state = pp.PersistentState(pp.BUILDER_VERSION, 'a'*32, pp.target_binding('192.0.2.10','root',22,fingerprint), (), PORTS, pp.AcceptanceLedger(), 'I', 'server_only')
                session = pp.RemoteSession('192.0.2.10','root',22,private/'lilfox-am'/'known_hosts',control_path=root/'ctl')
                events = []
                class Executor:
                    def __init__(self, *_args, **_kw): pass
                    def _run(self, script, marker, **kw): events.append((marker, script))
                    def _scp_to(self, path, remote): events.append(('upload', remote))
                    def _scp_from(self, remote, path):
                        name = remote.rsplit('/',1)[1]
                        if name == 'server.json':
                            value = json.loads(server); value['inbounds'][0].update(listen='127.0.0.1', port=23457)
                            if outcome == 'mismatch': value['log']['loglevel'] = 'debug'
                        elif name == 'client.json':
                            value = json.loads(client); value['inbounds'][0].update(listen='127.0.0.1', port=23458)
                            value['outbounds'][0]['settings']['vnext'][0].update(address='127.0.0.1', port=23457)
                        elif name == 'result.json':
                            value = {'loopback_http': {'ok': outcome == 'pass'}, 'error': None, 'processes_remaining': 0, 'listeners_remaining': 0, 'saved_files':['server.log','client.log']}
                        else: value = {}
                        pp.write_private(path,json.dumps(value))
                args = pp.build_parser().parse_args(['--diagnostic-vps-loopback','--server-only','--profile-name','lilfox-am','--target-host','192.0.2.10','--ssh-user','root','--ssh-port','22','--identity-file',str(identity),'--saved-run-id','a'*32])
                with mock.patch.object(pp,'private_root',return_value=private), mock.patch.object(pp,'cache_root',return_value=root/'cache'), mock.patch.object(pp,'load_state',return_value=state), mock.patch.object(pp,'verify_sha256',return_value=True), mock.patch.object(pp.subprocess,'run',return_value=mock.Mock(returncode=0,stdout='256 '+fingerprint+' synthetic (ED25519)')), mock.patch.object(pp,'SSHControlMaster',return_value=nullcontext(session)), mock.patch.object(pp,'preflight_session'), mock.patch.object(pp,'_load_runtime',return_value=RUNTIME), mock.patch.object(pp,'SSHStageExecutor',Executor), mock.patch.object(pp,'save_state') as save, mock.patch('builtins.print'):
                    if outcome == 'pass': self.assertEqual(pp.run_saved_vps_loopback_after_gate(args),0)
                    else:
                        with self.assertRaises(pp.BuilderStop): pp.run_saved_vps_loopback_after_gate(args)
                    save.assert_not_called()
                markers = [e[0] for e in events]
                self.assertEqual(markers[-1], 'LOOPBACK_CLEANUP=PASS')
                self.assertEqual('LOOPBACK_FINISHED=SAVED' in markers, outcome != 'mismatch')
                self.assertNotIn('systemctl', '\n'.join(e[1] for e in events))
                self.assertEqual((source/'verify-I-1-1.server.json').read_text(), server)
                self.assertEqual((source/'verify-I-1-1.json').read_text(), client)
                if outcome != 'mismatch':
                    status_path, = (private/'lilfox-am'/'diagnostics').glob('*/status-I.json')
                    status = json.loads(status_path.read_text())
                    self.assertEqual(status['client_verified'], 'NOT_RECORDED')
                    self.assertEqual(status['read_client_finished'], 'NOT_RECORDED')
                    self.assertEqual(status['server_handshake'], 'NOT_RECORDED')
                    self.assertEqual(stat.S_IMODE(status_path.stat().st_mode), 0o600)

    def test_saved_loopback_agent_watchdog_scope_and_diagnostics(self):
        compile(pp.SAVED_LOOPBACK_AGENT,'<test-agent>','exec')
        self.assertIn("'--max-time', '20'",pp.SAVED_LOOPBACK_AGENT)
        self.assertIn("if not live and not result['loopback_http']['ok']",pp.SAVED_LOOPBACK_AGENT)
        self.assertIn('child.terminate()',pp.SAVED_LOOPBACK_AGENT)
        self.assertIn('child.kill()',pp.SAVED_LOOPBACK_AGENT)
        self.assertIn('signal.SIGHUP',pp.SAVED_LOOPBACK_AGENT)
        self.assertNotRegex(pp.SAVED_LOOPBACK_AGENT,r"'systemctl'\s*,\s*'(?:start|stop|restart|enable|disable)'")
        self.assertNotIn('show=',pp.SAVED_LOOPBACK_AGENT)

    def test_paired_saved_stage_preserves_keys_instead_of_regenerating(self):
        script = pp.stage_i_apply_script(443,diagnostic=True,saved_pair=True)
        self.assertIn('"$ROOT/source.server.json" "$CFG"',script)
        self.assertNotIn('uuid.uuid4',script)
        self.assertNotIn('"$XRAY" x25519',script)
        self.assertNotIn('openssl rand',script)
        with self.assertRaises(pp.BuilderStop): pp.stage_i_apply_script(443,saved_pair=True)

    def test_paired_external_template_and_failure_endpoint_are_preserved(self):
        server, client, material = self.config_pair_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); template=root/'template.json'
            source=json.loads(client); source['outbounds'][0]['streamSettings']['realitySettings']['spiderX']='/retained'
            pp.write_private(template,json.dumps(source))
            def snapshot(path): pp.write_private(path,server)
            v=pp.LocalClientVerifier('192.0.2.10',PORTS,RUNTIME,'192.0.2.10',{'client_xray':Path('/bin/true')},root/'verify',preserve_logs=True,route_i_snapshot=snapshot,route_i_template=template)
            proc=mock.Mock(); proc.poll.return_value=None
            with mock.patch.object(v,'_free_local_port',return_value=10809),mock.patch.object(v,'_wait_socks',return_value=True),mock.patch.object(pp.subprocess,'Popen',return_value=proc),mock.patch.object(v,'_curl_status_body',side_effect=[(200,'ok'),pp.BuilderStop('CLIENT_CURL_EXIT_56=STOP')]),mock.patch('builtins.print'):
                with self.assertRaises(pp.BuilderStop): v._verify_round(pp.Route.I,material,1)
            actual=json.loads(v.last_route_i_config.read_text())
            expected=json.loads(json.dumps(source)); expected['inbounds'][0].update(listen='127.0.0.1',port=10809)
            self.assertEqual(actual,expected)
            attempt=json.loads(v.last_route_i_config.with_suffix('.attempt.json').read_text())
            self.assertEqual(attempt['url'],pp.HTTPS_PROBE_URL)
            self.assertEqual([event['url'] for event in attempt['probe_events']],[pp.HTTP_PROBE_URL,pp.HTTPS_PROBE_URL])
            self.assertIn('ended_at_epoch',attempt)
            proc.terminate.assert_called_once()
            self.assertEqual(json.loads(template.read_text()),source)

    def test_paired_failure_hook_precedes_capture_and_always_rolls_back(self):
        for hook_fails in (False,True):
            ex=FakeExecutor(); verifier=FakeVerifier()
            verifier.verify=mock.Mock(side_effect=pp.BuilderStop('CLIENT_CURL_EXIT_56=STOP'))
            def hook(route,error):
                ex.events.append(('control',route))
                if hook_fails: raise pp.BuilderStop('PAIRED_CONTROL_FAIL=STOP')
            with tempfile.TemporaryDirectory() as tmp,mock.patch('builtins.print'):
                engine=pp.DeploymentEngine(ex,verifier,Path(tmp)/'bundle','192.0.2.10',PORTS,RUNTIME,'a'*32,failure_diagnostic=hook)
                with self.assertRaisesRegex(pp.BuilderStop,'STAGE_I_FAIL_CLIENT_CURL_EXIT_56'):
                    engine.build_route(pp.Route.I,pp.NetworkClass.OPERATOR)
            self.assertLess(ex.events.index(('control',pp.Route.I)),ex.events.index(('capture',pp.Route.I)))
            self.assertLess(ex.events.index(('capture',pp.Route.I)),ex.events.index(('rollback',pp.Route.I)))
            self.assertNotIn(('apply',pp.Route.II),ex.events)

    def test_paired_live_control_same_process_preservation_cleanup_and_stop(self):
        for outcome in ('pass','process-changed','config-changed','curl-fail'):
            with self.subTest(outcome=outcome),tempfile.TemporaryDirectory() as tmp,mock.patch('builtins.print'):
                root=Path(tmp); server,client,_=self.config_pair_fixture()
                cfg=root/'verify'/'verify-I-1-1.json'; pp.write_private(cfg,client)
                pp.write_private(cfg.with_suffix('.server.json'),server)
                identity={'pid':123,'start_ticks':'42','boot_id':'synthetic','binary_sha256':'a'*64,'config_sha256':'b'*64}
                info={'identity':identity,'observed_epoch':1,'platform':'synthetic'}
                pp.write_private(cfg.with_suffix('.server.meta.json'),json.dumps(info))
                verifier=mock.Mock(last_route_i_config=cfg,last_route_i_probe={'url':pp.HTTPS_PROBE_URL,'started_at_epoch':2,'destination':'192.0.2.10'})
                session=pp.RemoteSession('192.0.2.10','root',22,root/'known',control_path=root/'ctl')
                ex=pp.SSHStageExecutor(session,PORTS,RUNTIME,{},root/'private',diagnostic_run_id='a'*32,paired_control=True)
                events=[]
                def capture(route):
                    events.append('capture')
                    for name in ('server-I.log','server-I.jsonl','status-I.json'): pp.write_private(root/'private'/'diagnostics'/('a'*32)/name,'{}')
                    return True
                def download(remote,path):
                    name=remote.rsplit('/',1)[1]
                    if name=='server.json': value=json.loads(server)
                    elif name=='client.json':
                        value=json.loads(client); value['inbounds'][0].update(listen='127.0.0.1',port=10810)
                        value['outbounds'][0]['settings']['vnext'][0]['address']='127.0.0.1'
                        if outcome=='config-changed': value['log']['loglevel']='debug'
                    elif name=='result.json': value={'error':None,'loopback_http':{'ok':outcome!='curl-fail'},'processes_remaining':0,'listeners_remaining':0,'saved_files':['client.log'],'server_identity_before':identity,'server_identity_after':identity}
                    else: value={}
                    pp.write_private(path,json.dumps(value))
                current=info if outcome!='process-changed' else {'identity':dict(identity,pid=124)}
                def run(script,marker,**kw): events.append(marker)
                with mock.patch.object(ex,'route_i_process_info',return_value=current),mock.patch.object(ex,'capture_diagnostics',side_effect=capture),mock.patch.object(ex,'_run',side_effect=run),mock.patch.object(ex,'_scp_to'),mock.patch.object(ex,'_scp_from',side_effect=download),mock.patch.object(ex,'action') as action:
                    if outcome in ('process-changed','config-changed'):
                        with self.assertRaises(pp.BuilderStop): ex.paired_failure_control(pp.Route.I,pp.BuilderStop('CLIENT_CURL_EXIT_56=STOP'),verifier)
                    else: ex.paired_failure_control(pp.Route.I,pp.BuilderStop('CLIENT_CURL_EXIT_56=STOP'),verifier)
                    with self.assertRaisesRegex(pp.BuilderStop,'ALREADY_USED'):
                        ex.paired_failure_control(pp.Route.I,pp.BuilderStop('CLIENT_CURL_EXIT_56=STOP'),verifier)
                    action.assert_not_called()
                self.assertEqual('LOOPBACK_FINISHED=SAVED' in events,outcome in ('pass','curl-fail'))
                if outcome!='process-changed':
                    self.assertEqual(events[-1],'PAIRED_CLEANUP=PASS')
                    self.assertLess(events.index('capture'),events.index('LIVE_CLIENT_PREPARE=PASS'))
                self.assertEqual(cfg.read_text(),client)
                self.assertEqual(cfg.with_suffix('.server.json').read_text(),server)

    def test_paired_control_skips_non_data_failures_and_other_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=pp.RemoteSession('192.0.2.10','root',22,Path(tmp)/'known',control_path=Path(tmp)/'ctl')
            ex=pp.SSHStageExecutor(session,PORTS,RUNTIME,{},Path(tmp)/'private',diagnostic_run_id='a'*32,paired_control=True)
            verifier=mock.Mock(last_route_i_probe={'url':pp.HTTP_PROBE_URL})
            with mock.patch.object(ex,'route_i_process_info') as info:
                for route,error in ((pp.Route.II,'CLIENT_CURL_EXIT_56=STOP'),(pp.Route.I,'ROUTE_I_CONFIG_PAIR_MISMATCH=STOP'),(pp.Route.I,'CLIENT_VERIFIER_PROCESS_EXIT=STOP'),(pp.Route.I,'STOP_ISOLATION_ROUTE_STILL_AVAILABLE=STOP')):
                    ex.paired_failure_control(route,pp.BuilderStop(error),verifier)
                info.assert_not_called()
                self.assertFalse(ex.control_attempted)

    def test_paired_mode_scope_and_agent_are_bounded(self):
        args=pp.build_parser().parse_args(['--apply','--loopback-on-failure'])
        with mock.patch.object(pp,'perform_target_inputs') as inputs,self.assertRaisesRegex(pp.BuilderStop,'SCOPE_INVALID'):
            pp.run_deployment_after_gate(args)
        inputs.assert_not_called()
        with mock.patch('builtins.print'):
            self.assertEqual(pp.main(['--preflight-only','--loopback-on-failure']),2)
        compile(pp.SAVED_LOOPBACK_AGENT,'<paired-agent>','exec')
        self.assertIn("[('client', client)] if live",pp.SAVED_LOOPBACK_AGENT)
        self.assertIn("if not live and not result['loopback_http']['ok']",pp.SAVED_LOOPBACK_AGENT)
        self.assertIn("result['server_identity_after'] != expected",pp.SAVED_LOOPBACK_AGENT)

    def test_paired_cli_wires_saved_pair_without_control_on_success(self):
        with tempfile.TemporaryDirectory() as tmp,mock.patch('builtins.print'):
            root=Path(tmp); private=root/'private'/'lilfox-am'; source=private/'verify'/('a'*32)
            server,client,_=self.config_pair_fixture()
            pp.write_private(source/'verify-I-1-1.server.json',server)
            pp.write_private(source/'verify-I-1-1.json',client)
            pp.write_private(private/'runtime.json',json.dumps({'cover_hostname':RUNTIME.cover_hostname}))
            pp.write_private(private/'known_hosts','synthetic pin')
            identity=root/'identity'; pp.write_private(identity,'synthetic identity')
            fp='SHA256:'+'A'*43; binding=pp.target_binding('192.0.2.10','root',22,fp)
            state_path=root/'state'/'lilfox-am'/'state.json'
            pp.save_state(state_path,pp.PersistentState(pp.BUILDER_VERSION,'a'*32,binding,(),PORTS,pp.AcceptanceLedger(),'I','server_only'))
            session=pp.RemoteSession('192.0.2.10','root',22,private/'known_hosts')
            context=pp.PreflightContext('lilfox-am','lilfox-am',session,pp.parse_inventory(GOOD),PORTS,private,state_path.parent,{},binding)
            ex=FakeExecutor(); ex.paired_failure_control=mock.Mock()
            ex.capture_diagnostics=lambda route: True
            args=pp.build_parser().parse_args(['--apply','--server-only','--diagnostic-route-i','--loopback-on-failure','--saved-run-id','a'*32,'--profile-name','lilfox-am','--target-host','192.0.2.10','--ssh-user','root','--ssh-port','22','--identity-file',str(identity)])
            with mock.patch.object(pp,'private_root',return_value=root/'private'),mock.patch.object(pp,'state_root',return_value=root/'state'),mock.patch.object(pp,'local_prerequisites',return_value={'ok':True}),mock.patch.object(pp.subprocess,'run',return_value=mock.Mock(returncode=0,stdout='256 '+fp+' synthetic (ED25519)')),mock.patch.object(pp,'perform_target_inputs',return_value=('lilfox-am','lilfox-am','192.0.2.10',22,'root',fp,private/'known_hosts')),mock.patch.object(pp,'SSHControlMaster',return_value=nullcontext(session)),mock.patch.object(pp,'preflight_session',return_value=context),mock.patch.object(pp,'remote_cover_probe'),mock.patch.object(pp,'prepare_artifacts',return_value={}),mock.patch.object(pp,'SSHStageExecutor',return_value=ex) as factory,mock.patch.object(pp,'LocalClientVerifier',return_value=FakeVerifier()) as clients:
                self.assertEqual(pp.run_deployment_after_gate(args),0)
            self.assertTrue(factory.call_args.kwargs['paired_control'])
            self.assertEqual(factory.call_args.kwargs['saved_route_i'],source)
            self.assertEqual(clients.call_args.kwargs['route_i_template'],source/'verify-I-1-1.json')
            ex.paired_failure_control.assert_not_called()
            self.assertNotIn(('apply',pp.Route.II),ex.events)
            self.assertNotIn(('apply',pp.Route.III),ex.events)
            self.assertEqual(pp.load_state(state_path).accepted_routes,('I',))
            self.assertEqual((source/'verify-I-1-1.server.json').read_text(),server)

    def checkpoint_body(self, route):
        return re.search(r"<<'__PP_CHECKPOINT__'\n(.*?)\n__PP_CHECKPOINT__", pp.owner_checkpoint_script("a" * 32, route), re.S).group(1)

    def test_checkpoint_python_executes_idempotently_and_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); owner = root / "owner.json"; cfg = root / "config"
            owner.write_text(json.dumps({"run_id": "a" * 32, "accepted": [], "config_sha256": {}}))
            cfg.write_text("synthetic config\n")
            body = self.checkpoint_body(pp.Route.I)
            def invoke():
                return subprocess.run([sys.executable, "-B", "-", str(owner), "a" * 32, "I", str(cfg)], input=body, text=True, capture_output=True, timeout=5)
            self.assertEqual(invoke().returncode, 0)
            first = owner.read_bytes()
            self.assertEqual(invoke().returncode, 0)
            self.assertEqual(owner.read_bytes(), first)
            cfg.write_text("changed fixture\n")
            self.assertEqual(invoke().returncode, 42)
            self.assertEqual(owner.read_bytes(), first)

    @staticmethod
    def sandbox_shell(script, root):
        # Generated scripts only see disposable paths and fake system commands.
        for source, target in ((pp.REMOTE_ROOT, root / "remote"),
                               ("/etc/privatpirat", root / "config"),
                               ("/etc/systemd/system", root / "units"),
                               ("/usr/local/lib/privatpirat", root / "binary")):
            script = script.replace(source, str(target))
        return script

    def test_stage_prechecks_reject_existing_user_port_and_paths_before_writes(self):
        for route in pp.Route:
            for obstacle in ("user", "port", "ss_error", "unit", "config"):
                with self.subTest(route=route, obstacle=obstacle), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp); remote = root / "remote"; remote.mkdir()
                    (root / "units").mkdir(); (root / "config").mkdir(); (root / "binary").mkdir()
                    (remote / "runtime.json").write_text('{}')
                    (remote / pp.ARTIFACTS["xray-linux-amd64"].name).write_text('fixture')
                    (remote / "owner.json").write_text(json.dumps({"run_id": "a" * 32, "accepted": [], "config_sha256": {}}))
                    xray = root / "binary" / f"xray-{pp.XRAY_VERSION}" / "xray"
                    if route is not pp.Route.I:
                        xray.parent.mkdir(); xray.write_text('fixture'); xray.chmod(0o700)
                    name = f"pp-lab-{route.value.lower()}"
                    sentinel = root / ("units/" + name + ".service" if obstacle == "unit" else "config/" + name)
                    if obstacle in ("unit", "config"):
                        sentinel.write_text("foreign resource")
                    script = {pp.Route.I: pp.stage_i_apply_script, pp.Route.II: pp.stage_ii_apply_script, pp.Route.III: pp.stage_iii_apply_script}[route](23451)
                    stubs = f'''id() {{ if [ "$1" = -u ]; then printf 0; elif [ "{obstacle}" = user ] && [ "$1" = {name} ]; then return 0; else return 1; fi; }}
ss() {{ if [ "{obstacle}" = ss_error ]; then return 1; elif [ "{obstacle}" = port ]; then printf 'LISTEN 0 0 0.0.0.0:23451\\n'; fi; }}
systemctl() {{ return 0; }}
sha256sum() {{ if [ "${{1:-}}" = -c ]; then cat >/dev/null; else printf 'fixturehash fixture\\n'; fi; }}
install() {{ printf UNEXPECTED_WRITE; return 90; }}
useradd() {{ printf UNEXPECTED_WRITE; return 90; }}
userdel() {{ printf UNEXPECTED_DELETE; return 90; }}
'''
                    proc = subprocess.run(["bash", "-c", stubs + self.sandbox_shell(script, root)], capture_output=True, text=True, timeout=5)
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertNotIn("UNEXPECTED_", proc.stdout)
                    self.assertFalse((remote / f"stage-{route.value}.owned").exists())
                    if obstacle in ("unit", "config"):
                        self.assertEqual(sentinel.read_text(), "foreign resource")

    def test_rollback_requires_matching_receipt_and_never_deletes_unowned_config(self):
        for receipt in (None, "b" * 32, "a" * 32):
            with self.subTest(receipt=receipt), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); remote = root / "remote"; remote.mkdir()
                (remote / "owner.json").write_text(json.dumps({"run_id": "a" * 32, "accepted": [], "config_sha256": {}}))
                foreign = root / "config/pp-lab-i"; foreign.mkdir(parents=True)
                (foreign / "sentinel").write_text("preserve")
                if receipt:
                    mark = remote / "stage-I.owned"; mark.mkdir(); (mark / "run-id").write_text(receipt)
                script = self.sandbox_shell(pp.rollback_script(pp.Route.I, 23451), root)
                stubs = 'id() { return 1; }; ss() { return 0; }; userdel() { printf UNEXPECTED_DELETE; return 1; }; systemctl() { return 0; };\n'
                result = subprocess.run(["bash", "-c", stubs + script], text=True, capture_output=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("UNEXPECTED_DELETE", result.stdout)
                self.assertEqual((foreign / "sentinel").read_text(), "preserve")

    def test_real_stage_i_filesystem_transaction_and_user_creation_race(self):
        import zipfile
        for race in (False, True):
            with self.subTest(user_creation_race=race), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); remote = root / "remote"; remote.mkdir()
                (root / "units").mkdir()
                sentinel = root / "unrelated"; sentinel.write_text("preserve")
                (remote / "owner.json").write_text(json.dumps({"run_id": "a" * 32, "accepted": [], "config_sha256": {}}))
                (remote / "runtime.json").write_text(json.dumps({"cover_hostname": "cover.example"}))
                with zipfile.ZipFile(remote / pp.ARTIFACTS["xray-linux-amd64"].name, 'w') as z:
                    z.writestr('xray', '#!/bin/sh\nif [ "$1" = x25519 ]; then printf "PrivateKey: ' + 'A' * 43 + '\\nPassword (PublicKey): ' + 'B' * 43 + '\\n"; fi\nexit 0\n')
                stubs = f'''id() {{ if [ "$1" = -u ]; then printf 0; elif [ -f {str(root / 'user')!r} ]; then return 0; else return 1; fi; }}
useradd() {{ : > {str(root / 'user')!r}; return {1 if race else 0}; }}
userdel() {{ printf USER_DELETE; rm -f {str(root / 'user')!r}; }}
chown() {{ return 0; }}
openssl() {{ printf 'aabbccddeeff0011\\n'; }}
sha256sum() {{ cat >/dev/null; return 0; }}
systemctl() {{ case "$1" in enable) : > {str(root / 'active')!r};; disable) rm -f {str(root / 'active')!r};; is-active) test -f {str(root / 'active')!r};; *) return 0;; esac; }}
ss() {{ if [ -f {str(root / 'active')!r} ]; then printf 'LISTEN 0 0 0.0.0.0:23451\\n'; fi; }}
'''
                stage = self.sandbox_shell(pp.stage_i_apply_script(23451), root)
                result = subprocess.run(['bash', '-c', stubs + stage], text=True, capture_output=True, timeout=10)
                if race:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue((root / 'user').exists())
                    self.assertNotIn('USER_DELETE', result.stdout)
                    self.assertFalse((remote / 'stage-I.owned/user').exists())
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    cfg = json.loads((root / 'config/pp-lab-i/config.json').read_text())
                    self.assertEqual(cfg['inbounds'][0]['streamSettings']['network'], 'raw')
                    self.assertEqual(stat.S_IMODE((root / 'config').stat().st_mode), 0o755)
                    self.assertEqual(stat.S_IMODE((root / 'binary').stat().st_mode), 0o755)
                    self.assertTrue((remote / 'stage-I.owned/user').exists())
                    rollback = self.sandbox_shell(pp.rollback_script(pp.Route.I, 23451), root)
                    result = subprocess.run(['bash', '-c', stubs + rollback], text=True, capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(remote.exists())
                    self.assertFalse((root / 'config').exists())
                    self.assertFalse((root / 'binary').exists())
                    self.assertFalse((root / 'user').exists())
                    self.assertFalse((root / 'active').exists())
                self.assertEqual(sentinel.read_text(), 'preserve')

    def test_owned_rollback_preserves_prior_config_and_clears_only_current_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); remote = root / "remote"; remote.mkdir()
            prior = root / "config/pp-lab-i/config.json"; prior.parent.mkdir(parents=True); prior.write_text("prior fixture")
            current = root / "config/pp-lab-ii"; current.mkdir(); (current / "config.json").write_text("current fixture")
            owner = remote / "owner.json"
            owner.write_text(json.dumps({"run_id": "a" * 32, "accepted": ["I"], "config_sha256": {"I": hashlib.sha256(prior.read_bytes()).hexdigest()}}))
            mark = remote / "stage-II.owned"; mark.mkdir(); (mark / "run-id").write_text("a" * 32); (mark / "config").touch()
            script = self.sandbox_shell(pp.rollback_script(pp.Route.II, 23452), root)
            stubs = 'id() { return 1; }; ss() { return 0; }; systemctl() { return 0; }; userdel() { printf UNEXPECTED_DELETE; return 1; };\n'
            proc = subprocess.run(["bash", "-c", stubs + script], text=True, capture_output=True, timeout=5)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse(current.exists()); self.assertFalse(mark.exists())
            self.assertEqual(prior.read_text(), "prior fixture")
            self.assertEqual(json.loads(owner.read_text())["accepted"], ["I"])
            self.assertNotIn("UNEXPECTED_DELETE", proc.stdout)

    def test_rollback_regression_failure_marks_prior_route_failed_and_stops(self):
        ex = FakeExecutor(fail=("health", pp.Route.II)); ver = FakeVerifier(fail_verify_calls=(5,))
        with tempfile.TemporaryDirectory() as tmp:
            engine = pp.DeploymentEngine(ex, ver, Path(tmp) / "bundle", "192.0.2.10", PORTS, RUNTIME, "a" * 32, server_only=True)
            engine.initialize(); engine.build_route(pp.Route.I, pp.NetworkClass.OPERATOR); engine.accept_server_stage(pp.Route.I)
            with self.assertRaisesRegex(pp.BuilderStop, "ROLLBACK_REGRESSION_FAIL"):
                engine.build_route(pp.Route.II, pp.NetworkClass.OPERATOR)
            self.assertIn("I", engine.ledger.failed_routes)
            self.assertFalse(engine.can_advance(pp.Route.I))
            self.assertIn(("rollback", pp.Route.II), ex.events)
            self.assertNotIn(("apply", pp.Route.III), ex.events)

    def test_route_ii_low_port_receives_bind_capability(self):
        self.assertIn("AmbientCapabilities=CAP_NET_BIND_SERVICE", pp.stage_ii_apply_script(443))
        self.assertNotIn("AmbientCapabilities", pp.stage_ii_apply_script(8443))

    def test_full_server_only_cli_uses_real_generated_checkpoints_and_reports_partial(self):
        outer = self
        with tempfile.TemporaryDirectory() as tmp, mock.patch('builtins.print') as printed:
            root = Path(tmp); private = root / "private" / "fixture"; state_path = root / "state" / "fixture" / "state.json"
            session = pp.RemoteSession("192.0.2.10", "root", 22, private / "known_hosts")
            fp = "SHA256:" + "A" * 43; binding = pp.target_binding(session.host, session.user, session.port, fp)
            context = pp.PreflightContext("fixture", "fixture", session, pp.parse_inventory(GOOD), PORTS, private, state_path.parent, {}, binding)
            class Executor(FakeExecutor):
                def initialize_owner(self, run_id):
                    super().initialize_owner(run_id)
                    self.run_id = run_id
                    (root / "owner.json").write_text(json.dumps({"run_id": run_id, "accepted": [], "config_sha256": {}}))
                def checkpoint(self, run_id, route):
                    cfg = root / (route.value + '.config'); cfg.write_text('synthetic stage ' + route.value)
                    code = outer.checkpoint_body(route)
                    proc = subprocess.run([sys.executable, '-B', '-', str(root / 'owner.json'), run_id, route.value, str(cfg)], input=code, text=True, capture_output=True, timeout=5)
                    outer.assertEqual(proc.returncode, 0, proc.stderr)
                    super().checkpoint(run_id, route)
            ex = Executor()
            args = pp.build_parser().parse_args(['--apply', '--server-only', '--profile-name', 'fixture'])
            with mock.patch.object(pp, 'private_root', return_value=root / 'private'), mock.patch.object(pp, 'state_root', return_value=root / 'state'), mock.patch.object(pp, 'local_prerequisites', return_value={'ok': True}), mock.patch.object(pp, 'perform_target_inputs', return_value=('fixture', 'fixture', session.host, 22, 'root', fp, private / 'known_hosts')), mock.patch.object(pp, 'SSHControlMaster', return_value=nullcontext(session)), mock.patch.object(pp, 'preflight_session', return_value=context), mock.patch.object(pp.getpass, 'getpass', return_value='cover.example'), mock.patch.object(pp, 'remote_cover_probe'), mock.patch.object(pp, 'prepare_artifacts', return_value={}), mock.patch.object(pp, 'SSHStageExecutor', return_value=ex), mock.patch.object(pp, 'LocalClientVerifier', return_value=FakeVerifier()):
                self.assertEqual(pp.main(['--apply', '--server-only', '--profile-name', 'fixture']), 0)
            self.assertEqual(json.loads((root / 'owner.json').read_text())['accepted'], ['I', 'II', 'III'])
            self.assertEqual([route for op, route in ex.events if op == 'apply'], list(pp.Route))
            self.assertEqual(pp.load_state(state_path).ledger.final_verdict(), pp.Verdict.PARTIAL)
            self.assertTrue((private / 'client-bundle/manifest.json').exists())
            messages = '\n'.join(str(c.args[0]) for c in printed.call_args_list)
            self.assertIn('VERDICT=PARTIAL', messages)
            self.assertIn('FORMAL_ACCEPTANCE=CLIENT_TEST_PENDING', messages)

    def test_render_check(self): self.assertEqual(pp.render_check(),0)


if __name__ == "__main__": unittest.main()
