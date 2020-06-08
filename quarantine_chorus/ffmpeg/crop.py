"""Crop detection filter."""

import re

import ffmpeg
import funcy as F


def read_cropdetect_line(l):
    m = re.search(r'x1:(?P<x>\S+).*y1:(?P<y>\S+).*w:(?P<w>\S+).*h:(?P<h>\S+)', l)
    if m:
        return m.groupdict()


def run_cropdetect(filename, cmd=None, **input_args):
    """Runs the crepdetect filter for a file. Returns output as a dict.

    Runs crop detection only on a single frame. To select the frame to use, pass `ss`
    with the start position in seconds.
    """
    stream = (ffmpeg
              .input(filename, t=1, **input_args)
              .video.filter('cropdetect', round=2))
    # Cropdetect outputs a line per frame
    _, stderr = stream.output('-', f='null').run(cmd=cmd, capture_stderr=True)
    return F.first(F.keep(read_cropdetect_line, stderr.decode('utf-8').splitlines()))


def crop(stream, **kwargs):
    """Crops a video stream.

    With only `w` and `h` crops the center of the video.
    With `x`, `y`, `w`, and `h` crops the specified rectangle.
    """
    return stream.filter('crop', **kwargs)
