import importlib.util
import contextlib
import errno
import io
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
import urllib.parse
import stat

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "lilfox-family-bundle.py"
spec = importlib.util.spec_from_file_location("lilfox_family_bundle", PATH)
family = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = family
assert spec.loader is not None
spec.loader.exec_module(family)


class FamilyBundleTests(unittest.TestCase):
    @property
    def template(self):
        return (ROOT / "web/landing/lisya_bukhta_deepwork_ailab.html").read_text(encoding="utf-8")

    def assert_no_staging(self, parent):
        self.assertFalse(list(parent.glob(".lilfox-bundle-*")))

    def test_destination_is_absent_until_verified_atomic_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent, output = Path(tmp), Path(tmp) / "publish"
            real_write, real_verify, real_rename = family.pp.write_private, family._verify_bundle, family._rename_noreplace
            verified = []
            def write(path, text):
                self.assertFalse(output.exists())
                self.assertTrue(path.is_relative_to(parent))
                self.assertTrue(path.relative_to(parent).parts[0].startswith(".lilfox-bundle-"))
                return real_write(path, text)
            def verify(stage, files):
                self.assertFalse(output.exists())
                real_verify(stage, files)
                verified.append(True)
            def publish(fd, source, destination):
                self.assertEqual(verified, [True])
                self.assertFalse(output.exists())
                return real_rename(fd, source, destination)
            old_umask = os.umask(0)
            try:
                with mock.patch.object(family.pp, "write_private", side_effect=write), mock.patch.object(family, "_verify_bundle", side_effect=verify), mock.patch.object(family, "_rename_noreplace", side_effect=publish):
                    family.build_bundle(self.fixture(), self.template, output)
            finally:
                os.umask(old_umask)
            for path in [output, *output.rglob("*")]:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700 if path.is_dir() else 0o600)
            self.assert_no_staging(parent)

    def test_enospc_after_partial_file_at_every_write_cleans_only_own_stage(self):
        real_write = family.pp.write_private
        # Three recipient pairs, delivery manifest, headers and 404.
        for fail_at in range(1, 10):
            with self.subTest(write=fail_at), tempfile.TemporaryDirectory() as tmp:
                parent, output = Path(tmp), Path(tmp) / "publish"
                foreign = parent / ".lilfox-bundle-other-run"
                foreign.mkdir(mode=0o700)
                sentinel = foreign / "keep"; sentinel.write_bytes(b"another run")
                inode = sentinel.stat().st_ino
                calls = []
                def write(path, text):
                    calls.append(path)
                    self.assertFalse(output.exists())
                    if len(calls) == fail_at:
                        real_write(path, text[:7])
                        raise OSError(errno.ENOSPC, "synthetic disk full")
                    return real_write(path, text)
                with mock.patch.object(family.pp, "write_private", side_effect=write):
                    with self.assertRaises(OSError) as error:
                        family.build_bundle(self.fixture(), self.template, output)
                self.assertEqual(error.exception.errno, errno.ENOSPC)
                self.assertFalse(output.exists())
                self.assertEqual(set(parent.iterdir()), {foreign})
                self.assertEqual((sentinel.stat().st_ino, sentinel.read_bytes()), (inode, b"another run"))
                # Retry needs no deletion/repair of a partially published tree.
                family.build_bundle(self.fixture(), self.template, output)
                self.assertEqual(len(list((output / "public/sub").iterdir())), 3)

    def test_enospc_creating_staging_publishes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "publish"
            with mock.patch.object(family.tempfile, "mkdtemp", side_effect=OSError(errno.ENOSPC, "synthetic disk full")):
                with self.assertRaises(OSError):
                    family.build_bundle(self.fixture(), self.template, output)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_file_fsync_failure_cleans_partial_temporary_file(self):
        real_sync = os.fsync
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "publish"
            def sync(fd):
                if stat.S_ISREG(os.fstat(fd).st_mode):
                    raise OSError(errno.ENOSPC, "synthetic flush failure")
                return real_sync(fd)
            with mock.patch.object(family.os, "fsync", side_effect=sync):
                with self.assertRaises(OSError):
                    family.build_bundle(self.fixture(), self.template, output)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_precommit_directory_sync_and_publish_errors_leave_no_output(self):
        faults = [("_sync_dir", errno.EIO), ("_rename_noreplace", errno.ENOSPC),
                  ("_rename_noreplace", errno.EACCES), ("_rename_noreplace", errno.EXDEV),
                  ("_rename_noreplace", errno.EOPNOTSUPP)]
        for helper, code in faults:
            with self.subTest(helper=helper, code=code), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "publish"
                with mock.patch.object(family, helper, side_effect=OSError(code, "synthetic failure")):
                    with self.assertRaises(OSError) as error:
                        family.build_bundle(self.fixture(), self.template, output)
                self.assertEqual(error.exception.errno, code)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_postcommit_sync_failure_preserves_complete_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent, output = Path(tmp), Path(tmp) / "publish"
            real_sync = os.fsync
            def sync(fd):
                if output.exists():
                    raise OSError(errno.EIO, "synthetic post-commit failure")
                return real_sync(fd)
            with mock.patch.object(family.os, "fsync", side_effect=sync):
                with self.assertRaises(OSError):
                    family.build_bundle(self.fixture(), self.template, output)
            self.assertEqual(len(list(output.rglob("*"))), 12)
            self.assert_no_staging(parent)
            before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
                family.build_bundle(self.fixture(), self.template, output)
            self.assertEqual(before, {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()})

    def test_rejects_existing_paths_without_chmod_or_delete(self):
        for kind in ("empty", "nonempty", "file", "symlink", "dangling"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                parent, output = Path(tmp), Path(tmp) / "publish"
                target = parent / "target"; target.mkdir(); (target / "keep").write_bytes(b"keep")
                if kind in ("empty", "nonempty"):
                    output.mkdir(mode=0o755)
                    if kind == "nonempty": (output / "keep").write_bytes(b"keep")
                elif kind == "file": output.write_bytes(b"keep")
                else: output.symlink_to(target if kind == "symlink" else parent / "absent", target_is_directory=True)
                before = output.lstat()
                with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
                    family.build_bundle(self.fixture(), self.template, output)
                after = output.lstat()
                self.assertEqual((before.st_ino, before.st_mode), (after.st_ino, after.st_mode))
                self.assertEqual((target / "keep").read_bytes(), b"keep")
                if kind == "file": self.assertEqual(output.read_bytes(), b"keep")
                if kind == "nonempty": self.assertEqual((output / "keep").read_bytes(), b"keep")
                self.assert_no_staging(parent)

    def test_destination_race_uses_real_noreplace_and_preserves_winner(self):
        for kind in ("empty", "nonempty", "file", "symlink", "dangling"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                parent, output = Path(tmp), Path(tmp) / "publish"
                target = parent / "target"; target.mkdir(); (target / "keep").write_bytes(b"keep")
                real_rename = family._rename_noreplace
                winner = []
                def publish(fd, source, destination):
                    if kind in ("empty", "nonempty"):
                        output.mkdir(mode=0o755)
                        if kind == "nonempty": (output / "keep").write_bytes(b"keep")
                    elif kind == "file": output.write_bytes(b"keep")
                    else: output.symlink_to(target if kind == "symlink" else parent / "absent", target_is_directory=True)
                    winner.append(output.lstat())
                    return real_rename(fd, source, destination)
                with mock.patch.object(family, "_rename_noreplace", side_effect=publish):
                    with self.assertRaises(OSError) as error:
                        family.build_bundle(self.fixture(), self.template, output)
                self.assertEqual(error.exception.errno, errno.EEXIST)
                self.assertEqual((winner[0].st_ino, winner[0].st_mode), (output.lstat().st_ino, output.lstat().st_mode))
                self.assertEqual((target / "keep").read_bytes(), b"keep")
                if kind == "file": self.assertEqual(output.read_bytes(), b"keep")
                if kind == "nonempty": self.assertEqual((output / "keep").read_bytes(), b"keep")
                self.assert_no_staging(parent)

    def test_two_concurrent_builds_publish_exactly_one_complete_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "publish"
            barrier = threading.Barrier(2, timeout=10)
            real_rename, results = family._rename_noreplace, []
            def publish(*args):
                barrier.wait()
                return real_rename(*args)
            def build(label):
                raw = self.fixture(1); raw["recipients"][0]["name"] = label
                try:
                    family.build_bundle(raw, self.template, output)
                    results.append((label, "ok"))
                except OSError as error:
                    results.append((label, error.errno))
            with mock.patch.object(family, "_rename_noreplace", side_effect=publish):
                workers = [threading.Thread(target=build, args=(label,)) for label in ("Alpha", "Beta")]
                for worker in workers: worker.start()
                for worker in workers: worker.join(timeout=15)
            self.assertTrue(all(not worker.is_alive() for worker in workers))
            self.assertEqual(sorted(result for _, result in results if result != "ok"), [errno.EEXIST])
            winners = [label for label, result in results if result == "ok"]
            self.assertEqual(len(winners), 1)
            page = next((output / "public/page").iterdir()).read_text()
            self.assertIn(f'<div class="brand">{winners[0]}</div>', page)
            self.assertTrue((output / "private-delivery.txt").read_text().startswith(winners[0]))
            self.assert_no_staging(Path(tmp))

    def test_validation_rejects_corruption_missing_extra_links_and_permissions(self):
        for corruption in ("bytes", "missing", "extra", "symlink", "hardlink", "file_mode", "dir_mode"):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as tmp:
                parent, output = Path(tmp), Path(tmp) / "publish"
                sentinel = parent / "keep"; sentinel.write_bytes(b"foreign")
                real_verify = family._verify_bundle
                def verify(stage, files):
                    path = stage / "private-delivery.txt"
                    if corruption == "bytes": path.write_bytes(b"damaged")
                    elif corruption == "missing": path.unlink()
                    elif corruption == "extra": (stage / "unexpected").write_bytes(b"extra")
                    elif corruption == "symlink": path.unlink(); path.symlink_to(sentinel)
                    elif corruption == "hardlink": path.unlink(); os.link(sentinel, path)
                    elif corruption == "file_mode": path.chmod(0o644)
                    elif corruption == "dir_mode": (stage / "public/sub").chmod(0o755)
                    return real_verify(stage, files)
                with mock.patch.object(family, "_verify_bundle", side_effect=verify):
                    with self.assertRaisesRegex(ValueError, "STAGING_INVALID"):
                        family.build_bundle(self.fixture(), self.template, output)
                self.assertEqual(sentinel.read_bytes(), b"foreign")
                self.assertEqual(set(parent.iterdir()), {sentinel})

    def test_cleanup_does_not_delete_replacement_directory_or_follow_link(self):
        for replacement in ("directory", "symlink"):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as tmp:
                parent, output = Path(tmp), Path(tmp) / "publish"
                target = parent / "target"; target.mkdir(); (target / "keep").write_bytes(b"keep")
                replaced = []
                def write(path, text):
                    stage = parent / path.relative_to(parent).parts[0]
                    stage.rename(parent / "moved-own-stage")
                    if replacement == "directory":
                        stage.mkdir(); (stage / "keep").write_bytes(b"keep")
                    else: stage.symlink_to(target, target_is_directory=True)
                    replaced.append(stage)
                    raise OSError(errno.ENOSPC, "synthetic failure after replacement")
                with mock.patch.object(family.pp, "write_private", side_effect=write):
                    with self.assertRaises(OSError):
                        family.build_bundle(self.fixture(), self.template, output)
                self.assertFalse(output.exists())
                self.assertEqual((target / "keep").read_bytes(), b"keep")
                self.assertEqual((replaced[0] / "keep").read_bytes(), b"keep")
                self.assertEqual(replaced[0].is_symlink(), replacement == "symlink")

    def test_missing_or_writable_parent_is_not_created_or_chmodded(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "missing"
            with self.assertRaises(OSError):
                family.build_bundle(self.fixture(), self.template, parent / "publish")
            self.assertFalse(parent.exists())
            parent.mkdir(mode=0o777); parent.chmod(0o777)
            with self.assertRaisesRegex(ValueError, "PARENT_UNSAFE"):
                family.build_bundle(self.fixture(), self.template, parent / "publish")
            self.assertEqual(stat.S_IMODE(parent.stat().st_mode), 0o777)
            self.assertEqual(list(parent.iterdir()), [])

    def test_cleanup_failure_keeps_staging_private_without_touching_foreign_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent, output = Path(tmp), Path(tmp) / "publish"
            foreign = parent / "keep"; foreign.write_bytes(b"foreign")
            def fail_validation(stage, files):
                raise ValueError("FAMILY_STAGING_INVALID")
            with mock.patch.object(family, "_verify_bundle", side_effect=fail_validation), mock.patch.object(family.shutil, "rmtree", side_effect=PermissionError(errno.EACCES, "synthetic cleanup failure")):
                # Retain the safety attribute normally attached to shutil.rmtree.
                family.shutil.rmtree.avoids_symlink_attacks = True
                with self.assertRaises(PermissionError):
                    family.build_bundle(self.fixture(), self.template, output)
            self.assertFalse(output.exists())
            self.assertEqual(foreign.read_bytes(), b"foreign")
            stages = list(parent.glob(".lilfox-bundle-*"))
            self.assertEqual(len(stages), 1)
            for path in [stages[0], *stages[0].rglob("*")]:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700 if path.is_dir() else 0o600)

    def test_no_unsafe_fallback_when_atomic_rename_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent, output = Path(tmp), Path(tmp) / "publish"
            with mock.patch.object(family.ctypes, "CDLL", return_value=object()):
                with self.assertRaisesRegex(OSError, "ATOMIC_RENAME_UNAVAILABLE"):
                    family.build_bundle(self.fixture(), self.template, output)
            self.assertEqual(list(parent.iterdir()), [])
            with mock.patch.object(family.sys, "platform", "unsupported"):
                with self.assertRaisesRegex(OSError, "ATOMIC_PLATFORM_UNSUPPORTED"):
                    family.build_bundle(self.fixture(), self.template, output)
            self.assertEqual(list(parent.iterdir()), [])

    def test_cli_failure_does_not_print_exception_or_private_material(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            source = parent / "material.json"; source.write_text(json.dumps(self.fixture())); source.chmod(0o600)
            args = [str(PATH), "--material-json", str(source), "--template", str(ROOT / "web/landing/lisya_bukhta_deepwork_ailab.html"), "--output", str(parent / "publish")]
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(sys, "argv", args), mock.patch.object(family.pp, "write_private", side_effect=OSError(errno.ENOSPC, "SYNTHETIC_PRIVATE_MARKER")), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(family.main(), 2)
            self.assertEqual(out.getvalue(), "FAMILY_BUNDLE=STOP\n")
            self.assertEqual(err.getvalue(), "")
            self.assert_no_staging(parent)
            self.assertFalse((parent / "publish").exists())

    def test_sigkill_leaves_only_private_staging_and_retry_ignores_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent, output = Path(tmp), Path(tmp) / "publish"
            code = '''
import importlib.util,json,signal,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("family_kill",sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
real=m.pp.write_private
def pause(path,text):
    real(path,text)
    print("PAUSED",flush=True)
    signal.pause()
m.pp.write_private=pause
m.build_bundle(json.load(sys.stdin),Path(sys.argv[2]).read_text(),Path(sys.argv[3]))
'''
            process = subprocess.Popen([sys.executable, "-B", "-c", code, str(PATH), str(ROOT / "web/landing/lisya_bukhta_deepwork_ailab.html"), str(output)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                process.stdin.write(json.dumps(self.fixture())); process.stdin.close()
                self.assertTrue(select.select([process.stdout], [], [], 10)[0])
                self.assertEqual(process.stdout.readline().strip(), "PAUSED")
            finally:
                process.kill(); process.wait(timeout=10)
                process.stdout.close(); process.stderr.close()
            self.assertFalse(output.exists())
            stages = list(parent.glob(".lilfox-bundle-*"))
            self.assertEqual(len(stages), 1)
            orphan = stages[0]
            for path in [orphan, *orphan.rglob("*")]:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700 if path.is_dir() else 0o600)
            family.build_bundle(self.fixture(), self.template, output)
            self.assertTrue(orphan.is_dir())
            self.assertTrue(output.is_dir())

    def test_direct_https_delivery_port_is_separate_from_vpn_ports(self):
        self.assertEqual(family._public_base("https://family.example:9443/"), "https://family.example:9443")
        for value in ("https://family.example:8443", "http://family.example:9443", "https://family.example:9443/private"):
            with self.assertRaisesRegex(ValueError, "PUBLIC_BASE_INVALID"):
                family._public_base(value)

    def fixture(self, count=3):
        recipients = []
        for index in range(1, count + 1):
            name, slug = f"Получатель {index}", f"person{index}"
            recipients.append({
                "name": name, "slug": slug,
                "page_token": f"{index:064x}",
                "subscription_token": f"{index + count:064x}",
                "routes": {
                    "I": {"route": "I", "uuid": f"123e4567-e89b-12d3-a456-{index:012d}", "public_key": "A"*43, "short_id": f"{index:016x}"},
                    "II": {"route": "II", "uuid": f"123e4567-e89b-12d3-a456-{index + count:012d}", "public_key": "B"*43, "short_id": f"{index+count:016x}", "xhttp_path": "/0123456789abcdef"},
                    "III": {"route": "III", "auth": f"{slug}:" + f"{index:064x}", "pin_sha256": "b"*64},
                },
            })
        return {"public_base": "https://family.example", "host": "192.0.2.10", "cover_hostname": "cover.example", "ports": {"route_i_tcp": 443, "route_ii_tcp": 8443, "route_iii_udp": 443}, "recipients": recipients}

    def test_three_private_personal_pages_and_exact_route_labels(self):
        template = (ROOT / "web" / "landing" / "lisya_bukhta_deepwork_ailab.html").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "publish"
            family.build_bundle(self.fixture(), template, output)
            self.assertEqual(len(list((output / "public" / "page").iterdir())), 3)
            self.assertEqual(len(list((output / "public" / "sub").iterdir())), 3)
            self.assertFalse((output / "public" / "private-delivery.txt").exists())
            headers = (output / "public" / "_headers").read_text(encoding="utf-8")
            self.assertIn("profile-title: DeepWork AILab", headers)
            self.assertIn("Referrer-Policy: no-referrer", headers)
            self.assertTrue((output / "public" / "404.html").exists())
            rows = (output / "private-delivery.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows), 3)
            for index, recipient in enumerate(self.fixture()["recipients"], 1):
                name = recipient["name"]
                page = (output / "public" / "page" / (f"{index:064x}" + ".html")).read_text(encoding="utf-8")
                subscription = (output / "public" / "sub" / (f"{index + 3:064x}" + ".txt")).read_text(encoding="utf-8")
                self.assertIn(f'<div class="brand">{name}</div>', page)
                self.assertIn('content="https://family.example/sub/', page)
                self.assertIn('content="https://family.example/sub/' + f"{index + 3:064x}" + '.txt"', page)
                self.assertIn("!SUBSCRIPTION_URL.includes('__SUBSCRIPTION_URL__')", page)
                self.assertEqual(len(subscription.splitlines()), 3)
                for route in "I II III".split():
                    self.assertIn(f"%F0%9F%87%AF%F0%9F%87%B2%20%D0%94%D0%BE%D0%B1%D1%80%D0%BE%D0%B5%20%F0%9F%8C%9E%20%D0%A3%D1%82%D1%80%D0%BE%20{route}", subscription)

    def test_rejects_duplicate_recipient_credential(self):
        fixture = self.fixture()
        fixture["recipients"][1]["routes"]["I"]["uuid"] = fixture["recipients"][0]["routes"]["I"]["uuid"]
        template = (ROOT / "web" / "landing" / "lisya_bukhta_deepwork_ailab.html").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "CREDENTIAL_DUPLICATE"):
                family.build_bundle(fixture, template, Path(tmp) / "publish")

    def test_rejects_same_page_and_subscription_token(self):
        fixture = self.fixture()
        fixture["recipients"][0]["subscription_token"] = fixture["recipients"][0]["page_token"]
        template = (ROOT / "web" / "landing" / "lisya_bukhta_deepwork_ailab.html").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "TOKEN_INVALID"):
                family.build_bundle(fixture, template, Path(tmp) / "publish")

    def test_rejects_duplicate_hysteria_credential(self):
        fixture = self.fixture()
        fixture["recipients"][1]["routes"]["III"]["auth"] = fixture["recipients"][0]["routes"]["III"]["auth"]
        template = (ROOT / "web" / "landing" / "lisya_bukhta_deepwork_ailab.html").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "CREDENTIAL_DUPLICATE"):
                family.build_bundle(fixture, template, Path(tmp) / "publish")

    def test_rejects_duplicate_short_id(self):
        fixture = self.fixture()
        fixture["recipients"][1]["routes"]["II"]["short_id"] = fixture["recipients"][0]["routes"]["I"]["short_id"]
        template = (ROOT / "web" / "landing" / "lisya_bukhta_deepwork_ailab.html").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "SHORT_ID_DUPLICATE"):
                family.build_bundle(fixture, template, Path(tmp) / "publish")

    def test_rejects_stale_publish_tree(self):
        template = (ROOT / "web" / "landing" / "lisya_bukhta_deepwork_ailab.html").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "publish"
            family.build_bundle(self.fixture(), template, output)
            with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
                family.build_bundle(self.fixture(), template, output)

    def test_rejects_equivalent_credentials_and_output_inside_other_git_worktree(self):
        template = (ROOT / "web/landing/lisya_bukhta_deepwork_ailab.html").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            raw = self.fixture()
            raw["recipients"][1]["routes"]["I"]["uuid"] = raw["recipients"][0]["routes"]["I"]["uuid"].replace("-", "").upper()
            with self.assertRaisesRegex(ValueError, "CREDENTIAL_DUPLICATE"):
                family.build_bundle(raw, template, Path(tmp) / "publish")
            raw = self.fixture()
            raw["recipients"][0]["routes"]["I"]["short_id"] = "aabbccddeeff0011"
            raw["recipients"][1]["routes"]["I"]["short_id"] = "AABBCCDDEEFF0011"
            with self.assertRaisesRegex(ValueError, "SHORT_ID_DUPLICATE"):
                family.build_bundle(raw, template, Path(tmp) / "publish")
            other = Path(tmp) / "other-worktree"; other.mkdir(); (other / ".git").write_text("synthetic gitdir marker")
            with self.assertRaisesRegex(ValueError, "PRIVATE_PATH_IN_GIT"):
                family.build_bundle(self.fixture(), template, other / "publish")

    def test_arbitrary_counts_and_explicit_ports_are_used_in_each_profile(self):
        template = (ROOT / "web/landing/lisya_bukhta_deepwork_ailab.html").read_text(encoding="utf-8")
        for count in (1, 6, 11):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as tmp:
                raw = self.fixture(count)
                raw["ports"] = {"route_i_tcp": 23451, "route_ii_tcp": 23452, "route_iii_udp": 23451}
                out = Path(tmp) / "publish"
                family.build_bundle(raw, template, out)
                pages = list((out / "public/page").iterdir())
                subs = list((out / "public/sub").iterdir())
                self.assertEqual((len(pages), len(subs)), (count, count))
                for sub in subs:
                    profiles = sub.read_text().splitlines()
                    self.assertEqual(len(profiles), 3)
                    self.assertEqual([urllib.parse.urlsplit(x).port for x in profiles], [23451, 23452, 23451])
                    self.assertEqual(stat.S_IMODE(sub.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o700)
                for page in pages:
                    self.assertIn("!SUBSCRIPTION_URL.includes('__SUBSCRIPTION_URL__')", page.read_text())

    def test_invalid_recipient_lists_and_ports_write_nothing(self):
        import copy
        template = (ROOT / "web/landing/lisya_bukhta_deepwork_ailab.html").read_text(encoding="utf-8")
        mutations = [
            lambda d: d.update(recipients=[]),
            lambda d: d["recipients"][1].update(name=d["recipients"][0]["name"]),
            lambda d: d["recipients"][1].update(slug=d["recipients"][0]["slug"]),
            lambda d: d["recipients"][0].update(slug="../escape"),
            lambda d: d["recipients"][0].update(name="name\nnewline"),
            lambda d: d["ports"].update(route_ii_tcp=443),
            lambda d: d["ports"].update(route_i_tcp=True),
            lambda d: d["ports"].update(route_iii_udp=65536),
            lambda d: d.pop("ports"),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                raw = copy.deepcopy(self.fixture())
                mutation(raw)
                out = Path(tmp) / "publish"
                with self.assertRaises((ValueError, KeyError)):
                    family.build_bundle(raw, template, out)
                self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
