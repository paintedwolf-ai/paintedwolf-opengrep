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
