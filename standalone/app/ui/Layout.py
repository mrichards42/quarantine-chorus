"""LayoutPanel"""

from app.model.tracklist import TrackList

from . import base


class LayoutPanel(base.LayoutPanel):
    def __init__(self, parent):
        super().__init__(parent)
        TrackList.subscribe(self, self._updateLayout, video=True)

    def _updateLayout(self, tracks, video_height=360):
        old_tracks = set(self.m_layoutPreview.GetTrackNames())
        needs_layout = set(old_tracks) != set(t['path'] for t in tracks)
        # Update the layout preview
        self.m_layoutPreview.SetTracks(tracks)
        self.m_layoutPreview.SetBackgroundSize(**TrackList.background_size())
        # New tracks means run the layout again
        if needs_layout:
            layout = TrackList.as_layout(video_height=video_height)
            TrackList.update_from_layout(layout)
