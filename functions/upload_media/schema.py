import datetime
from marshmallow import Schema, fields, pprint, validate, pre_load

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

class ParticipantSchema(Schema):
    first_name = fields.Str()
    last_name = fields.Str()
    part = fields.Str(required=True, validate=validate.OneOf(PARTS))

class LocationSchema(Schema):
    city = fields.Str()
    state = fields.Str()
    country = fields.Str()

class SubmissionSchema(Schema):
    # required fields
    singing = fields.Str(required=True)
    song = fields.Str(required=True)
    participants = fields.List(fields.Nested(ParticipantSchema), required=True,
                               validate=validate.Length(min=1))
    # optional fields
    location = fields.Nested(LocationSchema)
    master = fields.Bool()
    # fields required in firestore but not in upload
    object_url = fields.Str(validate=validate.Regexp("gs://.+/.+"))
    parts = fields.List(fields.Str(validate=validate.OneOf(PARTS)))
    created = RealDateTime()

class UploadRequest(Schema):
    submission = fields.Nested(SubmissionSchema, required=True)
    filename = fields.Str(required=True, validate=validate.Regexp(FILENAME_RE))
    content_type = fields.Str(required=True, validate=validate.Regexp(CONTENT_TYPE_RE))
    content_length = fields.Int(required=True, validate=validate.Range(0, MAX_FILE_SIZE))
