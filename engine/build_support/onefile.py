"""Package a signed distribution with the pinned launcher."""
import importlib.metadata
import os
from pathlib import Path
import subprocess
import sys


def package(distribution, output, scratch, build_id, deployment_target):
    import nuitka
    from nuitka.tools.onefile_compressor.OnefileCompressor import attachOnefilePayload

    if sys.platform != "darwin" or importlib.metadata.version("Nuitka") != "2.8.9":
        raise RuntimeError("Onefile packaging requires macOS and the locked Nuitka 2.8.9")
    scratch.mkdir()
    nuitka_root = Path(nuitka.__file__).resolve().parent
    source = nuitka_root / "build"
    attachOnefilePayload(
        dist_dir=str(distribution), onefile_output_filename=str(scratch / "__payload.bin"),
        start_binary=str(distribution / "opengrep.bin"), expect_compression=True,
        as_archive=False, use_compression_cache=False, file_checksums=True,
        win_path_sep=False, low_memory=False)
    definitions = {
        "_NUITKA_ONEFILE_TEMP_SPEC": "{CACHE_DIR}/opengrep/" + build_id,
        "_NUITKA_ONEFILE_COMPRESSION_BOOL": "1",
        "_NUITKA_ONEFILE_ARCHIVE_BOOL": "0",
        "_NUITKA_ONEFILE_CHILD_GRACE_TIME_INT": "5000",
    }
    env = dict(os.environ, **definitions, NUITKA_PACKAGE_DIR=str(nuitka_root),
               _NUITKA_BUILD_DEFINITIONS_CATALOG=",".join(definitions), NUITKA_PYTHON_EXE_PATH=sys.executable,
               MACOSX_DEPLOYMENT_TARGET=deployment_target)
    options = {
        "source_dir": str(scratch), "nuitka_src": str(source), "result_exe": str(output),
        "python_prefix": sys.base_prefix, "python_version": ".".join(map(str, sys.version_info[:3])),
        "target_arch": "arm64", "macos_target_arch": "arm64", "macos_min_version": deployment_target,
        "clang_mode": "true", "disable_ccache": "true", "progress_bar": "none",
        "lto_mode": "no", "deployment": "false", "gil_mode": "true", "onefile_mode": "true",
        "standalone_mode": "true", "exe_mode": "true", "noelf_mode": "true",
    }
    command = [sys.executable, str(source / "inline_copy/bin/scons.py"), "--quiet", "--jobs=2",
               "--file=" + str(source / "Onefile.scons")]
    subprocess.run(command + [key + "=" + value for key, value in options.items()], env=env, check=True)
    subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", str(output)], check=True)
