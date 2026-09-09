import gzip
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("test_native_handoff", Path(__file__).parents[1] / "build_support/handoff.py")
HANDOFF = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HANDOFF)
SOURCE = "a" * 64
BUILD = "paintedwolf-" + "b" * 64


class NativeHandoffTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.input = self.root / "input"
        (self.input / "artifact").mkdir(parents=True)
        (self.input / "artifact/opengrep").write_bytes(b"native content")
        (self.input / "artifact/opengrep").chmod(0o755)
        self.archive = self.root / "handoff.tar.gz"

    def write(self):
        HANDOFF.write(self.input, self.archive, SOURCE, "compiled", BUILD)

    def read(self, stage="compiled", source=SOURCE):
        return HANDOFF.read(self.archive, self.root / "output", source, stage)

    def replace_archive(self, mutate):
        with tarfile.open(self.archive, "r:gz") as archive:
            entries = [(entry, archive.extractfile(entry).read() if entry.isfile() else None) for entry in archive]
        mutate(entries)
        with tarfile.open(self.archive, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            for entry, raw in entries:
                archive.addfile(entry, None if raw is None else io.BytesIO(raw))

    def test_roundtrip_preserves_hashes_modes_and_contained_links(self):
        (self.input / "artifact/link").symlink_to("opengrep")
        self.write()
        self.read()
        self.assertEqual(HANDOFF.inventory(self.input), HANDOFF.inventory(self.root / "output"))

    def test_long_paths_use_bounded_path_only_pax(self):
        (self.input / "artifact" / ("x" * 140)).write_bytes(b"data")
        self.write()
        self.read()
        self.assertEqual(HANDOFF.inventory(self.input), HANDOFF.inventory(self.root / "output"))

    def test_source_or_stage_mismatch_precedes_payload_writes(self):
        self.write()
        with self.assertRaisesRegex(ValueError, "stage or source"):
            self.read(stage="packaged")
        self.assertFalse((self.root / "output/artifact").exists())

    def test_source_mismatch_is_rejected(self):
        self.write()
        with self.assertRaisesRegex(ValueError, "stage or source"):
            self.read(source="c" * 64)

    def test_changed_member_bytes_are_rejected(self):
        self.write()
        self.replace_archive(lambda entries: entries.__setitem__(1, (entries[1][0], b"X" * len(entries[1][1]))))
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.read()

    def test_duplicate_member_is_rejected(self):
        self.write()
        self.replace_archive(lambda entries: entries.append(entries[1]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.read()

    def test_path_escape_is_rejected_before_writing(self):
        self.write()
        self.replace_archive(lambda entries: setattr(entries[1][0], "name", "../outside"))
        with self.assertRaisesRegex(ValueError, "Invalid handoff path"):
            self.read()
        self.assertFalse((self.root / "outside").exists())

    def test_hardlinks_are_rejected(self):
        self.write()
        def hardlink(entries):
            entry, _ = entries[1]
            entry.type, entry.linkname, entry.size = tarfile.LNKTYPE, "handoff.json", 0
            entries[1] = entry, None
        self.replace_archive(hardlink)
        with self.assertRaisesRegex(ValueError, "file type"):
            self.read()

    def test_symlink_escape_is_rejected(self):
        (self.input / "artifact/link").symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.write()

    def test_large_hidden_pax_metadata_is_rejected(self):
        self.write()
        self.replace_archive(lambda entries: setattr(entries[1][0], "pax_headers", {"comment": "x" * 1000000}))
        with self.assertRaisesRegex(ValueError, "oversized.*PAX"):
            self.read()

    def test_unknown_pax_metadata_is_rejected(self):
        self.write()
        self.replace_archive(lambda entries: setattr(entries[1][0], "pax_headers", {"comment": "untrusted"}))
        with self.assertRaisesRegex(ValueError, "Unsupported handoff PAX"):
            self.read()

    def test_pax_sparse_hooks_are_rejected_before_stdlib_parsing(self):
        self.write()
        self.replace_archive(lambda entries: setattr(entries[1][0], "pax_headers", {"GNU.sparse.map": "0,14"}))
        with mock.patch.object(tarfile.TarInfo, "_proc_gnusparse_01", side_effect=AssertionError("entered sparse parser")):
            with self.assertRaisesRegex(ValueError, "Sparse files"):
                self.read()

    def test_buffered_nonzero_tar_padding_is_rejected(self):
        self.write()
        raw = gzip.decompress(self.archive.read_bytes())
        self.archive.write_bytes(gzip.compress(raw[:-1] + b"X"))
        with self.assertRaisesRegex(ValueError, "Unexpected data"):
            self.read()

    def test_expanded_zero_tail_is_bounded(self):
        self.write()
        with self.archive.open("ab") as output:
            output.write(gzip.compress(b"\0" * 200000))
        with mock.patch.object(HANDOFF, "MAX_BYTES", 2048), mock.patch.object(HANDOFF, "MAX_MANIFEST", 1024), \
                mock.patch.object(HANDOFF, "MAX_FILES", 10):
            with self.assertRaisesRegex(ValueError, "Expanded handoff"):
                self.read()

    def test_duplicate_manifest_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            json.loads('{"files":{},"files":{}}', object_pairs_hook=HANDOFF.unique_object)

    def test_existing_output_is_preserved(self):
        self.archive.write_bytes(b"existing")
        with self.assertRaisesRegex(ValueError, "must be new"):
            self.write()
        self.assertEqual(self.archive.read_bytes(), b"existing")
