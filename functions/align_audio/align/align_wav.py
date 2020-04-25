"""Align wav data using cross-correlation (aka the fun part)"""

import logging

import scipy.signal as signal
import numpy as np

from . import util

class Preprocessor:
    """Simple preprocessing algorithms

    Algorithms:

    - none: no-op
    - loudness: Selects samples in the loudest N percentile. Everything below
      the cutoff is silenced; everything above the cutoff is set to max gain.
    """
    def __init__(self, wav):
        self.wav = wav

    def none(self):
        return self.wav

    def _loudness(self, ratio):
        # Some files have fleeting very loud pops. Instead of the maximum,
        # let's take a very high percentile, and hopefully that knocks off the
        # extreme outliers
        max_sample = np.percentile(self.wav, 99.5)
        cutoff = int(ratio * max_sample)
        return np.clip(self.wav - cutoff, 0, 1) * max_sample

    def loudness_25(self):
        """Selects the 25th percentile of samples (i.e. the loudest 75%)"""
        return self._loudness(0.25)

    def loudness_50(self):
        """Selects the 50th percentile of samples (i.e. the loudest 50%)"""
        return self._loudness(0.5)

    def loudness_75(self):
        """Selects the 75th percentile of samples (i.e. the loudest 25%)"""
        return self._loudness(0.75)

def preprocess(wav_data, algorithm):
    """Processes a wav file before running cross-correlation."""
    return getattr(Preprocessor(wav_data), algorithm)()

def cross_correlate(samplerate, ref_wav, subj_wav, **kwargs):
    """Runs a cross-correlation analysis, returning (analysis_map, correlation_data)

    kwargs:

    - min_shift   start of the correlation shift window (samples)
    - max_shift   end of the correlation shift window (samples)
    - silence     calculate shift window based on silent samples (threshold)
    - subj_start  trim start of subject wav (samples)
    - subj_end    trim end of subject wav (samples)

    Returned analysis keys:

    - correlation_start       offset of the first sample in correlation (usually negative)
    - correlation_end         offset of last sample in correlation (usually positive)
    - correlation_shift       samples to shift subj_wav (negative: trim; positive: pad)
    - correlation_window_min  calculated min_shift window
    - correlation_window_max  calculated max_shift window
    - trim                    samples to trim from the beginning of subj_wav
    - pad                     samples to add to the beginning of subj_wav

    Note: the above analysis values are in samples; the analysis also returns
    values converted to seconds. These keys have a `_seconds` suffix.
    """
    # -- Calculate shift window -----------------------------------------------
    min_shift = kwargs.get('min_shift')
    max_shift = kwargs.get('max_shift')
    if ('min_shift' not in kwargs or 'max_shift' not in kwargs) and 'silence' in kwargs:
        # Find the quiet parts of the reference wav
        ref_quiet_start = util.quiet_count(ref_wav, kwargs['silence'])
        ref_quiet_end = util.quiet_count(ref_wav[::-1], kwargs['silence'])
        logging.info('Ignoring silence at beginning and end of reference')
        logging.info('  beginning silence: %f seconds; %d samples', ref_quiet_start / samplerate, ref_quiet_start)
        logging.info('  ending silence: %f seconds; %d samples', ref_quiet_end / samplerate, ref_quiet_end)
        logging.info('  length without silence: %f seconds; %d samples',
                     (len(ref_wav) - ref_quiet_start - ref_quiet_end) / samplerate,
                     len(ref_wav) - ref_quiet_start - ref_quiet_end)
        # Assuming that the subject audio must fit within the non-silent part
        # of the reference audio, we can exclude the part of the correlation
        # that is outside the reasonable shift bounds
        # Examples:
        #  1. reference is 10 seconds. subject is 15 seconds. It can only make
        #     sense to shift the subject +/- 5 seconds
        #  2. reference is 10 seconds; subject is 50 seconds. It can only make
        #     sense to shift the subject +/- 40 seconds (in this case the
        #     subject probably has a lot of silence, but we don't know where)
        #  3. reference is 50 seconds; subject is 20 seconds. It can only make
        #     sense to shift the subject +/- 30 seconds (in this case the
        #     subject is only a subset of the reference, but we don't know
        #     which part)
        shift_range = [ref_quiet_start, len(ref_wav) - len(subj_wav) - ref_quiet_end]
        min_shift = min(shift_range) - 1 * samplerate # add an extra second of slop
        max_shift = max(shift_range) + 1 * samplerate # to either end
    else:
        # Allow shifting up to half the subject duration in either direction
        min_shift = int(-len(subj_wav) / 2)
        max_shift = int(len(subj_wav) / 2)

    # -- Trim subject wav -----------------------------------------------------
    subj_start = kwargs.get('subj_start', 0)
    subj_end = kwargs.get('subj_end', len(subj_wav))
    # adjust negative offsets (these would work as-is for slicing, but they
    # would mess up the calculations below)
    if subj_start < 0:
        subj_start += len(subj_wav)
    if subj_end < 0:
        subj_end += len(subj_wav)
    if 'subj_start' in kwargs or 'subj_end' in kwargs:
        logging.info('Trimming subject wav to:')
        logging.info('  start: %f seconds; %d samples', subj_start / samplerate, subj_start)
        logging.info('  end: %f seconds; %d samples', subj_end / samplerate, subj_end)
        logging.info('  length: %f seconds; %d samples',
                     (subj_end - subj_start) / samplerate,
                     subj_end - subj_start)
    sample_wav = subj_wav[subj_start:subj_end]

    # -- Cross-correlation ----------------------------------------------------
    # The following discussion uses `f` and `g` to discuss the two input
    # signals. In our case, `f` is the reference, and `g` is the subject
    # Cross-correlation can be computed using convolution if you reverse `g`
    # https://en.wikipedia.org/wiki/Cross-correlation
    corr = signal.fftconvolve(ref_wav, sample_wav[::-1], mode='full')

    # This would also work, except that we want to correlate using fft
    # corr = signal.correlate(data1, data2, mode='full')

    ## This is how Praat explains cross-correlation offsets:
    # http://www.fon.hum.uva.nl/praat/manual/Sounds__Cross-correlate___.html
    # The start time of the resulting Sound will be the start time of `f` minus
    # the end time of `g`, the end time of the resulting Sound will be the end
    # time of `f` minus the start time of `g`, the time of the first sample of
    # the resulting Sound will be the first sample of `f` minus the last sample
    # of `g`, the time of the last sample of the resulting Sound will be the
    # last sample of `f` minus the first sample of `g`, and the number of
    # samples in the resulting Sound will be the sum of the numbers of samples
    # of `f` and `g` minus 1.
    corr_start = 0 - subj_end
    corr_end = len(ref_wav) - subj_start

    # Find the best correlation point (highest value)
    corr_zero = -corr_start # the location of no shift
    corr_slice = corr[corr_zero + min_shift:corr_zero + max_shift]
    logging.info('Clamping shift to between %f and %f seconds; %d and %d samples',
                 min_shift / samplerate, max_shift / samplerate,
                 min_shift, max_shift)
    corr_best_index = int(np.argmax(np.abs(corr_slice)))
    corr_best = abs(corr_slice[corr_best_index])
    corr_shift = corr_best_index + min_shift
    logging.info('Best shift: %f seconds; %d samples',
                 corr_shift / samplerate, corr_shift)

    analysis = {
        'correlation_start': corr_start,
        'correlation_end': corr_end,
        'correlation_shift': corr_shift,
        'correlation_window_min': min_shift,
        'correlation_window_max': max_shift,
        'trim': -corr_shift if corr_shift < 0 else 0,
        'pad': corr_shift if corr_shift > 0 else 0,
    }
    for k, v in list(analysis.items()):
        analysis[k + '_seconds'] = v / samplerate
    return analysis, corr / corr_best
