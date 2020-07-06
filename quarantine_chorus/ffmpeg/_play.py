"""ffplay helpers."""

import subprocess

import ffmpeg


EXECUTABLE = 'ffplay'


def play_async(
        filename,
        cmd=None,
        pipe_stdin=False,
        pipe_stdout=False,
        pipe_stderr=False,
        quiet=False,
        **kwargs
):
    args = [cmd or EXECUTABLE, '-i', filename]
    for k, v in kwargs.items():
        args.append(f'-{k}')
        if v is not None:
            args.append(str(v))
    stdin_stream = subprocess.PIPE if pipe_stdin else None
    stdout_stream = subprocess.PIPE if pipe_stdout or quiet else None
    stderr_stream = subprocess.PIPE if pipe_stderr or quiet else None
    return subprocess.Popen(
        args, stdin=stdin_stream, stdout=stdout_stream, stderr=stderr_stream
    )


def play(filename, cmd=None, **kwargs):
    proc = play_async(filename, cmd, **kwargs)
    out, err = proc.communicate(None)
    retcode = proc.poll()
    if retcode:
        raise ffmpeg.Error('ffplay', out, err)
    return out, err
