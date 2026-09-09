import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "corresponding_source", Path(__file__).parents[1] / "build_support/corresponding_source.py")
RETAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETAIN)

PACKAGE = Path(__file__).parents[1]
SOURCE = b"upstream library source\n"


class Response:
    def __init__(self, raw):
        self.raw = raw

    def read(self):
        return self.raw


def entry(**overrides):
    base = {"id": "ocaml/example-1.0", "license": "LGPL-2.1", "obligations": ["source-offer"],
            "url": "https://example.invalid/example-1.0.tar.gz", "revision": None,
            "sha256": hashlib.sha256(SOURCE).hexdigest(), "sha512": None, "note": None}
    base.update(overrides)
    return base


class CorrespondingSourceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def retain(self, entries, raw=SOURCE):
        lock = self.root / "lock.json"
        lock.write_text(json.dumps({"schema_version": 1, "artifact_version": "test",
                                    "retained": entries}))
        with patch.object(RETAIN.urllib.request, "urlopen", return_value=Response(raw)):
            return RETAIN.retain(self.root / "retained", lock)

    def test_retained_source_is_written_and_verified_against_its_sha256(self):
        manifest = self.retain([entry()])
        record = manifest["retained"][0]
        self.assertEqual(record["verified_against_pin"], "sha256")
        self.assertEqual((self.root / "retained" / record["retained"]).read_bytes(), SOURCE)
        self.assertEqual(json.loads((self.root / "retained/RETAINED-SOURCE.json").read_text()),
                         manifest)

    def test_a_pin_recording_only_sha512_still_verifies(self):
        manifest = self.retain([entry(sha256=None, sha512=hashlib.sha512(SOURCE).hexdigest())])
        self.assertEqual(manifest["retained"][0]["verified_against_pin"], "sha512")

    def test_source_that_does_not_match_its_pin_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "retained sha256"):
            self.retain([entry()], raw=b"substituted source\n")

    def test_archive_with_no_digest_to_verify_against_is_refused(self):
        with self.assertRaisesRegex(RuntimeError, "no digest to verify against"):
            self.retain([entry(sha256=None, sha512=None)])

    def test_component_without_an_upstream_archive_is_recorded_as_unretained(self):
        manifest = self.retain([entry(url=None, sha256=None, note="carried by another component")])
        self.assertEqual(manifest["retained"], [])
        self.assertEqual(manifest["unretained"],
                         [{"id": "ocaml/example-1.0", "retained": None,
                           "reason": "carried by another component"}])

    def test_shipped_lock_covers_every_component_the_inventory_says_owes_source(self):
        lock = json.loads((PACKAGE / "locks/corresponding-source.json").read_text())
        inventory = json.loads((PACKAGE / "licensing/inventory.json").read_text())
        carried = {"engine", "parsers", "grammars"}
        owed = {component["id"] for component in inventory["components"]
                if {"source-offer", "relink"} & set(component["obligations"])
                and component["group"] not in carried}
        self.assertEqual({item["id"] for item in lock["retained"]}, owed)
        self.assertTrue(all(item["sha256"] or item["sha512"] or item["revision"] or not item["url"]
                            for item in lock["retained"]),
                        "every retained archive must carry a digest to verify against")


if __name__ == "__main__":
    unittest.main()
