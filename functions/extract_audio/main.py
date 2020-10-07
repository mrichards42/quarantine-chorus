"""Extract Audio Cloud Function"""

import logging
import os
from tempfile import TemporaryDirectory

from quarantine_chorus import ffmpeg
from quarantine_chorus.decorators import log_return
from quarantine_chorus.submission import Submission

logging.basicConfig(level=logging.DEBUG)


def extract_audio_to_file(in_file, out_file, cfg):
    return (
        ffmpeg.input(in_file)
        .audio
        .filter('aresample', cfg.get('samplerate', 48000), first_pts=0)
        .filter('asetpts', 'PTS-STARTPTS')
        .output(
            out_file,
            acodec=cfg.get('codec', 'aac'),
            audio_bitrate=cfg.get('bitrate', '128k'),
            ac=1,
        )
        .run(overwrite_output=True)
    )


@log_return(logging.WARNING)
def main(data, context):
    submission = Submission.from_bucket_trigger(data, context)
    video = submission.video_upload
    audio = submission.audio_extracted

    # Get the uploaded video
    if not video.exists():
        return f"Blob {video.url} does not exist!"

    with TemporaryDirectory() as tempdir:
        os.chdir(tempdir)
        logging.info('In temp dir: %s', tempdir)

        # A lot of video formats don't support piping (e.g. mp4), so while downloading
        # the whole file is inefficient, it's pretty much the only way to do it.
        logging.info("Downloading %s", video.url)
        video.download(video.filename)

        # Extract
        audio_cfg = submission.song_config()['audio']
        logging.info("Extracting audio to %s", audio.filename)
        extract_audio_to_file(video.filename, audio.filename, audio_cfg)

        # Upload reference audio files first (so they're available for align_audio
        # before the main file is uploaded).
        if submission.is_reference():
            logging.info("Reference submission: creating reference files.")
            for reference in submission.audio_reference_candidates():
                # Note: it would be more efficient to use bucket.copy_blob()
                # https://googleapis.dev/python/storage/latest/buckets.html#google.cloud.storage.bucket.Bucket.copy_blob
                # But it's nice to be able to run this using a LocalSubmission, and
                # we'd have to reimplement the copy function.
                logging.info("Uploading to %s", reference.url)
                reference.upload(audio.filename)

        logging.info("Uploading to %s", submission.audio_extracted.url)
        audio.upload(audio.filename)
