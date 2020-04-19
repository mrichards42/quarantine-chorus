import logging
import os
import subprocess
import tempfile
from pathlib import Path

from google.cloud import storage

storage_client = storage.Client()

UPLOAD_BUCKET = os.environ['UPLOAD_BUCKET']
AUDIO_BUCKET = os.environ['AUDIO_BUCKET']

logging.basicConfig(level=logging.INFO)

def extract_audio(data, context):
    url = f"gs://{data['bucket']}/{data['name']}"
    blob = storage_client.bucket(data['bucket']).get_blob(data['name'])

    if not blob:
        logging.warning('Blob %s does not exist! Aborting.', url)
        return

    _, temp1 = tempfile.mkstemp(Path(data['name']).suffix)
    _, temp2 = tempfile.mkstemp('.m4a')
    try:
        logging.info('Downloading %s', url)
        # TODO: streaming download piped to ffmpeg?
        blob.download_to_filename(temp1)
        # encode to aac
        logging.info('Extracting audio to %s', temp2)
        subprocess.run(['ffmpeg', '-y',
                        '-i', temp1,
                        '-vn',
                        '-c:a', 'aac',
                        '-b:a', '128k',
                        '-af', 'aresample=44100:first_pts=0',
                        '-ac', '1',
                        temp2],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       check=True)
        logging.info('Uploading to %s', f'gs://{AUDIO_BUCKET}/{data["name"]}.m4a')
        audio_bucket = storage_client.bucket(AUDIO_BUCKET)
        audio_bucket.blob(data['name'] + '.m4a').upload_from_filename(temp2)
    except subprocess.CalledProcessError as err:
        logging.error('ffmpeg failure: %d', err.returncode)
        logging.error('cmd: %s', err.cmd)
        logging.error('stdout: %s', err.stdout)
        logging.error('stderr: %s', err.stderr)
    finally:
        os.remove(temp1)
        os.remove(temp2)
