"""Monkey patches around ffmpeg-python"""

import logging
import subprocess

from ffmpeg import *  # noqa F403

# For patching run_async
import ffmpeg._run

# extra filters
from ffmpeg.nodes import filter_operator, output_operator
from . import filters as extra_filters
from .filters import *  # noqa F403

# Loudnorm filters
from .loudnorm import run_analysis as run_loudnorm_analysis  # noqa F401
from .loudnorm import loudnorm

# Crop filters
from .crop import run_cropdetect  # noqa F401
from .crop import crop

# ffprobe helpers
from . import _probe
from ._probe import probe  # noqa F401

# ffplay helpers
from . import _play
from ._play import play, play_async  # noqa F401


# == Patch run_async with logging and allow changing default ffmpeg ==

EXECUTABLE = 'ffmpeg'


def set_executables(ffmpeg=None, ffprobe=None, ffplay=None):
    if ffmpeg is not None:
        global EXECUTABLE
        EXECUTABLE = ffmpeg
    if ffprobe is not None:
        _probe.EXECUTABLE = ffprobe
    if ffplay is not None:
        _play.EXECUTABLE = ffplay


@output_operator()
def run_async(
        stream_spec,
        cmd=None,  # changed
        pipe_stdin=False,
        pipe_stdout=False,
        pipe_stderr=False,
        quiet=False,
        overwrite_output=False,
):
    cmd = cmd or EXECUTABLE  # added
    args = ffmpeg._run.compile(stream_spec, cmd, overwrite_output=overwrite_output)
    logging.info('Running ffmpeg with args: %s', args)  # added
    stdin_stream = subprocess.PIPE if pipe_stdin else None
    stdout_stream = subprocess.PIPE if pipe_stdout or quiet else None
    stderr_stream = subprocess.PIPE if pipe_stderr or quiet else None
    return subprocess.Popen(
        args, stdin=stdin_stream, stdout=stdout_stream, stderr=stderr_stream
    )


_old_run = ffmpeg._run.run


@output_operator()
def run(stream_spec, cmd=None, **kwargs):
    return _old_run(stream_spec, cmd or EXECUTABLE, **kwargs)


ffmpeg._run.run = run
ffmpeg._run.run_async = run_async


# == Patch our extra filters into ffmpeg's fluent node system ==


for name in list(extra_filters.__dict__.keys()):
    if name.startswith('_'):
        continue
    f = extra_filters.__dict__[name]
    if hasattr(f, '__module__') and f.__module__ == extra_filters.__name__:
        extra_filters.__dict__[name] = filter_operator()(f)

filter_operator()(loudnorm)
filter_operator()(crop)
