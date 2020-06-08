"""Two-pass loudnorm filter."""

import json

import ffmpeg


def run_analysis(filename, params, cmd=None, **input_args):
    """Runs the loudnorm analysis pass for a file. Returns output as a dict.

    `params` should include i, tp, and lra.
    """
    stream = (ffmpeg
              .input(filename, **input_args)
              .audio.filter('loudnorm',
                            print_format='json',
                            i=params['i'],
                            tp=params['tp'],
                            lra=params['lra']))
    # ugh, loudnorm prints to stderr, and the script for automating two-pass
    # normalization (written by the loudnorm author!) just parses the last 12
    # lines of output.
    # https://gist.github.com/kylophone/84ba07f6205895e65c9634a956bf6d54#file-loudness-rb-L29
    _, stderr = stream.output('-', f='null').run(cmd=cmd, capture_stderr=True)
    json_str = '\n'.join(stderr.decode('utf-8').splitlines()[-12:])
    d = json.loads(json_str)
    # We need the input params for the second pass
    d.update(params)
    return d


def loudnorm(stream, analysis, resample=None):
    """Adds the second-pass loudnorm filter for an audio stream.

    `analysis` should be a dict with the loudnorm output plus its input params (as
    returned by `run_analysis`).

    Note that the loudnorm filter upsamples to 192k. Use `resample` with a new sample
    rate to downsample after running loudnorm.
    """
    stream = stream.filter('loudnorm',
                           print_format='summary',
                           linear=True,
                           i=analysis['i'],
                           tp=analysis['tp'],
                           lra=analysis['lra'],
                           measured_i=analysis['input_i'],
                           measured_tp=analysis['input_tp'],
                           measured_lra=analysis['input_lra'],
                           measured_thresh=analysis['input_thresh'],
                           offset=analysis['target_offset'])
    # Loudnorm upsamples to 192k which is absurd
    # resample back to a lower rate by default
    if resample is not None:
        sample_rate = resample if isinstance(resample, int) else 48000
        stream = stream.filter('aresample', sample_rate, first_pts=0)
    return stream
