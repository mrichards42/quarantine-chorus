"""Basic additions to the wxFB-generated UI"""
import wx

from quarantine_chorus import ffmpeg

from . import wxFB_ui
from .wxFB_ui import TrackListPanel, Frame, LogDialog  # no changes needed  # noqa F401


def load_bitmap(filename, h):
    (stdout, _) = (ffmpeg.input(filename, ss=10)
                   .scale(w=-2, h=h)
                   .output('pipe:', vframes=1, format='image2pipe', vcodec='png')
                   .run(capture_stdout=True))
    return stdout


class LayoutPreview(wx.Window):
    def __init__(self, parent):
        super().__init__(parent, id=wx.ID_ANY)
        self.tracks = []
        self.width = 0
        self.height = 0
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.bitmaps = {}
        self._bitmap_heights = {}
        self.SetBackgroundColour(wx.TransparentColour)

    VIDEO_BACKGROUND_COLOR = wx.Colour(221, 160, 221, 255 * 0.85)
    VIDEO_BORDER_COLOR = wx.Colour(255, 0, 255)

    # -- Public functions --

    def SetTracks(self, tracks):
        self.tracks = tracks
        for t in tracks:
            self.LoadBitmap(t)
        self.Refresh()

    def SetBackgroundSize(self, width, height):
        self.width = width
        self.height = height
        self.Refresh()

    def GetTrackNames(self):
        if self.tracks:
            return [t['path'] for t in self.tracks]
        else:
            return []

    def LoadBitmap(self, track):
        path = track['path']
        height = track.get('height')
        if not height:
            return
        # Make sure we aren't already loading this bitmap
        if self._bitmap_heights.get(path) and self._bitmap_heights[path] == height:
            return
        self._bitmap_heights[path] = height

        def callback(png_bytes):
            if self._bitmap_heights[path] == height:
                self.bitmaps[path] = wx.Bitmap.NewFromPNGData(png_bytes, len(png_bytes))
            self.Refresh()

        wx.GetApp().RunInBackground(load_bitmap, path, height, callback=callback)

    # -- Drawing --

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        dc.Clear()
        if not self.tracks or not self.width or not self.height:
            return
        scale = min(self.GetSize().GetHeight() / self.height,
                    self.GetSize().GetWidth() / self.width)
        dc.SetUserScale(scale, scale)
        # Outline
        dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.BLACK))
        dc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.BLACK))
        dc.DrawRectangle(0, 0, self.width, self.height)
        # Videos
        for t in self.tracks:
            self.DrawVideo(dc, t)

    def DrawVideo(self, dc, t):
        bmp = self.bitmaps.get(t['path'])
        if bmp:
            _ = wx.DCClipper(dc, t['left'], t['top'], t['width'], t['height'])
            dc.DrawBitmap(bmp, t['left'] - t.get('crop', 0) / 2, t['top'])
        else:
            dc.SetPen(wx.ThePenList.FindOrCreatePen(self.VIDEO_BORDER_COLOR))
            dc.SetBrush(wx.TheBrushList.FindOrCreateBrush(self.VIDEO_BACKGROUND_COLOR))
            dc.DrawRectangle(t['left'], t['top'], t['width'], t['height'])


class LayoutPanel(wxFB_ui.LayoutPanel):
    def __init__(self, parent):
        super().__init__(parent)
        self.m_layoutPreview = LayoutPreview(self.m_sizer.GetStaticBox())
        self.m_sizer.Prepend(self.m_layoutPreview, 1, wx.EXPAND | wx.ALL, 5)
