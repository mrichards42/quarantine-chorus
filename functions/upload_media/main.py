import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import storage

storage_client = storage.Client()
UPLOAD_BUCKET = os.environ['UPLOAD_BUCKET']

logging.basicConfig(level=logging.INFO)

def object_name(data, timestamp, extension):
    meta = data['metadata']
    parts = (
        [meta.get(x) for x in ('song', 'part')] +
        meta['names'] +
        [meta.get('location').get(x) for x in ('city', 'state', 'county')]
    )
    return '_'.join(filter(None, parts)) + '.' + timestamp + extension

def upload_media(request):
    """Initiates a media upload.

    Request should include:

    * content-type
    * content-length
    * filename
    * metadata
        * song
        * names (list of people involved)
        * part (bass, alto, tenor, treble)
        * location
            * city
            * state
            * country
        * additional metadata is allowed

    Metadata will be stored in a firebase database.

    Returns a url that can be used to start a resumable cloud storage upload.
    """
    # TODO: swagger spec? for now, just assume the data is good
    data = request.get_json(silent=True) or request.args
    logging.info('Received request with data: %s', data)

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
    extension = Path(data['filename']).suffix
    name = object_name(data, timestamp, extension)
    logging.info('Creating upload request for object %s', name)

    bucket = storage_client.bucket(UPLOAD_BUCKET)
    blob = bucket.blob(name)

    return blob.create_resumable_upload_session(
        content_type=data['content-type'],
        size=data['content-length'],
        origin=request.headers.get('origin')
    )
