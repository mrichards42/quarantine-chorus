"""melt cli helpers."""

import logging
import re
import subprocess


EXECUTABLE = 'melt'


def set_executable(melt=None):
    if melt is not None:
        global EXECUTABLE
        EXECUTABLE = melt


def _run(
        run_fn,
        args,
        cmd=None,
        pipe_stdin=False,
        pipe_stdout=False,
        pipe_stderr=False,
        quiet=False,
        **kwargs,
):
    args = [cmd or EXECUTABLE] + args
    logging.info('Running melt with args: %s', args)
    stdin_stream = subprocess.PIPE if pipe_stdin else None
    stdout_stream = subprocess.PIPE if pipe_stdout or quiet else None
    stderr_stream = subprocess.PIPE if pipe_stderr or quiet else None
    return run_fn(
        args, stdin=stdin_stream, stdout=stdout_stream, stderr=stderr_stream,
        **kwargs,
    )


class MeltNode:
    def __init__(self):
        self.args = []

    def _append(self, *args, **kwargs):
        self.args.extend(args)
        for k, v in kwargs.items():
            self.args.append(f'{k}={v}')
        return self

    def _append_with_arg(self, flag, name, arg=None, **properties):
        if arg:
            name = f'{name}:{arg}'
        return self._append(flag, name, **properties)

    def flag(self, **kwargs):
        for k, v in kwargs.items():
            self.args.append(f'-{k}')
            if v is not True:
                self.args.append(v)
        return self

    def producer(self, name, **properties):
        return self._append(name, **properties)

    def consumer(self, name, arg=None, **properties):
        return self._append_with_arg('-consumer', name, arg, **properties)

    def transition(self, name, arg=None, **properties):
        return self._append_with_arg('-transition', name, arg, **properties)

    def filter(self, name, arg=None, **properties):
        return self._append_with_arg('-filter', name, arg, **properties)

    def attach(self, name, arg=None, **properties):
        return self._append_with_arg('-attach', name, arg, **properties)

    def attach_cut(self, name, arg=None, **properties):
        return self._append_with_arg('-attach-cut', name, arg, **properties)

    def attach_track(self, name, arg=None, **properties):
        return self._append_with_arg('-attach-track', name, arg, **properties)

    def attach_clip(self, name, arg=None, **properties):
        return self._append_with_arg('-attach-clip', name, arg, **properties)

    def track(self):
        return self._append('-track')

    def run_async(self, cmd=None, **kwargs):
        return _run(subprocess.Popen, self.args, cmd, **kwargs)

    def run(self, cmd=None, encoding='utf-8', **kwargs):
        proc = _run(subprocess.run, self.args, cmd, encoding=encoding, **kwargs)
        proc.check_returncode()
        return proc.stdout, proc.stderr


def producer(name, **properties):
    """Returns a MeltNode representing a producer"""
    return MeltNode().producer(name, **properties)


def loudness_analysis(filename, target=-23, cmd=None):
    """Runs the loudness analysis pass, returning a map of:

    program -- the target loudness level (in db)
    results -- the raw results string
    L       -- loudness
    R       -- range
    P       -- peak
    """
    # Run the melt process
    (stdout, stdin) = (
        producer(filename)
        .filter('loudness', program=target)
        .consumer('xml', video_off=1, all=1)
        .flag(silent=True)
        .run(pipe_stdout=True)
    )
    # Parse output. The relevant line looks like:
    # <property name="results">L: -28.586770    R: 10.149692    P 0.186446</property>
    m = re.search(r'(?:[LRP]:?\s*[\-\d.]+\s*){3}', stdout)
    if m is not None:
        ret = {
            'results': m.group(),
            'program': target,
        }
        for k, v in re.findall(r'([LRP]):?\s*(\S+)', m.group()):
            ret[k] = float(v)
        return ret
