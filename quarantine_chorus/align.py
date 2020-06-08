"""Align wav data using cross-correlation (aka the fun part)"""

import logging

import numpy as np
import scipy.signal as signal


def _array_or_read_wav(array_or_filename, samplerate):
    if isinstance(array_or_filename, np.ndarray):
        return array_or_filename
    elif isinstance(array_or_filename, str):
        logging.info("Extracting pcm data from %s", array_or_filename)
        from .ffmpeg import wav
        return wav.read_wav(array_or_filename, samplerate)
    else:
        raise ValueError("Expected a numpy array or a file name but got "
                         + type(array_or_filename))


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
        # This is a bit more verbose than this one-liner:
        #
        #   return np.clip(self.wav - cutoff, 0, 1) * max_sample
        #
        # ... but it does everything in-place (after the first copy), which saves some
        # memory
        if True:
            normalized = self.wav - cutoff
            np.clip(normalized, 0, 1, out=normalized)
            normalized *= int(max_sample)
            return normalized
        else:
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


def cross_correlate(reference, subject, samplerate, **kwargs):
    """Runs a cross-correlation analysis, returning (analysis_map, correlation_data)

    `reference` and `subject` may be numpy 1-d arrays of samples, or audio filenames.

    kwargs:

    - min_shift   start of the correlation shift window (samples)
    - max_shift   end of the correlation shift window (samples)
    - preprocess  preprocessing algorithm

    Returned analysis keys:

    - correlation_start       offset of first sample in correlation (usually negative)
    - correlation_end         offset of last sample in correlation (usually positive)
    - correlation_shift       samples to shift subj_wav (negative: trim; positive: pad)
    - correlation_window_min  calculated min_shift window
    - correlation_window_max  calculated max_shift window
    - trim                    samples to trim from the beginning of subj_wav
    - pad                     samples to add to the beginning of subj_wav

    Note: the above analysis values are in samples; the analysis also returns
    values converted to seconds. These keys have a `_seconds` suffix.
    """
    # Read wav files and preprocess
    ref_wav = _array_or_read_wav(reference, samplerate)
    subj_wav = _array_or_read_wav(subject, samplerate)
    preprocess_algorithm = kwargs.get('preprocess')
    if preprocess_algorithm:
        logging.info('Preprocessing wav data using %s', preprocess_algorithm)
        ref_wav = preprocess(ref_wav, preprocess_algorithm)
        subj_wav = preprocess(subj_wav, preprocess_algorithm)
    # return {}

    # Clamp shift window
    min_shift = kwargs.get('min_shift') or int(-len(subj_wav) / 2)
    max_shift = kwargs.get('max_shift') or int(len(subj_wav) / 2)

    # The following discussion uses `f` and `g` to discuss the two input
    # signals. In our case, `f` is the reference, and `g` is the subject
    # Cross-correlation can be computed using convolution if you reverse `g`
    # https://en.wikipedia.org/wiki/Cross-correlation
    corr = signal.fftconvolve(ref_wav, subj_wav[::-1], mode='full')

    # This would also work, except that we want to correlate using fft
    # corr = signal.correlate(data1, data2, mode='full')

    # This is how Praat explains cross-correlation offsets:
    # http://www.fon.hum.uva.nl/praat/manual/Sounds__Cross-correlate___.html
    # The start time of the resulting Sound will be the start time of `f` minus
    # the end time of `g`, the end time of the resulting Sound will be the end
    # time of `f` minus the start time of `g`, the time of the first sample of
    # the resulting Sound will be the first sample of `f` minus the last sample
    # of `g`, the time of the last sample of the resulting Sound will be the
    # last sample of `f` minus the first sample of `g`, and the number of
    # samples in the resulting Sound will be the sum of the numbers of samples
    # of `f` and `g` minus 1.
    ref_start, ref_end = 0, len(ref_wav)
    subj_start, subj_end = 0, len(subj_wav)
    corr_start = ref_start - subj_end
    corr_end = ref_end - subj_start

    # Find the best correlation point (highest value)
    corr_zero = -corr_start  # the location of no shift
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
