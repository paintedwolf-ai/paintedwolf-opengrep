#!/usr/bin/env python3
"""Run engine contracts with their pinned YAML dependency in a private environment."""
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent.parent


def main():
    requirements = [line.strip() for line in (ROOT / 'engine/locks/python.txt').read_text().splitlines()
                    if line.startswith('ruamel.yaml==')]
    if len(requirements) != 1:
        raise ValueError('The engine lock must pin exactly one ruamel.yaml version')
    requirement = requirements[0]
    cache = ROOT / '.cache'
    cache.mkdir(exist_ok=True)
    environment = cache / ('contracts-python-' + '.'.join(map(str, sys.version_info[:2])))
    python = environment / 'bin/python'
    with (cache / (environment.name + '.lock')).open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if not python.is_file():
            venv.EnvBuilder(with_pip=True).create(environment)
        version = subprocess.run([str(python), '-c', 'import importlib.metadata; print(importlib.metadata.version("ruamel.yaml"))'],
                                 text=True, capture_output=True)
        if version.returncode != 0 or version.stdout.strip() != requirement.split('==')[1]:
            subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check', requirement], check=True)
    os.execv(str(python), [str(python), str(ROOT / 'engine/verify.py'), *sys.argv[1:]])


if __name__ == '__main__':
    main()
