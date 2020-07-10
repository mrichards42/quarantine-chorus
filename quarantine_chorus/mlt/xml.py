"""Shotcut MLT template

See: https://www.mltframework.org/docs/mltxml/
See: https://shotcut.org/notes/mltxml-annotations/
"""

import pkgutil

import pybars


compiler = pybars.Compiler()
TEMPLATE_STR = pkgutil.get_data('quarantine_chorus.mlt', 'template.mlt.hbs').decode('utf-8')
TEMPLATE = compiler.compile(TEMPLATE_STR)


def fmt_duration(seconds):
    s = int(seconds)
    ms = int((seconds - s) * 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}'


def write_file(tracks, width=None, height=None):
    video_tracks = [t for t in tracks if t.get('has_video')]
    ctx = {
        'width': width or int(max(t['left'] + t['width'] for t in video_tracks)),
        'height': height or int(max(t['top'] + t['height'] for t in video_tracks)),
        'total_duration': max(t.get('duration', 0) for t in tracks),
        'frame_rate': 30,
        'tracks': tracks
    }
    return TEMPLATE(ctx, helpers={'fmt_duration': lambda _, d: fmt_duration(d or 0),
                                  'inc': lambda _, x: x + 1})
