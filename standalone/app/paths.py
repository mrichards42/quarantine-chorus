"""Executable searching"""

import os
import shutil
import sys
from pathlib import Path


def find_file(d, *names):
    for name in names:
        try:
            return str(next(p for p in Path(d).glob('**/' + name) if p.is_file()))
        except StopIteration:
            continue


def default_shotcut_dir():
    if sys.platform.startswith('darwin'):
        return '/Applications/Shotcut.app'
    elif sys.platform.startswith('win'):
        for v in ('programfiles', 'programfiles(x86)', 'programw6432'):
            d = os.environ.get(v)
            if d:
                p = Path(d).joinpath('Shotcut')
                if p.exists():
                    return p


def find_shotcut_executable(name, shotcut_dir=None):
    exe = None
    shotcut_dir = shotcut_dir or default_shotcut_dir()
    names = [name]
    if os.name == 'nt':
        names = [name + '.exe', name]
    if shotcut_dir:
        exe = find_file(shotcut_dir, *names)
    if exe:
        return exe
    for name in names:
        exe = shutil.which(name)
        if exe:
            return exe
