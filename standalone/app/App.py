import logging
import os
import sys
import tempfile
from pathlib import Path

import funcy as F
import wx

from quarantine_chorus import ffmpeg
from quarantine_chorus import mlt

from . import util
from .logging import StreamToLogger, LogEventHandler, EVT_LOG
from .paths import find_shotcut_executable
from .ui import background
from .ui import dialogs
from .ui.base import LogDialog
from .ui.Frame import Frame


LOG_FORMAT = "%(asctime)s [%(threadName)s][%(pathname)s:%(funcName)s:%(lineno)d] %(levelname)s: %(message)s"


class App(wx.App):
    def OnInit(self):
        # Setup logging
        self.log_dir = tempfile.TemporaryDirectory()
        self.log_file = str(Path(self.log_dir.name).joinpath('application_log.txt'))
        self.log_file_handler = logging.FileHandler(self.log_file, 'a')
        self.log_event_handler = LogEventHandler()
        logging.basicConfig(level=logging.DEBUG,
                            handlers=[self.log_file_handler,
                                      self.log_event_handler],
                            format=LOG_FORMAT)
        logging.info("Starting application with log %s", self.log_file)
        if getattr(sys, 'frozen', False):
            sys.stdout = StreamToLogger(logging.getLogger('STDOUT'))
            sys.stderr = StreamToLogger(logging.getLogger('STDERR'))
            print("Script is frozen: redirecting stdout and stderr to logs")
        else:
            print("Script is not frozen: not redirecting stdout or stderr")
        # Find ffmpeg, etc
        if not self.SetExecutables():
            return False
        # Setup threadpool
        max_workers = os.cpu_count()
        logging.info("Initializing pool with %d worker threads.", max_workers)
        self.threadpool = background.ThreadPool(self, max_workers=max_workers)
        # Setup UI
        self.frame = Frame(None)
        self.SetTopWindow(self.frame)
        self.log_dialog = LogDialog(self.frame)
        self.frame.Show()
        self.log_dialog.Bind(EVT_LOG, self.OnLog)
        self.log_dialog.Bind(wx.EVT_CLOSE, self.OnLogClosed)
        return True

    def OnExit(self):
        logging.info("Shutting down thread pool")
        self.threadpool.shutdown()
        logging.shutdown()
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
        # Get the log text
        self.log_file_handler.flush()
        # Send it to the textctrl
        text = self.log_dialog.m_text
        text.SetValue(Path(self.log_file).read_text())
        text.ShowPosition(text.GetLastPosition())
        text.SetInsertionPoint(-1)
        # Subscribe to log updates
        self.log_event_handler.set_event_target(self.log_dialog)
        # Show the log window
        self.log_dialog.Show()

    def OnLogClosed(self, evt):
        self.log_event_handler.set_event_target(None)
        evt.Skip()

    def OnLog(self, evt):
        self.log_dialog.m_text.AppendText(evt.message + '\n')
        self.log_dialog.m_text.SetInsertionPoint(-1)


def find_executables():
    """Finds ffmpeg and melt executables, returning a dict of names to paths."""
    required_exes = ['ffmpeg', 'ffprobe', 'melt']
    all_exes = ['ffmpeg', 'ffprobe', 'ffplay', 'melt']
    shotcut_dir = None
    while True:
        executables = {
            name: find_shotcut_executable(name, shotcut_dir=shotcut_dir)
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
