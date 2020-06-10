"""Align Audio Cloud Function"""

import logging
import os
from tempfile import TemporaryDirectory

import funcy as F

from quarantine_chorus import ffmpeg
from quarantine_chorus.submission import Submission
import quarantine_chorus.align as align

logging.basicConfig(level=logging.DEBUG)


# Turns out that cross-correlation is pretty expensive in terms of memory. Sample rate
# is directly correlated with how much memory the cross-correlation uses, so rather
# than picking a normal sample rate for audio, we'll go with a lower rate to keep
# memory usage down. The loudness-based preprocessing algorithms aren't concerned with
# audio quality since they transform the audio into essentially a boolean (silent or
# not). I expect each time sample rate is cut in half we might lose a couple samples of
# accuracy in the final shift, but since we have to round the shift to milliseconds for
# ffmpeg anyways, it shouldn't make any difference in practice.
ANALYSIS_SAMPLERATE = 24000


def loudnorm_analysis(subj_file, singer_count, cfg):
    params = cfg if singer_count == 1 else cfg.get('multiple_singers', cfg)
    logging.info("Running loudnorm analysis for %d singer(s)", singer_count)
    return ffmpeg.run_loudnorm_analysis(subj_file, params)


def write_aligned_audio(in_file, out_file, analysis, cfg):
    audio = ffmpeg.input(in_file).audio.align_audio(analysis)
    if analysis.get('loudnorm'):
        audio = audio.loudnorm(analysis['loudnorm'],
                               resample=cfg.get('samplerate', 48000))
    return audio.output(out_file, ac=1).run(overwrite_output=True)


def main(data, context):
    submission = Submission.from_bucket_trigger(data, context)

    # Check required files
    audio = submission.audio_extracted
    if not audio.exists():
        return f"Blob {audio.url} does not exist!"

    reference = F.some(lambda x: x.exists(), submission.audio_reference_candidates())
    if not reference:
        urls = [c.url for c in submission.audio_reference_candidates()]
        return f"Unable to find reference audio! Tried {urls}"

    # Load config
    audio_cfg = submission.song_config()['audio']
    loudnorm_cfg = submission.song_config()['loudnorm']
    corr_cfg = submission.song_config()['correlation']

    with TemporaryDirectory() as tempdir:
        os.chdir(tempdir)
        logging.info("In temp dir: %s", tempdir)

        # Download files
        logging.info("Downloading subject %s", audio.url)
        audio.download(audio.filename)
        logging.info("Downloading reference %s", reference.url)
        reference.download(reference.filename)

        # Process
        analysis, _ = align.cross_correlate(
            reference.filename,
            audio.filename,
            samplerate=corr_cfg.get('samplerate', ANALYSIS_SAMPLERATE),
            preprocess=corr_cfg.get('preprocess')
        )
        if audio_cfg['loudnorm']:
            analysis['loudnorm'] = loudnorm_analysis(audio.filename,
                                                     submission.singer_count(),
                                                     loudnorm_cfg)

        # Update firestore
        logging.info('Saving analysis data to firestore')
        submission.firestore_document().set({'analysis': analysis}, merge=True)

        # Output
        out_file = 'tmp_' + audio.filename
        write_aligned_audio(audio.filename, out_file, analysis, audio_cfg)

        # Upload
        logging.info("Uploading to %s", submission.audio_aligned.url)
        submission.audio_aligned.upload(out_file)
