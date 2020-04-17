import funcy as F
from datetime import datetime

import flask
import marshmallow

import schema

def participant_parts(submission):
    return sorted(set(p.get('part') for p in submission['participants']))

def object_name(submission, extension):
    participants = submission['participants']
    name_parts = F.flatten((
        # Song
        submission['singing'],
        submission['song'],
        # Parts
        participant_parts(submission),
        # Names
        ['.'.join(F.keep(p.get, ('first_name', 'last_Name'))) for p in participants],
        # Location
        F.keep(submission.get('location', {}).get, ('city', 'state', 'country'))
    ))
    return '_'.join(filter(None, name_parts)) + extension

DOC_KEYS = ('singing', 'song', 'participants', 'location', 'master')

def firestore_document(submission, object_url):
    doc = F.project(submission, DOC_KEYS)
    doc.update({
        'parts': participant_parts(submission),
        'object_url': object_url,
        'created': datetime.now(),
    })
    # validate before we send this to firestore, just in case
    return schema.SubmissionSchema().load(doc)

def _error(data, code):
    flask.abort(flask.Response(
        response=flask.json.dumps(data),
        status=code,
        mimetype='application/json'
    ))

def parse_upload_request(request):
    if request.method != 'POST':
        _error({"error": f"{request.method} not allowed"}, 405)
    try:
        return schema.UploadRequest().load(request.get_json(silent=True) or request.args)
    except marshmallow.exceptions.ValidationError as e:
        _error({"error": "Bad request",
                "messages": e.messages},
               400)
