import importlib.util
import json
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
            self.assertNotIn("TOP_SECRET_PAYLOAD",argv)
            self.assertNotIn("scp ",argv)
        source=MODULE_PATH.read_text()
        self.assertNotIn("sshpass",source)
        self.assertNotIn("sudo -S",source)

    def test_route_renderers(self):
        i=json.loads(pp.render_xray_server_config(pp.Route.I,23451,I,"cover.example","C"*43)); ii=json.loads(pp.render_xray_server_config(pp.Route.II,23452,II,"cover.example","D"*43))
        self.assertEqual(i["inbounds"][0]["streamSettings"]["network"],"raw"); self.assertEqual(ii["inbounds"][0]["streamSettings"]["network"],"xhttp")
        ci=json.loads(pp.render_xray_client_config(pp.Route.I,"192.0.2.10",23451,I,"cover.example",10808)); self.assertEqual(ci["outbounds"][0]["streamSettings"]["realitySettings"]["fingerprint"],"firefox")
        hy=pp.render_hysteria_client_config("192.0.2.10",23453,III,10808); self.assertIn("pinSHA256",hy); self.assertIn("insecure: true",hy)

    def test_bundle_permissions_and_manifest_sanitized(self):
        with tempfile.TemporaryDirectory() as tmp:
            files=pp.write_client_bundle(Path(tmp)/"bundle","192.0.2.10",PORTS,RUNTIME,{pp.Route.I:I,pp.Route.II:II,pp.Route.III:III})
            self.assertEqual(len(files),7)
            for p in files: self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
            m=(Path(tmp)/"bundle"/"manifest.json").read_text(); self.assertNotIn(I.uuid,m); self.assertNotIn(III.auth,m); self.assertNotIn("192.0.2.10",m)

    def test_server_actions_are_separate(self):
        restart=pp.server_action_script(pp.Route.II,23452,"restart"); stop=pp.server_action_script(pp.Route.II,23452,"stop")
        self.assertIn("systemctl restart",restart); self.assertNotIn("systemctl stop",restart); self.assertIn("OLD_PID",restart); self.assertIn("NEW_PID",restart)
        self.assertIn("systemctl stop",stop); self.assertIn("! ss -H -ltn",stop); self.assertIn("pp-lab-i.service",stop)

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

    def test_render_check(self): self.assertEqual(pp.render_check(),0)


if __name__ == "__main__": unittest.main()
