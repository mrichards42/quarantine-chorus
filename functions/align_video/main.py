import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

from google.cloud import firestore
from google.cloud import storage

storage_client = storage.Client()
db = firestore.Client()

UPLOAD_BUCKET = os.environ['UPLOAD_BUCKET']
ALIGNED_VIDEO_BUCKET = os.environ['ALIGNED_VIDEO_BUCKET']
SUBMISSIONS_COLLECTION = os.environ['SUBMISSIONS_COLLECTION']

# config
FFMPEG = os.environ.get('FFMPEG', 'ffmpeg-static/ffmpeg-4.2.2-amd64-static/ffmpeg')
SAMPLERATE = 48000
VIDEO_SCALE = '-2:360'

logging.basicConfig(level=logging.INFO)

def gcs_url(bucket, object_name):
    return f'gs://{bucket}/{object_name}'

def get_analysis_data(original_name):
    ref = db.collection(SUBMISSIONS_COLLECTION).document(original_name)
    snapshot = ref.get(['analysis'])
    return snapshot.get('analysis')

def original_video_blob(original_name):
    bucket = storage_client.bucket(UPLOAD_BUCKET)
    return bucket.get_blob(original_name)

def crop_detect(filename):
    cmd = [FFMPEG, '-y',
           '-ss', '20', '-t', '1', # analyze just 1 second, 20 seconds into the video
           '-i', filename,
           '-vf', 'cropdetect=round=2',
           '-f', 'null', '-']
    proc = subprocess.run(cmd,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          check=True)
    for line in proc.stderr.splitlines():
        m = re.search(r'x1:(\S+).*y1:(\S+).*w:(\S+).*h:(\S+)', line.decode())
        if m:
            return f'x={m.group(1)}:y={m.group(2)}:w={m.group(3)}:h={m.group(4)}'

def ffmpeg_filter_args(analysis, crop):
    vf = []
    af = []

    # extract shift
    pad_ms = round(analysis['pad_seconds'] * 1000)
    trim_ms = round(analysis['trim_seconds'] * 1000)
    pad_s = '%0.3f' % analysis['pad_seconds']
    trim_s = '%0.3f' % analysis['trim_seconds']

    # realign audio
    af.append(f'aresample={SAMPLERATE}:first_pts=0')

    # resize video
    vf.append(f'crop={crop}')
    vf.append(f'scale={VIDEO_SCALE}')

    # pad or trim video and audio
    if pad_ms > 0:
        # TODO: we're working with ffmpeg 3.6.0, and tpad was added in 4.2
        vf.append(f'tpad=start_mode=add:start_duration={pad_s}')
        af.append(f'adelay={pad_ms}|{pad_ms}')
    elif trim_ms > 0:
        vf.append(f'trim={trim_s}')
        af.append(f'atrim={trim_s}')
        # trim and atrim mess with pts, so we have to reset them to 0 here; for
        # some reason tpad and delay don't?
        vf.append('setpts=PTS-STARTPTS')
        af.append('asetpts=PTS-STARTPTS')

    # copied from align_audio
    af.append((
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
    ).format(**analysis['loudnorm']))

    # loudnorm upsamples to 192k; set the expected samplerate here
    af.append(f'aresample={SAMPLERATE}:first_pts=0')

    if not crop or '-' in crop:
        # negative crop means no video
        return ['-vn', '-af', ','.join(af), '-ac', '1']
    else:
        return ['-vf', ','.join(vf), '-af', ','.join(af), '-ac', '1']


## MAIN
def align_video(data, context):
    # Get alignment data
    object_name = data['name']
    original_name = str(Path(object_name).with_suffix(''))
    analysis = get_analysis_data(original_name)
    if not analysis:
        logging.warning('Analysis data %s does not exist! Aborting.', original_name)
        return

    # Get original file
    blob = original_video_blob(original_name)
    if not blob:
        logging.warning('Original file %s does not exist! Aborting.',
                        gcs_url(UPLOAD_BUCKET, original_name))
        return

    _, temp_video = tempfile.mkstemp(Path(blob.name).suffix)
    _, temp_out = tempfile.mkstemp('.mp4')
    try:
        # Download files
        logging.info('Downloading original file %s',
                     gcs_url(blob.bucket.name, blob.name))
        blob.download_to_filename(temp_video)
        logging.info('Detecting crop size')
        crop = crop_detect(temp_video)
        logging.info('Aligning and resizing video')
        cmd = ([FFMPEG, '-y', '-i', temp_video]
               + ffmpeg_filter_args(analysis, crop)
               # allow re-encoding on the fly
               + ['-movflags', '+faststart']
               + [temp_out])
        logging.info('Executing ffmpeg with args %s', cmd)
        subprocess.run(cmd,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       check=True)
        # Upload
        logging.info('Uploading to %s',
                     gcs_url(ALIGNED_VIDEO_BUCKET, blob.name + '.mp4'))
        bucket = storage_client.bucket(ALIGNED_VIDEO_BUCKET)
        bucket.blob(blob.name + '.mp4').upload_from_filename(temp_out)
    except subprocess.CalledProcessError as err:
        logging.error('ffmpeg failure: %d', err.returncode)
        logging.error('cmd: %s', err.cmd)
        logging.error('stdout: %s', err.stdout)
        logging.error('stderr: %s', err.stderr)
    finally:
        os.remove(temp_video)
        os.remove(temp_out)
