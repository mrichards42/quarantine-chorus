"""ffprobe helpers."""

import ffmpeg
import funcy as F


EXECUTABLE = 'ffprobe'


class ProbeResult:
    def __init__(self, filename, probe_result):
        self.filename = filename
        self._probe = probe_result
        self.format = self._probe.get('format', {})
        self.video = {}
        self.audio = {}
        self.maps = [self.format] + self._probe.get('streams', [])
        for s in self._probe.get('streams', []):
            if s['codec_type'] == 'audio':
                self.audio = self.audio or s
            elif s['codec_type'] == 'video':
                self.video = self.video or s

    def get(self, k, default=None):
        for d in self.maps:
            if d:
                v = d.get(k)
                if v is not None:
                    return v
        return default

    def get_in(self, ks, default=None):
        for d in self.maps:
            if d:
                v = F.get_in(d, ks)
                if v is not None:
                    return v
        return default

    @property
    def rotate(self):
        return int(self.get_in(['tags', 'rotate'], 0))

    @property
    def width(self):
        if self.rotate in (90, 270):
            return self.get('height')
        else:
            return self.get('width')

    @property
    def height(self):
        if self.rotate in (90, 270):
            return self.get('width')
        else:
            return self.get('height')

    @property
    def duration(self):
        return max(float(m.get('duration', 0)) for m in self.maps)


def probe(filename, cmd=None, **kwargs):
    res = ffmpeg.probe(filename, cmd or EXECUTABLE, **kwargs)
    if res:
        return ProbeResult(filename, res)
