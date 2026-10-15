import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
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
            with self.assertRaisesRegex(ValueError, "OUTPUT_NOT_EMPTY"):
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
