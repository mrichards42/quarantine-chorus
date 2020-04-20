#!/usr/bin/env python3
"""Align similar audio files using cross-correlation.
Prints offset (in seconds) of subject.wav from reference.wav

Usage: align.py [options] (<reference.wav> <subject.wav>|--analysis=file)

Options:
  -p, --plot=file          Save an analysis plot
      --plot-size=w,h      Plot size in inches [default: 10,7]
  -s, --start=seconds      Subject slice start, in seconds (positive or negative)
  -e, --end=seconds        Subject slice end, in seconds (positive or negative)
      --min-shift=seconds  Shift window start, in seconds (positive or negative)
      --max-shift=seconds  Shift window end, in seconds (positive or negative)
      --loudnorm           Include ffmpeg normalization analysis
  -o, --output=file        Align (trim or pad) subject and write to file
      --json               Print output as json
  -h, --help               Show this help screen
      --analysis=file      Read previous analysis file
      --preprocess=name    Select a preprocessing algorithm [default: none]
"""

import json
import logging
import os

import numpy as np
import scipy.io.wavfile as wav
from docopt import docopt

from . import align_wav, loudnorm, plot

def read_wav_channel(f):
    samplerate, data = wav.read(f)
    if len(data.shape) > 1 and data.shape[1] > 1:
        # just the left channel
        return samplerate, data[:, 0]
    else:
        return samplerate, data

def write_aligned_wav(data, opts):
    logging.info('Aligning subject wav')
    if opts['trim']:
        logging.info('  trim beginning: %f seconds; %d samples', opts['trim_seconds'], opts['trim'])
        data = data[opts['trim']:]
    elif opts['pad']:
        logging.info('  pad beginning: %f seconds; %d samples', opts['pad_seconds'], opts['pad'])
        data = np.pad(data, [opts['pad'], 0])
    return data

def main(opts):
    analysis = opts['analysis']
    # -- Read WAV files -------------------------------------------------------
    logging.info('Reading reference wav: %s', opts['<reference.wav>'])
    samplerate_ref, ref = read_wav_channel(opts['<reference.wav>'])
    logging.info('  sample rate: %d Hz', samplerate_ref)
    logging.info('  length: %f seconds; %d samples', len(ref) / samplerate_ref, len(ref))

    logging.info('Reading subject wav: %s', opts['<subject.wav>'])
    samplerate_subj, subj = read_wav_channel(opts['<subject.wav>'])
    logging.info('  sample rate: %d Hz', samplerate_subj)
    logging.info('  length: %f seconds; %d samples',
                 len(subj) / samplerate_subj, len(subj))

    assert samplerate_ref == samplerate_subj
    samplerate = samplerate_ref

    preprocess_algorithm = opts['--preprocess']
    logging.info("Preprocessing reference using '%s'", preprocess_algorithm)
    processed_ref = align_wav.preprocess(ref, preprocess_algorithm)
    logging.info("Preprocessing subject using '%s'", preprocess_algorithm)
    processed_subj = align_wav.preprocess(subj, preprocess_algorithm)

    # -- Cross-correlation ----------------------------------------------------
    if not analysis:
        logging.info('Running cross-correlation')
        correlate_args = {}
        if opts['--start']:
            correlate_args['subj_start'] = round(float(opts['--start']) * samplerate)
        if opts['--end']:
            correlate_args['subj_end'] = round(float(opts['--end']) * samplerate)
        if opts['--min-shift']:
            correlate_args['min_shift'] = round(float(opts['--min-shift']) * samplerate)
        if opts['--max-shift']:
            correlate_args['max_shift'] = round(float(opts['--max-shift']) * samplerate)

        analysis, corr = align_wav.cross_correlate(
            samplerate, processed_ref, processed_subj, **correlate_args)

        analysis['subject'] = os.path.abspath(opts['<subject.wav>'])
        analysis['reference'] = os.path.abspath(opts['<reference.wav>'])

        # -- Normalization --------------------------------------------------------
        if opts['--loudnorm']:
            logging.info('Running loudnorm analysis')
            analysis['loudnorm'] = loudnorm.loudnorm_analysis(opts['<subject.wav>'], analysis['trim_seconds'])

    # -- Output ---------------------------------------------------------------
        if opts['--plot']:
            analysis['plot'] = os.path.abspath(opts['--plot'])
            logging.info('Writing analysis plot: %s', opts['--plot'])
            plotter = plot.Plotter(samplerate, processed_ref, processed_subj, corr, analysis)
            fig = plotter.make_plot(opts)
            plotter.save_plot(fig, opts['--plot'])

    if opts['--output']:
        filename = os.path.abspath(opts['--output'])
        logging.info('Aligning subject wav')
        aligned = write_aligned_wav(subj, analysis)
        logging.info('Writing aligned wav to: %s', filename)
        wav.write(filename, samplerate, aligned)
        analysis['output'] = filename
        if opts['--loudnorm']:
            logging.info('Normalizing output')
            loudnorm.apply_loudnorm(filename, analysis['loudnorm'])

    if opts['--json']:
        print(json.dumps(analysis))
    else:
        logging.info(json.dumps(analysis))
        print(analysis['correlation_shift_seconds'])

def parse_cli():
    opts = docopt(__doc__)
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s %(asctime)s [%(filename)s:%(lineno)s] %(message)s')

    preprocess_algorithms = [k for k in align_wav.Preprocessor.__dict__ if not k.startswith('_')]
    if opts['--preprocess'] not in preprocess_algorithms:
        raise RuntimeError(f'--preprocess must be one of {preprocess_algorithms}')

    if opts.get('--plot-size'):
        opts['plot-size'] = [float(x) for x in opts['--plot-size'].split(',')]

    analysis = None
    if opts['--analysis']:
        with open(opts['--analysis']) as f:
            analysis = json.load(f)
        opts['--plot'] = opts['--plot'] or analysis['plot']
        opts['--output'] = opts['--output'] or analysis['output']
        opts['<subject.wav>'] = opts['<subject.wav>'] or analysis['subject']
        opts['<reference.wav>'] = opts['<reference.wav>'] or analysis['reference']
        opts['--loudnorm'] = opts['--loudnorm'] or bool(analysis['loudnorm'])
    # logging.info(opts)
    opts['analysis'] = analysis
    return opts

if __name__ == '__main__':
    main(parse_cli())
