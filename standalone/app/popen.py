"""Monkey-patch subprocess.Popen for windows

See: https://github.com/pyinstaller/pyinstaller/wiki/Recipe-subprocess
"""

import subprocess


_Popen = subprocess.Popen


class PopenWindows(_Popen):
    def __init__(self, cmd, *args, **kwargs):
        # Disconnect all streams
        if kwargs.get('stdin') is None:
            kwargs['stdin'] = subprocess.DEVNULL
        if kwargs.get('stdout') is None:
            kwargs['stdout'] = subprocess.DEVNULL
        if kwargs.get('stderr') is None:
            kwargs['stderr'] = subprocess.DEVNULL
        if kwargs.get('close_fds') is None:
            kwargs['close_fds'] = True
        # Set windows-specific flags to hide any console
        if 'startupinfo' not in kwargs and False:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs['startupinfo'] = si
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        super().__init__(cmd, *args, **kwargs)


if hasattr(subprocess, 'STARTUPINFO'):
    subprocess.Popen = PopenWindows
