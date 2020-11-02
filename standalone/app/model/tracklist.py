from pathlib import Path

import wx

from quarantine_chorus import align
from quarantine_chorus import ffmpeg
from quarantine_chorus import mlt

from .observable import Observable


# Singleton
# TODO: could also be part of the app?
class _TrackList(Observable):
    def __init__(self):
        super().__init__()
        self.tracks = {}
        self.track_order = []
        self.background = {'width': 0, 'height': 0}

    # Subscription value

    def value(self, **kwargs):
        if kwargs.get('video'):
            return self.video_tracks()
        else:
            return self.all_tracks()

    # Getters

    def track_names(self):
        return self.track_order

    def all_tracks(self):
        return [self.tracks[f] for f in self.track_order]

    def video_tracks(self):
        return [t for t in self.all_tracks() if t.get('has_video')]

    def audio_tracks(self):
        return [t for t in self.all_tracks() if t.get('has_audio')]

    def background_size(self):
        return self.background

    # Conversions

    def as_mlt_tracks(self):
        return [dict(**t, filename=t['path']) for t in self.all_tracks()]

    def as_layout(self, aspect_ratio=16/9, video_height=None):
        from quarantine_chorus.layout import Layout, LayoutTrack
        layout = Layout((LayoutTrack(name=t['path'],
                                    width=t['original_width'],
                                    height=t['original_height'])
                         for t in self.video_tracks()),
                        aspect_ratio)
        if video_height:
            for v in layout.videos:
                v.scale(height=video_height)
        layout.center()
        return layout

    # Mutators

    def add(self, *paths):
        for path in paths:
            if path not in self.track_order:
                self.track_order.append(path)
                self.tracks[path] = self._new(path)
                self.probe_track(path)
        self.notify()

    def remove(self, *paths):
        for path in paths:
            self.track_order.remove(path)
            del self.tracks[path]
        self.notify()

    def move(self, from_idx, to_idx):
        self.track_order.insert(to_idx, self.track_order.pop(from_idx))
        self.notify()

    def merge(self, path, *args, **kwargs):
        for d in args:
            self.tracks[path].update(d)
        self.tracks[path].update(kwargs)
        self.notify()

    def update_from_probe(self, probe):
        path = probe.filename
        self.tracks[path] = dict(**{
            'has_video': bool(probe.video),
            'has_audio': bool(probe.audio),
            'video_index': probe.video.get('index'),
            'audio_index': probe.audio.get('index'),
            'duration': probe.duration,
            'left': 0,
            'top': 0,
            'width': probe.width,
            'height': probe.height,
            'original_width': probe.width,
            'original_height': probe.height,
            'probe': probe,
        }, **self.tracks[path])
        self.notify()

    def update_from_layout(self, layout, total_width=None, total_height=None):
        total_width = total_width or layout.width
        total_height = total_height or layout.height
        scale = min(total_width / layout.width, total_height / layout.height)
        for v in layout.videos:
            self.tracks[v.name]['left'] = int(v.left * scale)
            self.tracks[v.name]['top'] = int(v.top * scale)
            self.tracks[v.name]['width'] = int(v.width * scale)
            self.tracks[v.name]['height'] = int(v.height * scale)
            self.tracks[v.name]['crop'] = int(v.crop_amount() * scale)
        self.background['width'] = int(total_width)
        self.background['height'] = int(total_height)
        self.notify()

    def _new(self, path):
        return {
            'path': path,
            'name': Path(path).name,
            'alignment_analysis': {},
            'loudness_analysis': {},
        }

    # Background events

    def probe_track(self, path):
        wx.GetApp().RunInBackground(ffmpeg.probe, path, callback=self.update_from_probe)

    def align_track(self, reference, subject):
        self.merge(subject, alignment_analysis={'running': True})
        wx.GetApp().RunInBackground(
            lambda: align.cross_correlate(reference, subject,
                                          samplerate=22400,
                                          preprocess='loudness_25')[0],
            callback=lambda analysis: self.merge(subject, alignment_analysis=analysis))

    def normalize_track(self, path, target):
        self.merge(path, loudness_analysis={'running': True})
        wx.GetApp().RunInBackground(
            mlt.melt.loudness_analysis, path, target,
            callback=lambda result: self.merge(path, loudness_analysis=result))


TrackList = _TrackList()
