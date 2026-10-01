import hashlib
import types
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

RUNTIME_PATH = Path(__file__).parents[1] / "build_support/runtime.py"
RUNTIME = types.ModuleType("opengrep_runtime")
exec(compile(RUNTIME_PATH.read_bytes(), str(RUNTIME_PATH), "exec"), RUNTIME.__dict__)



class RuntimeArchiveTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.archive = Path(self.temporary.name) / "runtime.archive"
        self.spec = {"url": "https://example.invalid/runtime", "sha256": hashlib.sha256(b"verified").hexdigest()}

    def test_verified_cached_archive_needs_no_network(self):
        self.archive.write_bytes(b"verified")
        with patch.object(RUNTIME, "run") as runner:
            RUNTIME.download(self.spec, self.archive)
            runner.assert_not_called()

    def test_modified_cache_is_rejected_before_use(self):
        self.archive.write_bytes(b"modified")
        with patch.object(RUNTIME, "run") as runner:
            with self.assertRaisesRegex(RuntimeError, "Cached runtime archive"):
                RUNTIME.download(self.spec, self.archive)
            runner.assert_not_called()

    def test_download_digest_mismatch_does_not_publish_archive(self):
        def corrupt_download(*_):
            self.archive.with_suffix(".download").write_bytes(b"modified")
        with patch.object(RUNTIME, "run", side_effect=corrupt_download):
            with self.assertRaisesRegex(RuntimeError, "Downloaded runtime archive"):
                RUNTIME.download(self.spec, self.archive)
        self.assertFalse(self.archive.exists())


class DeploymentTargetTest(unittest.TestCase):
    def test_library_identity_is_not_a_runtime_dependency(self):
        commands = """Load command 1
          cmd LC_ID_DYLIB
         name /private/build/Python (offset 24)
Load command 2
          cmd LC_LOAD_DYLIB
         name @executable_path/libcrypto.3.dylib (offset 24)
Load command 3
          cmd LC_RPATH
         path /private/build/lib (offset 12)
"""
        self.assertEqual(RUNTIME.linked_libraries(commands),
                         (["@executable_path/libcrypto.3.dylib"], ["/private/build/lib"]))

    def test_universal_runtime_preserves_each_architecture_minimum(self):
        commands = """Load command 1
      cmd LC_VERSION_MIN_MACOSX
  cmdsize 16
  version 10.13
      sdk 15.4
Load command 2
      cmd LC_BUILD_VERSION
  cmdsize 32
 platform 1
    minos 11.0
      sdk 26.2
   ntools 1
     tool 3
  version 1220.1
"""
        # Linker tool versions are not deployment requirements.
        self.assertEqual(RUNTIME.deployment_versions(commands), [(10, 13), (11, 0)])

class PackagedMachOTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "entrypoint.dist").mkdir()
        (self.root / "opengrep").write_bytes(bytes.fromhex("cffaedfe") + b"fixture")

    def inspect(self, version="13.0", dependency="/usr/lib/libSystem.B.dylib", architecture=None):
        def output(arguments, **_):
            if arguments[0] == "lipo":
                return architecture or RUNTIME.platform.machine()
            if arguments[1] == "-l":
                return "Load command 1\n      cmd LC_BUILD_VERSION\n    minos " + version + "\n      sdk 26.2\nLoad command 2\n      cmd LC_LOAD_DYLIB\n      name " + dependency + " (offset 24)\n"
            return "opengrep:\n\t" + dependency + " (compatibility version 1.0.0, current version 1.0.0)\n"
        return patch.object(RUNTIME.subprocess, "check_output", side_effect=output)

    def test_newer_deployment_target_is_rejected(self):
        with self.inspect(version="14.0"):
            with self.assertRaisesRegex(RuntimeError, "exceeds the release baseline"):
                RUNTIME.validate_macos(self.root, "13.0")
        self.assertFalse((self.root / "platform-checks.json").exists())

    def test_host_library_dependency_is_rejected(self):
        with self.inspect(dependency="/opt/homebrew/lib/libev.dylib"):
            with self.assertRaisesRegex(RuntimeError, "build-host path"):
                RUNTIME.validate_macos(self.root, "13.0")

    def test_wrong_architecture_is_rejected(self):
        with self.inspect(architecture="unsupported-architecture"):
            with self.assertRaisesRegex(RuntimeError, "lacks the target architecture"):
                RUNTIME.validate_macos(self.root, "13.0")

    def test_system_prefix_does_not_allow_path_traversal(self):
        with self.inspect(dependency="/usr/lib/../../opt/host.dylib"):
            with self.assertRaisesRegex(RuntimeError, "build-host path"):
                RUNTIME.validate_macos(self.root, "13.0")

    def test_system_only_baseline_image_is_recorded(self):
        with self.inspect():
            RUNTIME.validate_macos(self.root, "13.0")
        self.assertTrue((self.root / "platform-checks.json").is_file())

    def test_relative_dependency_must_be_bundled(self):
        distribution = self.root / "entrypoint.dist"
        image = distribution / "module.so"
        with self.assertRaisesRegex(RuntimeError, "missing or outside"):
            RUNTIME.validate_relative_dependencies(image, distribution, ["@loader_path/missing.dylib"], [])
        (distribution / "present.dylib").write_bytes(b"library")
        RUNTIME.validate_relative_dependencies(image, distribution, ["@loader_path/present.dylib"], [])
        RUNTIME.validate_relative_dependencies(image, distribution, ["@rpath/present.dylib"], ["@executable_path"])

    def test_relative_dependency_cannot_escape_through_symlink(self):
        distribution = self.root / "entrypoint.dist"
        (self.root / "host.dylib").write_bytes(b"host library")
        (distribution / "escape.dylib").symlink_to(self.root / "host.dylib")
        with self.assertRaisesRegex(RuntimeError, "missing or outside"):
            RUNTIME.validate_relative_dependencies(distribution / "module.so", distribution,
                                                  ["@loader_path/escape.dylib"], [])

    def test_onefile_launcher_cannot_require_sibling_library(self):
        with self.assertRaisesRegex(RuntimeError, "Onefile launcher"):
            RUNTIME.validate_relative_dependencies(self.root / "opengrep", self.root / "entrypoint.dist",
                                                  ["@executable_path/Python"], [])


if __name__ == "__main__":
    unittest.main()


def elf_image(machine=62, needed=(), runpath=None, glibc=()):
    """A minimal little-endian ELF64 image with a dynamic section and version needs."""
    import struct
    strings = bytearray(b"\0")

    def intern(text):
        offset = len(strings)
        strings.extend(text.encode() + b"\0")
        return offset

    dynamic = b"".join(struct.pack("<qQ", 1, intern(name)) for name in needed)
    if runpath is not None:
        dynamic += struct.pack("<qQ", 29, intern(runpath))
    dynamic += struct.pack("<qQ", 0, 0)
    verneed = b""
    if glibc:
        file_name = intern("libc.so.6")
        aux = b""
        for index, version in enumerate(glibc):
            following = 16 if index < len(glibc) - 1 else 0
            aux += struct.pack("<IHHII", 0, 0, 0, intern("GLIBC_" + version), following)
        verneed = struct.pack("<HHIII", 1, len(glibc), file_name, 16, 0) + aux
    header_size, entry = 64, 64
    dynstr_offset = header_size
    dynamic_offset = dynstr_offset + len(strings)
    verneed_offset = dynamic_offset + len(dynamic)
    sections_offset = verneed_offset + len(verneed)
    sections = [struct.pack("<IIQQQQIIQQ", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                struct.pack("<IIQQQQIIQQ", 0, 3, 0, 0, dynstr_offset, len(strings), 0, 0, 1, 0),
                struct.pack("<IIQQQQIIQQ", 0, 6, 0, 0, dynamic_offset, len(dynamic), 1, 0, 8, 16)]
    if glibc:
        sections.append(struct.pack("<IIQQQQIIQQ", 0, 0x6FFFFFFE, 0, 0, verneed_offset, len(verneed), 1, 1, 8, 0))
    header = bytearray(64)
    header[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<H", header, 18, machine)
    struct.pack_into("<Q", header, 0x28, sections_offset)
    struct.pack_into("<HH", header, 0x3A, entry, len(sections))
    return bytes(header) + bytes(strings) + dynamic + verneed + b"".join(sections)


class LinuxImageTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, relative, **facts):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(elf_image(**facts))
        return path

    def test_reader_reports_dependencies_runpaths_and_glibc_versions(self):
        path = self.write("image.so", needed=("libssl.so.3", "libc.so.6"), runpath="$ORIGIN:$ORIGIN/lib",
                          glibc=("2.34", "2.2.5", "2.14"))
        self.assertEqual(RUNTIME.read_elf(path), {"architecture": "amd64", "dependencies": ["libssl.so.3", "libc.so.6"],
                                                  "rpaths": ["$ORIGIN", "$ORIGIN/lib"], "glibc_versions": ["2.2.5", "2.14", "2.34"]})
        self.assertTrue(RUNTIME.is_elf_image(path))
        self.assertEqual(RUNTIME.read_elf(self.write("arm.so", machine=183))["architecture"], "arm64")

    def distribution(self, root, core=None):
        dist = root / "entrypoint.dist"
        for relative, facts in (("opengrep.bin", {"needed": ("libc.so.6",), "runpath": "$ORIGIN"}),
                                ("_ssl.so", {"needed": ("libssl.so.3", "libc.so.6"), "runpath": "$ORIGIN"}),
                                ("libssl.so.3", {"needed": ("libc.so.6",), "runpath": "$ORIGIN"}),
                                ("semgrep/bin/opengrep-core", core or {"needed": ("libm.so.6", "libc.so.6"), "glibc": ("2.35",)})):
            path = dist / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(elf_image(**facts))
        return dist

    def report(self, core=None, launcher=None):
        cli = self.root / "cli"
        self.distribution(cli, core)
        extracted = self.distribution(self.root / "cache", core)
        (cli / "opengrep").write_bytes(elf_image(**(launcher or {"needed": ("libc.so.6",), "glibc": ("2.34",)})))
        with patch.object(RUNTIME.platform, "machine", return_value="x86_64"):
            return RUNTIME.validate_linux(cli, extracted, "2.35")

    def test_report_binds_launcher_and_payload(self):
        report = self.report()
        self.assertEqual((report["platform"], report["architecture"], report["glibc_max"]), ("linux", "amd64", "2.35"))
        self.assertEqual(report["outer"]["path"], "opengrep")
        self.assertEqual([image["path"] for image in report["standalone"]],
                         ["_ssl.so", "libssl.so.3", "opengrep.bin", "semgrep/bin/opengrep-core"])
        self.assertEqual(report["standalone"], report["extracted"])

    def test_images_above_the_glibc_baseline_or_with_host_paths_are_rejected(self):
        for core, message in (({"needed": ("libc.so.6",), "glibc": ("2.38",)}, "above the release baseline"),
                              ({"needed": ("libc.so.6",), "runpath": "/build/lib"}, "build-host runpath"),
                              ({"needed": ("libstdc++.so.6", "libc.so.6")}, "does not carry")):
            with self.subTest(message=message), self.assertRaisesRegex(RuntimeError, message):
                self.report(core=core)
                raise AssertionError("unreachable")
            for path in list(self.root.iterdir()):
                __import__("shutil").rmtree(path)

    def test_launcher_depends_only_on_glibc(self):
        with self.assertRaisesRegex(RuntimeError, "outside glibc"):
            self.report(launcher={"needed": ("libz.so.1", "libc.so.6")})
