"""Logging helper classes."""

import logging

import wx.lib.newevent


class StreamToLogger:
    """Fake file-like stream object that redirects writes to a logger instance.

    See: https://stackoverflow.com/a/36296215
    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        temp_linebuf = self.linebuf + buf
        self.linebuf = ''
        for line in temp_linebuf.splitlines(True):
            if line[-1] == '\n':
                self.logger.log(self.log_level, line.rstrip())
            else:
                self.linebuf += line

    def flush(self):
        if self.linebuf != '':
            self.logger.log(self.log_level, self.linebuf.rstrip())
        self.linebuf = ''

    def close(self):
        pass


(LogEvent, EVT_LOG) = wx.lib.newevent.NewEvent()


class LogEventHandler(logging.Handler):
    """A log handler that sends wxWidgets events."""
    def __init__(self, target=None):
        self.target = target
        super().__init__()

    def set_event_target(self, target):
        self.target = target

    def createLock(self):
        self.lock = None

    def handle(self, record):
        self.emit(record)

    def emit(self, record):
        if self.target:
            wx.PostEvent(self.target, LogEvent(message=self.format(record)))
