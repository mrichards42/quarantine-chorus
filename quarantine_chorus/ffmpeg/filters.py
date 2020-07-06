"""Additional ffmpeg filters."""

import ffmpeg
import funcy as F


# == Low level ==
# These are just additional filters

def scale(stream, w=None, h=None, **kwargs):
    """Scales a video stream.

    Using a negative number for width or height makes that dimension scale
    proportionally, but divisible by the number given.
    """
    if w:
        kwargs['width'] = w
    if h:
        kwargs['height'] = h
    return stream.filter('scale', **kwargs)


def pad_audio(stream, seconds):
    """Pads the beginning of the audio with silence."""
    ms = int(seconds * 1000)
    return stream.filter('adelay', f'{ms}|{ms}')


def pad_video(stream, seconds):
    """Pads the beginning of the video with black frames."""
    return stream.filter('tpad', start_mode='add', start_duration=f'{seconds:0.3f}')


def trim_audio(stream, seconds):
    """Trims the beginning of the audio."""
    return (stream
            .filter('atrim', f'{seconds:0.3f}')
            # atrim messes with pts, so we need to reset it
            .filter('asetpts', 'PTS-STARTPTS'))


def trim_video(stream, seconds):
    """Trims the beginning of the video."""
    return (stream
            .filter('trim', f'{seconds:0.3f}')
            # trim messes with pts, so we need to reset it
            .filter('setpts', 'PTS-STARTPTS'))


def aresample(stream, sample_rate, **kwargs):
    """Resamples audio.

    Use first_pts=0 to also reset audio timestamps.
    """
    return stream.filter('aresample', sample_rate, **kwargs)


def xstack(*streams, layout, **kwargs):
    """Adds an xstack layout for a number of video streams.

    `streams` is either a list of video streams, or any number of varargs streams.

    `layout` is a list with one item per video. Items may be either 2-tuples of (w, h)
    or strings of "w_h", using ffmpeg's xstack layout syntax.

    Example:

        # A 2x2 grid
        xstack(v1, v2, v3, v4, ["0_0", "w0_0", "0_h0", "w0_h0"])

        # Same thing
        xstack([v1, v2, v3, v4], [(0, 0), ("w0", 0), (0, "h0"), ("w0", "h0")])
    """
    streams = F.lflatten(streams)

    assert(len(streams) == len(layout))

    layout_strs = []
    for i, l in enumerate(layout):
        if isinstance(l, (list, tuple)):
            layout_strs.append(f'{l[0]}_{l[1]}')
        else:
            layout_strs.append(str(l))

    return ffmpeg.filter(streams, 'xstack',
                         inputs=len(streams),
                         layout='|'.join(layout_strs),
                         **kwargs)


def amix(*streams, **kwargs):
    """Mixes multiple audio streams.

    `streams` is either a list of audio streams, or any number of varargs streams.
    """
    streams = F.lflatten(streams)
    return ffmpeg.filter(streams, 'amix', inputs=len(streams), **kwargs)


def volume(stream, volume=None, *, dB=None, **kwargs):
    """Adjusts the volume of an audio stream.

    `volume` can be any of the following
    - A number used to multiply the current volume
    - A string of the format '[number]dB' to shift volume by some number of decibels
    - An expression used to compute volume frame-by-frame

    You may also use the `dB` arg with a number.

    Examples:

        volume(audio, '-2dB')  # Adjust down 2 dB
        volume(audio, dB=-2)   # Same thing
        volume(audio, 1.5)     # Increase volume to 150% of current
    """
    if volume is None and dB is not None:
        volume = f'{dB}dB'
    return stream.filter('volume', volume, **kwargs)


# == High level ==
# These are filters that use analysis data

def align_audio(stream, analysis):
    """Aligns an audio stream based on a cross-correlation analysis.

    Analysis should have 'pad_seconds' and 'trim_seconds' keys.
    """
    if analysis['pad_seconds'] > 0:
        return pad_audio(stream, analysis['pad_seconds'])
    elif analysis['trim_seconds'] > 0:
        return trim_audio(stream, analysis['trim_seconds'])
    else:
        return stream


def align_video(stream, analysis):
    """Aligns a video stream based on a cross-correlation analysis.

    Analysis should have 'pad_seconds' and 'trim_seconds' keys.
    """
    if analysis['pad_seconds'] > 0:
        return pad_video(stream, analysis['pad_seconds'])
    elif analysis['trim_seconds'] > 0:
        return trim_video(stream, analysis['trim_seconds'])
    else:
        return stream
