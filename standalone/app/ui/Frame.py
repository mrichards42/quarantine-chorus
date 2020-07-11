"""Main app Frame"""

import wx

from quarantine_chorus import mlt

from app import mix
from app.model.tracklist import TrackList

from . import base
from . import dialogs
from .TrackList import TrackListPanel
from .Layout import LayoutPanel


class Frame(base.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = LayoutPanel(self)
        self.tracklist = TrackListPanel(self)
        self.m_sizer.Insert(0, self.layout, 1, wx.EXPAND | wx.ALL, 5)
        self.m_sizer.Insert(1, self.tracklist, 1, wx.EXPAND | wx.ALL, 5)

    def OnFileOpen(self, evt):
        files = dialogs.file_dialog(
            self, message="Choose a file",
            wildcard="*.*",
            style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST)
        if files:
            TrackList.add(*files)

    def OnExportShotcut(self, evt):
        file = dialogs.file_dialog(self, message="Save a file",
                                   wildcard="Shotcut Files (*.mlt)|.mlt",
                                   style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if file:
            tracks = TrackList.as_mlt_tracks()
            # Folks usually include an image for the background, so add a blank track
            # to make that possible
            tracks.append({'blank_track': True})
            # Shotcut puts the first track at the bottom, so reverse the order
            tracks.reverse()
            with open(file, 'w') as f:
                f.write(mlt.xml.write_file(tracks, **TrackList.background_size()))

    def OnPreviewAudio(self, evt):
        wx.GetApp().RunInBackground(mix.preview_thread,
                                    TrackList.all_tracks(),
                                    **TrackList.background_size(),
                                    audio_only=True)

    def OnPreviewVideo(self, evt):
        h = TrackList.background_size()['height']
        max_height = 480
        scale = min(1, max_height / (h or max_height))
        wx.GetApp().RunInBackground(mix.preview_thread,
                                    TrackList.all_tracks(),
                                    **TrackList.background_size(),
                                    scale=scale)

    def OnViewLogs(self, evt):
        wx.GetApp().ShowLogs()
