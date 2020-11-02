"""LayoutPanel"""

import re

from app.model.tracklist import TrackList

from . import base

class LayoutPanel(base.LayoutPanel):
    def __init__(self, parent):
        super().__init__(parent)
        TrackList.subscribe(self, self._updateLayout, video=True)
        self.video_width = 1280
        self.video_height = 720
        self._updateVideoSize()

    def _updateLayout(self, tracks, force=False):
        old_tracks = set(self.m_layoutPreview.GetTrackNames())
        needs_layout = set(old_tracks) != set(t['path'] for t in tracks)
        # Update the layout preview
        self.m_layoutPreview.SetTracks(tracks)
        self.m_layoutPreview.SetBackgroundSize(**TrackList.background_size())
        # New tracks means run the layout again
        if tracks and (needs_layout or force):
            layout = TrackList.as_layout(self.video_width / self.video_height,
                                         self.video_height)
            TrackList.update_from_layout(layout, self.video_width, self.video_height)

    # -- Events --

    def _updateVideoSize(self):
        m = re.match(r'(\d+)\s*x\s*(\d+)', self.m_videoSize.GetValue().strip(), re.I)
        if m:
            self.video_width = int(m.group(1))
            self.video_height = int(m.group(2))
            self._updateLayout(TrackList.value(video=True), force=True)
        else:
            self.m_videoSize.SetValue(f"{self.video_width}x{self.video_height}")

    def OnVideoSizeUpdated(self, evt):
        self._updateVideoSize()
        evt.Skip()
