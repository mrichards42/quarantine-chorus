import funcy as F
from datetime import datetime

import flask
import marshmallow

import schema

def all_parts(submission):
    return sorted(set(s.get('part') for s in submission['singers']))

def object_name(submission, extension):
    singers = submission['singers']
    name_parts = F.flatten((
        # Song
        submission['singing'],
        submission['song'],
        # Parts
        all_parts(submission),
        # Names
        ['.'.join(s.get('name', '').split()) for s in singers],
        # Location
        F.keep(submission.get('location', {}).get, ('city', 'state', 'country'))
    ))
    return '_'.join(filter(None, name_parts)) + extension

DOC_KEYS = ('singing', 'song', 'singers', 'location', 'master')

def firestore_document(submission, object_url):
    doc = F.project(submission, DOC_KEYS)
    doc.update({
        'parts': all_parts(submission),
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
