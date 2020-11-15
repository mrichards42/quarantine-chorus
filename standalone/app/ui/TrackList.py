"""TrackListPanel"""

import wx
import wx.lib.newevent

from quarantine_chorus.mlt.xml import fmt_duration

from app.model.tracklist import TrackList

from . import base
from . import draglist
from . import dialogs


# == Labels ==

def orientation(track):
    if track.get('original_width') is None:
        return ""
    elif track['original_width'] > track['original_height']:
        return "horizontal"
    else:
        return "vertical"


def duration_label(track):
    if not track.get('probe'):
        return "..."
    else:
        d = fmt_duration(track['duration'])
        if d.startswith('00:'):
            return d[3:]
        else:
            return d


def streams_label(track):
    if not track.get('probe'):
        return "..."
    else:
        return "+".join(filter(None, ["Audio" if track['has_audio'] else None,
                                      "Video" if track['has_video'] else None]))


def size_label(track):
    if not track.get('probe'):
        return "..."
    elif track['has_video']:
        return f"{track['original_width']}x{track['original_height']}"
    else:
        return ""


def alignment_label(track):
    shift = track['alignment_analysis'].get('correlation_shift_seconds')
    if shift is not None:
        return f"{shift:+0.3f} s"
    elif track['status'].get('alignment') == 'running':
        return "...analyzing..."


def loudness_label(track):
    target = track['filters'].get('loudness', {}).get('program')
    if target is not None:
        return f"complete ({target} dB)"
    elif track['status'].get('loudness') == 'running':
        return "...analyzing..."


def fade_in_label(track):
    duration = track['filters'].get('fade_in', {}).get('duration', 0)
    return f"{duration} seconds"


def fade_out_label(track):
    duration = track['filters'].get('fade_out', {}).get('duration', 0)
    return f"{duration} seconds"


# == Panel ==

class TrackListPanel(base.TrackListPanel):
    def __init__(self, parent):
        super().__init__(parent)
        self.pinned_columns = set()
        self._setupList()
        # List dragging setup
        self.listDragger = draglist.ListDragger(self.m_listCtrl)
        self.m_listCtrl.Bind(draglist.EVT_BEGIN_DRAG, self.OnDragBegin)
        self.m_listCtrl.Bind(draglist.EVT_DRAGGING, self.OnDragging)
        self.m_listCtrl.Bind(draglist.EVT_END_DRAG, self.OnDragEnd)
        TrackList.subscribe(self, self._refreshList)

    # -- ListCtrl --

    def GetSelectedTracks(self):
        """Returns a list of selected tracks."""
        return [t for i, t in enumerate(TrackList.all_tracks())
                if self.m_listCtrl.IsSelected(i)]

    def GetSelectedTrackNames(self):
        """Returns a list of selected track filenames."""
        return [name for i, name in enumerate(TrackList.track_names())
                if self.m_listCtrl.IsSelected(i)]

    def _setupList(self):
        # Set up columns
        self.m_listCtrl.ClearAll()
        self.m_listCtrl.AppendColumn("File name")
        self.m_listCtrl.AppendColumn("Streams")
        self.m_listCtrl.AppendColumn("Duration", wx.LIST_FORMAT_RIGHT)
        self.m_listCtrl.AppendColumn("Size")
        self.m_listCtrl.AppendColumn("Orientation")
        self.m_listCtrl.AppendColumn("Alignment shift", wx.LIST_FORMAT_RIGHT)
        self.m_listCtrl.AppendColumn("Normalization")
        self.m_listCtrl.AppendColumn("Fade in")
        self.m_listCtrl.AppendColumn("Fade out")
        self.m_listCtrl.AppendColumn("Full path")
        self._refreshList()

    def _refreshList(self, tracks=None):
        # Make sure we have the right number of items
        tracks = tracks or []
        while self.m_listCtrl.GetItemCount() > len(tracks):
            self.m_listCtrl.DeleteItem(self.m_listCtrl.GetItemCount() - 1)
        while self.m_listCtrl.GetItemCount() < len(tracks):
            self.m_listCtrl.InsertItem(self.m_listCtrl.GetItemCount(), '')
        # Update all the text
        for idx, t in enumerate(tracks):
            row = [
                t['name'],
                streams_label(t),
                duration_label(t),
                size_label(t),
                orientation(t),
                alignment_label(t) or '(click align)',
                loudness_label(t) or '(click normalize)',
                fade_in_label(t) or '(click fade in)',
                fade_out_label(t) or '(click fade out)',
                t['path'],
            ]
            for col, label in enumerate(row):
                if self.m_listCtrl.GetItemText(idx, col) != label:
                    self.m_listCtrl.SetItem(idx, col, label)
        # Auto-size columns
        for idx in range(self.m_listCtrl.GetColumnCount()):
            if idx not in self.pinned_columns:
                self.m_listCtrl.SetColumnWidth(idx, wx.LIST_AUTOSIZE_USEHEADER)
        self.m_listCtrl.Refresh()
        self._refreshListButtons()

    def _refreshListButtons(self):
        count = self.m_listCtrl.GetSelectedItemCount()
        tracks_text = f"{count or 'all'} {'track' if count == 1 else 'tracks'}"
        self.m_alignBtn.SetLabel(f"Align {tracks_text}")
        self.m_normalizeBtn.SetLabel(f"Normalize {tracks_text}")
        self.m_fadeInBtn.SetLabel(f"Fade in {tracks_text}")
        self.m_fadeOutBtn.SetLabel(f"Fade out {tracks_text}")
        if count == 0:
            self.m_deleteBtn.Disable()
            self.m_deleteBtn.SetLabel(f"Delete")
        else:
            self.m_deleteBtn.Enable()
            self.m_deleteBtn.SetLabel(f"Delete {tracks_text}")
        self.m_listButtonSizer.Layout()

    def OnListSelectionChanged(self, evt):
        self._refreshListButtons()

    def OnListHeaderResized(self, evt):
        self.pinned_columns.add(evt.GetColumn())
        evt.Skip()

    # -- List dragging --

    def _moveItems(self, delta):
        # In order to update the list in-place, we need to:
        # - iterate forwards if delta is negative
        # - iterate backwards if delta is positive
        order = list(enumerate(TrackList.track_names()))
        if delta > 0:
            order = reversed(order)
        with TrackList.transaction():
            for i, f in order:
                if f in self.dragitems:
                    TrackList.move(i, i + delta)

    def _dragDelta(self, evt):
        # Base delta
        delta = evt.index - self.dragidx
        # Constrain delta so that the first item doesn't end up negative, and the last
        # item doesn't end up off the list
        tracks = TrackList.track_names()
        for i, f in enumerate(tracks):
            if f in self.dragitems:
                if i + delta < 0:
                    delta = -i
                elif i + delta >= len(tracks):
                    delta = len(tracks) - i - 1
        return delta

    def OnDragBegin(self, evt):
        self.dragitems = set(self.GetSelectedTrackNames())
        self.dragidx = evt.index

    def DoDrag(self, evt):
        delta = self._dragDelta(evt)
        self._moveItems(delta)
        # reset the selection
        for i, f in enumerate(TrackList.track_names()):
            self.m_listCtrl.Select(i, f in self.dragitems)

    def OnDragging(self, evt):
        self.DoDrag(evt)
        self.dragidx = evt.index

    def OnDragEnd(self, evt):
        self.DoDrag(evt)
        del self.dragitems
        del self.dragidx

    # -- Button events --

    def OnDeleteTracks(self, evt):
        TrackList.remove(*self.GetSelectedTrackNames())

    def OnAlign(self, evt):
        reference = wx.GetSingleChoice(
            "Select a reference track",
            self.m_alignBtn.GetLabel(),
            TrackList.track_names(),
            parent=self
        )
        if reference:
            tracks = self.GetSelectedTrackNames() or TrackList.track_names()
            for path in tracks:
                TrackList.align_track(reference, path)

    def OnNormalize(self, evt):
        target = wx.GetNumberFromUser(
            "Enter the normalization target",
            "Target LUFS",
            self.m_normalizeBtn.GetLabel(),
            value=-23,
            min=-50,
            max=-6,
            parent=self
        )
        if target != -1:
            tracks = self.GetSelectedTrackNames() or TrackList.track_names()
            for path in tracks:
                TrackList.normalize_track(path, target)

    def OnFadeIn(self, evt):
        seconds = dialogs.GetFloatFromUser(
            "Enter the fade in duration in seconds",
            self.m_fadeInBtn.GetLabel(),
            value=1.5,
            min=0,
            max=300,
            parent=self
        )
        if seconds is not None:
            tracks = self.GetSelectedTrackNames() or TrackList.track_names()
            for path in tracks:
                if seconds == 0:
                    TrackList.remove_filter(path, 'fade_in')
                else:
                    TrackList.set_filter(path, 'fade_in', {'duration': seconds})

    def OnFadeOut(self, evt):
        seconds = dialogs.GetFloatFromUser(
            "Enter the fade out duration in seconds",
            self.m_fadeOutBtn.GetLabel(),
            value=1.5,
            min=0,
            max=300,
            parent=self
        )
        if seconds is not None:
            tracks = self.GetSelectedTrackNames() or TrackList.track_names()
            for path in tracks:
                if seconds == 0:
                    TrackList.remove_filter(path, 'fade_out')
                else:
                    TrackList.set_filter(path, 'fade_out', {'duration': seconds})
