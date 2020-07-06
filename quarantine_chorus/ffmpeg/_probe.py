"""ffprobe helpers."""

import ffmpeg


EXECUTABLE = 'ffprobe'


def probe(filename, cmd=None, **kwargs):
    return ffmpeg.probe(filename, cmd or EXECUTABLE, **kwargs)


def video_info(f):
    for stream in probe(f).get('streams', []):
        if stream['codec_type'] == 'video':
            return stream


def audio_info(f):
    for stream in probe(f).get('streams', []):
        if stream['codec_type'] == 'audio':
            return stream
