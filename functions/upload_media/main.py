import logging

import flask
import marshmallow

from quarantine_chorus import schema
from quarantine_chorus.submission import Submission

logging.basicConfig(level=logging.DEBUG)


def json_error(data, status_code):
    return flask.Response(
        response=flask.json.dumps(data),
        status=status_code,
        mimetype='application/json'
    )


def log_error_response(request, response):
    logging.warning("Bad request with data: %r; returning error response: %s %r",
                    request.data or request.args,
                    response.status,
                    response.data)


def parse_request(request):
    if request.method != 'POST':
        return json_error({"error": f"{request.method} not allowed"}, 405)
    try:
        data = request.get_json(silent=True) or request.args
        return schema.UploadRequest().load(data)
    except marshmallow.exceptions.ValidationError as e:
        return json_error({"error": "Bad request", "messages": e.messages}, 400)


def main(request):
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
        * reference (true for the reference recording for a given part)
        * comment (free text)

    Submission data will be stored in a firebase database.

    Returns a url that can be used to start a resumable cloud storage upload.
    """
    # Parse the request into a Submission object
    data = parse_request(request)
    if isinstance(data, flask.Response):
        log_error_response(request, data)
        return data

    submission = Submission.from_gcs_url(data['submission']['object_url'])

    # Create the firestore document
    logging.info('Creating firestore document')
    submission.firestore_document().set(data['submission'])

    # Create and return a resumable upload URL for the bucket
    logging.info('Creating upload request for %s', submission.video_upload.url)
    url = submission.video_upload.create_resumable_upload_session(
        content_type=data['content_type'],
        size=data['content_length'],
        origin=request.headers.get('origin')
    )

    return flask.json.jsonify({"upload_url": url})
