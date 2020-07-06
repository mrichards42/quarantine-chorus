#!/usr/bin/env python3
"""Finds files for a GCP functions upload."""

import modulefinder
import re
import subprocess
from pathlib import Path


def gcloud_files():
    proc = subprocess.run(['gcloud', 'meta', 'list-files-for-upload'],
                          encoding='utf-8',
                          stdout=subprocess.PIPE)
    proc.check_returncode()
    return [Path(f) for f in proc.stdout.strip().split('\n')]


def requirements_files(root_file='requirements.txt'):
    root_file = Path(root_file)
    files = {root_file}
    for other in re.finditer(r'^\s*-r\s+(\S+)', root_file.read_text(), re.MULTILINE):
        files |= requirements_files(root_file.parent.joinpath(other.group(1)))
    return files


def python_files(entrypoint='main.py'):
    entrypoint = Path(entrypoint)
    finder = modulefinder.ModuleFinder()
    finder.run_script(str(entrypoint))
    files = {entrypoint}
    for k, m in finder.modules.items():
        if not m.__file__:
            continue
        p = Path(m.__file__)
        try:
            p = p.relative_to('.')
        except ValueError:
            continue
        files.add(p)
    return files


def find_files(entrypoint='main.py'):
    """Returns a set of files to include.

    Included files are:
    - Python files reachable from the entrypoint
    - Requirements files reachable from requirements.txt
    - Files in the same directory as a reachable python file
    - Files in a directory with no python files at all
    """
    files = set()
    # Start with files that `gcloud` thinks it needs
    all_files = gcloud_files()
    non_py_files = {f for f in all_files
                    if (not f.suffix == '.py'
                        and not str(f).endswith('requirements.txt'))}
    # 1. Reachable python files
    py_files = python_files(entrypoint)
    files |= py_files
    # 2. Reachable requirements files
    files |= requirements_files()
    # 3. Files in the same directory as a reachable python file (aside from
    # requirements files)
    py_dirs = set(f.parent for f in py_files)
    files |= {f for f in non_py_files if f.parent in py_dirs}
    # 4. Files not in a python directory at all
    non_py_dirs = set(f.parent for f in all_files) - py_dirs
    files |= {f for f in non_py_files if f.parent in non_py_dirs}
    return files


def main(entrypoint='main.py'):
    for f in find_files(entrypoint):
        print(str(f))


if __name__ == '__main__':
    # For modulefinder, make sure the cwd is in our path
    import sys
    sys.path.insert(0, '')
    main(*sys.argv[1:])
