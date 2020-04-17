import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import firestore
from google.cloud import storage

import impl

storage_client = storage.Client()
db = firestore.Client()

UPLOAD_BUCKET = os.environ['UPLOAD_BUCKET']
SUBMISSIONS_COLLECTION = os.environ['SUBMISSIONS_COLLECTION']

logging.basicConfig(level=logging.INFO)

def upload_media(request):
    """Initiates a media upload.

    Request should include:

    * content_type
    * content_length
    * filename
    * submission
        * singing
        * song
        * participants (list of names and parts)
        * location (city, state, country)
        * master (true for the master recording for a given part)

    Submission data will be stored in a firebase database.

    Returns a url that can be used to start a resumable cloud storage upload.
    """
    # Parse the request
    data = impl.parse_upload_request(request)
    submission = data['submission']

    # Build the storage object url
    extension = Path(data['filename']).suffix
    object_name = impl.object_name(submission, extension)
    object_url = f'gs://{UPLOAD_BUCKET}/{object_name}'
    logging.info('Creating firestore document')

    # Create the firestore document
    ref = db.collection(SUBMISSIONS_COLLECTION).document(object_name)
    ref.set(impl.firestore_document(submission, object_url))

    # Create and return a resumable upload URL for the bucket
    logging.info('Creating upload request for %s', object_url)
    bucket = storage_client.bucket(UPLOAD_BUCKET)
    blob = bucket.blob(object_name)

    url = blob.create_resumable_upload_session(
        content_type=data['content_type'],
        size=data['content_length'],
        origin=request.headers.get('origin')
    )