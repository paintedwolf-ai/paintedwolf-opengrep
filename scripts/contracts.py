#!/usr/bin/env python3
"""Run engine contracts with their pinned YAML dependency in a private environment."""
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'engine'))
from build_support import dependencies


def main():
    pins = [entry for entry in dependencies.requirements(ROOT / 'engine/locks/python.txt')
            if entry['name'] == 'ruamel.yaml']
    if len(pins) != 1:
        raise ValueError('The engine lock must pin exactly one ruamel.yaml version')
    requirement = pins[0]
    cache = ROOT / '.cache'
    cache.mkdir(exist_ok=True)
    environment = cache / ('contracts-python-' + '.'.join(map(str, sys.version_info[:2]))
                           + '-' + requirement['sha256'])
    python = environment / 'bin/python'
    with (cache / (environment.name + '.lock')).open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if not python.is_file():
            venv.EnvBuilder(with_pip=True).create(environment)
        version = subprocess.run([str(python), '-c', 'import importlib.metadata; print(importlib.metadata.version("ruamel.yaml"))'],
                                 text=True, capture_output=True)
        if version.returncode != 0 or version.stdout.strip() != requirement['version']:
            dependencies.install_contract_dependency(python, ROOT / 'engine', cache / 'contract-distributions')
    os.execv(str(python), [str(python), str(ROOT / 'engine/verify.py'), *sys.argv[1:]])


if __name__ == '__main__':
    main()
