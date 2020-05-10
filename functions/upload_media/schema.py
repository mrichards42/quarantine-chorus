import datetime
from marshmallow import Schema, fields, pprint, validate, pre_load, post_load

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
MAX_FILE_SIZE = 500 * MB
PARTS = ('bass', 'alto', 'tenor', 'treble')

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
    singing = fields.Str(required=True)
    song = fields.Str(required=True)
    singers = fields.List(fields.Nested(SingerSchema), required=True,
                          validate=validate.Length(min=1))
    # optional fields
    location = fields.Nested(LocationSchema)
    comment = fields.Str()
    reference = fields.Bool()
    # fields required in firestore but not in upload
    object_url = fields.Str(validate=validate.Regexp("gs://.+/.+"))
    parts = fields.List(fields.Str(validate=validate.OneOf(PARTS)))
    created = RealDateTime()

    @post_load
    def normalize_data(self, in_data, **kwargs):
        in_data['singing'] = in_data['singing'].lower()
        in_data['song'] = in_data['song'].lower()
        return in_data

class UploadRequest(Schema):
    submission = fields.Nested(SubmissionSchema, required=True)
    filename = fields.Str(required=True)
    content_type = fields.Str(required=True, validate=validate.Regexp(CONTENT_TYPE_RE))
    content_length = fields.Int(required=True, validate=validate.Range(0, MAX_FILE_SIZE))
