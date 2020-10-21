"""Align Video Cloud Function"""

import logging
import os
from tempfile import TemporaryDirectory

from quarantine_chorus import ffmpeg
from quarantine_chorus.decorators import log_return
from quarantine_chorus.submission import Submission

logging.basicConfig(level=logging.DEBUG)

ffmpeg.EXECUTABLE = os.environ.get('FFMPEG', 'ffmpeg')
if ffmpeg.EXECUTABLE != 'ffmpeg':
    ffmpeg.EXECUTABLE = os.path.abspath(ffmpeg.EXECUTABLE)


def write_aligned_video(in_file, out_file, analysis, cfg):
    stream = ffmpeg.input(in_file)

    # Video filters
    if ffmpeg.probe(in_file).video:
        video = stream.video
        # Detect crop at 20 seconds into the video
        crop = ffmpeg.run_cropdetect(in_file, ss=20)
        if crop:
            video = video.crop(**crop)
        if cfg.get('resize'):
            video = video.scale(**cfg['resize'])
        video = video.align_video(analysis)
    else:
        video = None

    # Audio filters
    audio = stream.audio
    audio = audio.align_audio(analysis)
    if analysis.get('loudnorm'):
        audio = audio.loudnorm(analysis['loudnorm'], resample=cfg.get('samplerate'))
    elif cfg.get('samplerate'):
        audio = audio.resample(cfg.get('samplerate'))

    # Output
    output_args = {}
    if cfg.get('framerate'):
        output_args['r'] = cfg.get('framerate')
    output_args['movflags'] = '+faststart'  # allow re-encoding on the fly
    output_args['ac'] = 1
    streams = [audio, video] if video else [audio]
    return ffmpeg.output(*streams, out_file, **output_args).run(overwrite_output=True)


@log_return(level=logging.WARNING)
def main(data, context):
    submission = Submission.from_bucket_trigger(data, context)

    # Find the video and analysis data
    video = submission.video_upload
    if not video.exists():
        return f"Blob {video.url} does not exist!"

    analysis = submission.get_firestore_data('analysis')
    if not analysis:
        return f"Unable to find analysis data for {video.url}"

    # Load config
    video_cfg = submission.song_config()['video']
    if not video_cfg['loudnorm']:
        analysis.pop('loudnorm', None)

    with TemporaryDirectory() as tempdir:
        os.chdir(tempdir)
        logging.info("In temp dir: %s", tempdir)

        # Download files
        logging.info("Downloading original video %s", video.url)
        video.download(video.filename)

        # Output
        out_file = 'tmp_' + video.filename
        write_aligned_video(video.filename, out_file, analysis, video_cfg)

        # Upload
        logging.info("Uploading to %s", submission.video_aligned.url)
        submission.video_aligned.upload(out_file)
