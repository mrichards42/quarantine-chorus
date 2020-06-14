import datetime
import re
import uuid

import funcy as F
from marshmallow import Schema, fields, validate, pre_load, post_load

from . import config

CONTENT_TYPE_RE = "video/.*|audio/.*"

AUDIO_EXTENSIONS = (
    'aac',
    'flac',
    'm4a',
    'mp3',
    'mp4',
    'oga',
    'ogg',
    'opus',
    'ts',
    'wav',
    'weba',
)
VIDEO_EXTENSIONS = (
    '3g2',
    '3gp',
    'avi',
    'flv'
    'mkv',
    'mov',
    'mp4',
    'mpeg',
    'ogv',
    'webm',
)
FILENAME_RE = '.*[.](' + '|'.join(AUDIO_EXTENSIONS + VIDEO_EXTENSIONS) + ')'
MB = 1024 * 1024
FILE_SIZE = 1024 * MB
PARTS = ('bass', 'alto', 'tenor', 'treble')
SONG_RE = '[A-Za-z]{,3}\d{1,3}[tb]?'


def sanitize_filename(filename):
    return re.sub(r'[^a-zA-Z0-9_.]', '', filename)


def object_name(submission, extension):
    name_parts = F.flatten((
        # Parts
        submission['parts'],
        # Names
        ['.'.join(s.get('name', '').split()) for s in submission['singers']],
        # Location
        F.keep(submission.get('location', {}).get, ('city', 'state', 'country'))
    ))
    return '/'.join(F.map(sanitize_filename, (
        submission['singing'],
        submission['song'],
        # attach a uuid to the file name so that we never clobber uploads
        '_'.join(filter(None, name_parts)) + '.' + str(uuid.uuid4()) + extension
    )))


class RealDateTime(fields.DateTime):
    """Like fields.DateTime, but also accepts datetime.datetime objects"""
    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, datetime.datetime):
            return value
        return super()._deserialize(value, attr, data, **kwargs)


class SingerSchema(Schema):
    name = fields.Str()
    email = fields.Str()
    part = fields.Str(required=True, validate=validate.OneOf(PARTS))

    @pre_load
    def normalize_part(self, in_data, **kwargs):
        if 'part' in in_data:
            in_data['part'] = in_data['part'].lower()
        return in_data


class LocationSchema(Schema):
    city = fields.Str()
    state = fields.Str()
    country = fields.Str()


class SubmissionSchema(Schema):
    # required fields
    singing = fields.Str(required=True, validate=validate.Length(min=1))
    song = fields.Str(required=True, validate=validate.Regexp(SONG_RE))
    singers = fields.List(fields.Nested(SingerSchema), required=True,
                          validate=validate.Length(min=1))
    # optional fields
    location = fields.Nested(LocationSchema)
    reference = fields.Bool()
    # fields required in firestore but not in upload
    object_url = fields.Str(validate=validate.Regexp("gs://.+/.+"))
    parts = fields.List(fields.Str(validate=validate.OneOf(PARTS)))
    created = RealDateTime()

    @post_load
    def normalize_data(self, data, **kwargs):
        # Normalize strings
        data['singing'] = data['singing'].lower()
        data['song'] = data['song'].lower()
        # Compute parts
        if not data.get('parts'):
            data['parts'] = sorted(set(s.get('part') for s in data['singers']))
        return data


class UploadRequest(Schema):
    submission = fields.Nested(SubmissionSchema, required=True)
    filename = fields.Str(required=True)
    content_type = fields.Str(required=True, validate=validate.Regexp(CONTENT_TYPE_RE))
    content_length = fields.Int(required=True, validate=validate.Range(0, FILE_SIZE))

    @post_load
    def normalize_data(self, data, **kwargs):
        # Compute an object url
        submission = data['submission']
        if not submission.get('object_url'):
            m = re.search(r'[.][^/.]+$', data['filename'])
            extension = m.group() if m else ''
            name = object_name(submission, extension)
            submission['object_url'] = f'gs://{config.UPLOAD_BUCKET}/{name}'
        return data
