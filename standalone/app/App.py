import logging
import os
import tempfile
from pathlib import Path

import funcy as F
import wx

from quarantine_chorus import ffmpeg
from quarantine_chorus import mlt

from . import util
from .paths import find_shotcut_executable
from .ui import background
from .ui import dialogs
from .ui.base import LogDialog
from .ui.Frame import Frame


class App(wx.App):
    def OnInit(self):
        self.log_file = tempfile.NamedTemporaryFile(encoding='utf-8', mode='w+')
        logging.basicConfig(stream=self.log_file, level=logging.DEBUG)
        logging.info("Starting application with log %s", self.log_file.name)
        if not self.SetExecutables():
            return False
        max_workers = os.cpu_count()  # * 10
        logging.info("Initializing pool with %d worker threads.", max_workers)
        self.threadpool = background.ThreadPool(self, max_workers=max_workers)
        self.frame = Frame(None)
        self.log_dialog = LogDialog(None)
        self.frame.Show()
        return True

    def OnExit(self):
        logging.info("Shutting down thread pool")
        self.threadpool.shutdown()
        return 0

    def RunInBackground(self, *args, **kwargs):
        self.threadpool.run(*args, **kwargs)

    def SetExecutables(self):
        executables = find_executables()
        if not executables:
            logging.info("Unable to find required programs; exiting")
            return False
        logging.info("Found required programs: %s", executables)
        ffmpeg.set_executables(**F.project(executables, ['ffmpeg',
                                                         'ffprobe',
                                                         'ffplay']))
        mlt.melt.set_executable(executables['melt'])
        return True

    def ShowLogs(self):
        self.log_dialog.m_text.SetValue(Path(wx.GetApp().log_file.name).read_text())
        self.log_dialog.ShowModal()


def find_executables():
    """Finds ffmpeg and melt executables, returning a dict of names to paths."""
    required_exes = ['ffmpeg', 'ffprobe', 'melt']
    all_exes = ['ffmpeg', 'ffprobe', 'ffplay', 'melt']
    shotcut_dir = None
    while True:
        executables = {
            name: find_shotcut_executable(name, name + '.exe', shotcut_dir=shotcut_dir)
            for name in all_exes
        }
        missing_exes = F.lremove(executables, required_exes)
        if not missing_exes:
            return executables

        result = wx.MessageBox(
            f"Unable to find {util.oxford_join(missing_exes)} (part of Shotcut)! "
            "Please install Shotcut, or locate Shotcut in your filesystem.",
            "Error",
            style=wx.OK | wx.CANCEL | wx.ICON_ERROR
        )
        if result == wx.CANCEL:
            return False

        result = dialogs.file_dialog(None, message="Select Shotcut",
                                     style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if not result:
            return False

        shotcut_dir = result if Path(result).is_dir() else str(Path(result).parent)
