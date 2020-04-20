"""Loudness normalization using ffmpeg"""

import json
import os
import subprocess

LOUDNORM_PARAMS = {
    'i': '-16',
    'tp': '-1.5',
    'lra': '11',
}

def loudnorm_analysis(filename, trim_seconds=0):
    loudnorm = (
        'loudnorm='
        'i={i}:'
        'tp={tp}:'
        'lra={lra}:'
        'print_format=json'
    ).format(**LOUDNORM_PARAMS)
    cmd = ['ffmpeg', '-ss', '%0.3f' % trim_seconds, '-i', filename,
           '-af', loudnorm,
           '-f', 'null', '-']
    proc = subprocess.run(cmd, capture_output=True)
    # ugh, loudnorm prints to stderr, and the script for automating two-pass
    # normalization (written by the loudnorm author!) just parses the last 12
    # lines of output.
    # https://gist.github.com/kylophone/84ba07f6205895e65c9634a956bf6d54#file-loudness-rb-L29
    json_str = '\n'.join(proc.stderr.decode('utf-8').splitlines()[-12:])
    return json.loads(json_str)

def apply_loudnorm(filename, analysis_output):
    loudnorm = (
        'loudnorm='
        'print_format=summary:'
        'linear=true:'
        'i={i}:'
        'lra={lra}:'
        'tp={tp}:'
        'measured_i={input_i}:'
        'measured_lra={input_lra}:'
        'measured_thresh={input_thresh}:'
        'offset={target_offset}'
    ).format(**analysis_output, **LOUDNORM_PARAMS)
    output = filename + '.loudnorm.wav'
    cmd = ['ffmpeg',
           '-y', # overwrite
           '-i', filename,
           '-af', loudnorm,
           # loudnorm increases sample rate to 192 kHz, but that's extremely
           # excessive
           '-ar', '44100',
           output]
    subprocess.run(cmd)
    os.replace(output, filename) # ffmpeg can't output to the same file
