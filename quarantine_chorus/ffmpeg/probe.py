"""ffprobe helpers."""

import ffmpeg


def video_info(f):
    for stream in ffmpeg.probe(f).get('streams', []):
        if stream['codec_type'] == 'video':
            return stream


def audio_info(f):
    for stream in ffmpeg.probe(f).get('streams', []):
        if stream['codec_type'] == 'audio':
            return stream
