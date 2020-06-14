"""Access to google cloud resources for a submission.

Submissions are uniquely identified by '{singing}/{song}/{filename}'
"""

import re
from pathlib import Path

from . import config
from . import gcp


def _remove_suffix(s):
    return str(Path(s).with_suffix(''))


class _GCS:
    """A helper class for cloud storage objects."""
    def __init__(self, storage_client, bucket, name):
        self.storage_client = storage_client
        self.bucket_name = bucket
        self.name = name
        self._blob_cache = None

    URL_PREFIX = 'gs://'

    @property
    def url(self):
        """A formatted GCS url for this object."""
        return f'{self.URL_PREFIX}{self.bucket_name}/{self.name}'

    @property
    def filename(self):
        """The object's filename, without singing or song."""
        return self.name.split('/')[-1]

    @property
    def _bucket(self):
        """Returns a GCS bucket. Intended for internal use only."""
        return self.storage_client.bucket(self.bucket_name)

    @property
    def _blob(self):
        """Returns a GCS blob object. Intended for internal use only."""
        if self._blob_cache is None:
            self._blob_cache = self._bucket.blob(self.name)
        return self._blob_cache

    def exists(self):
        """Does a blob with this name exist?"""
        return self._blob.exists()

    def download(self, file_or_filename, **kwargs):
        """Downloads to an open file-like object or a filename."""
        if isinstance(file_or_filename, str):
            return self._blob.download_to_filename(file_or_filename, **kwargs)
        else:
            return self._blob.download_to_file(file_or_filename, **kwargs)

    def upload(self, file_or_filename, **kwargs):
        """Uploads from an open file-like object or a filename."""
        if isinstance(file_or_filename, str):
            return self._blob.upload_from_filename(file_or_filename, **kwargs)
        else:
            return self._blob.upload_from_file(file_or_filename, **kwargs)

    def create_resumable_upload_session(self, content_type, size, origin=None):
        """Creates and returns a resumable upload url.

        See: https://cloud.google.com/storage/docs/resumable-uploads
        """
        return self._blob.create_resumable_upload_session(content_type, size, origin)


class Submission:
    """A video/audio submission.

    Provides access to cloud storage and firestore resources associated with this
    submission, as well as configuration for the submission's song.
    """
    def __init__(self, singing, song, filename,
                 storage_client=None,
                 firestore_client=None):
        self.singing = singing
        self.song = song
        self.filename = filename
        self._storage_client = storage_client
        self._firestore_client = firestore_client
        self._firestore_data = None

    # -- Named constructors --

    @classmethod
    def from_gcs_url(cls, url, **kwargs):
        """Constructor taking a cloud storage url."""
        if url.startswith(_GCS.URL_PREFIX):
            bucket, name = url[len(_GCS.URL_PREFIX):].split('/', 1)
            return cls.from_gcs_object(bucket, name, **kwargs)
        raise ValueError(f"URL '{url}' does not start with {_GCS.URL_PREFIX}")

    @classmethod
    def from_gcs_object(cls, bucket, name, **kwargs):
        """Constructor taking a bucket and object name."""
        bucket_fns = {
            config.UPLOAD_BUCKET: cls.from_video_upload,
            config.AUDIO_EXTRACTED_BUCKET: cls.from_audio_extracted,
            config.AUDIO_ALIGNED_BUCKET: cls.from_audio_aligned,
            config.VIDEO_ALIGNED_BUCKET: cls.from_video_aligned,
        }
        f = bucket_fns.get(bucket)
        if f:
            return f(name, **kwargs)
        raise ValueError(f"Bucket '{bucket}' is not in {list(bucket_fns.keys())}")

    @classmethod
    def from_bucket_trigger(cls, data, context, **kwargs):
        """Constructor for cloud storage bucket triggers."""
        return cls.from_gcs_object(data['bucket'], data['name'], **kwargs)

    @classmethod
    def from_video_upload(cls, name, **kwargs):
        return cls(*name.split('/', 2), **kwargs)

    @classmethod
    def from_audio_extracted(cls, name, **kwargs):
        return cls.from_video_upload(_remove_suffix(name), **kwargs)

    @classmethod
    def from_audio_aligned(cls, name, **kwargs):
        return cls.from_video_upload(_remove_suffix(name), **kwargs)

    @classmethod
    def from_video_aligned(cls, name, **kwargs):
        return cls.from_video_upload(_remove_suffix(name), **kwargs)

    # -- Config --

    def song_config(self):
        """Returns the song config dict for this submission."""
        return config.song(self.singing, self.song)

    def audio_config(self):
        """Returns the audio config dict for this submission."""
        return self.song_config()['audio']

    def audio_extension(self):
        """Returns the extension for processed audio files."""
        return self.audio_config()['extension']

    def video_config(self):
        """Returns the video config dict for this submission."""
        return self.song_config()['video']

    def video_extension(self):
        """Returns the extension for processed video files."""
        return self.video_config()['extension']

    # -- Names --

    def name(self):
        """Returns the blob name"""
        return f'{self.singing}/{self.song}/{self.filename}'

    def video_upload_name(self):
        """Returns the video upload blob name."""
        return self.name()

    def audio_extracted_name(self):
        """Returns the audio extracted blob name."""
        return self.name() + '.' + self.audio_extension()

    def audio_aligned_name(self):
        """Returns the audio aligned blob name."""
        return self.name() + '.' + self.audio_extension()

    def video_aligned_name(self):
        """Returns the video aligned blob name."""
        return self.name() + '.' + self.video_extension()

    def audio_reference_names(self):
        """Returns a list of candidate reference audio blob names.

        Prefers a reference specific to this submission's parts, falling back to a
        generic reference for the song.
        """
        ext = self.audio_extension()
        part_str = '_'.join(self.parts())
        return [
            f'{self.singing}/{self.song}/lead_{part_str}.{ext}',
            f'{self.singing}/{self.song}/lead.{ext}'
        ]

    # -- google cloud clients --

    GCP = gcp.GCP

    def storage_client(self):
        return self._storage_client or self.GCP.storage_client

    def firestore_client(self):
        return self._firestore_client or self.GCP.firestore_client

    # -- Firestore --

    def firestore_document(self):
        """Returns the firestore document for this submission."""
        return (
            self.firestore_client()
            .document(config.SUBMISSIONS_COLLECTION, self.name())
        )

    def firestore_data(self, refresh=False):
        """Returns the data from a firestore document."""
        if refresh or not self._firestore_data:
            self._firestore_data = self.firestore_document().get()
        return self._firestore_data

    def get_firestore_data(self, path, default=None):
        """Returns a value from firestore at `path`, or `default` if none exists."""
        try:
            return self.firestore_data().get(path)
        except KeyError:
            return default

    def is_reference(self):
        """Is this submission the reference for its song?"""
        return self.get_firestore_data('reference', False)

    def _guess_parts(self):
        m = re.search(r'^(alto_)?(bass_)?(tenor_)?(treble_)?', self.filename)
        if m:
            return [part[:-1] for part in m.groups() if part]

    def parts(self):
        """Gets a list of parts.

        Looks for parts in firestore, falling back to the file name.
        """
        return self.get_firestore_data('parts') or self._guess_parts() or []

    def singers(self):
        """Gets a list of singers from firestore."""
        return self.get_firestore_data('singers', [])

    def singer_count(self):
        """Returns the number of singers.

        Looks for singers in firestore, falling back to guessing based on parts.
        """
        return len(self.singers()) or len(self.parts()) or 1

    # -- Cloud storage --

    @property
    def video_upload(self):
        """Returns the GCS video_upload object for this submission.

        >>> s = Submission('providence', '37b', 'test.mp4')
        >>> s.video_upload.name
        'providence/37b/test.mp4'
        >>> s.video_upload.bucket
        'quarantine-chorus-upload'
        >>> s.video_upload.url
        'gs://quarantine-chorus-upload/providence/37b/test.mp4'
        """
        return _GCS(self.storage_client(),
                    config.UPLOAD_BUCKET,
                    self.video_upload_name())

    @property
    def audio_extracted(self):
        """Returns the GCS audio_extracted object for this submission.

        See video_upload for example usage.
        """
        return _GCS(self.storage_client(),
                    config.AUDIO_EXTRACTED_BUCKET,
                    self.audio_extracted_name())

    @property
    def audio_aligned(self):
        """Returns the GCS audio_aligned object for this submission.

        See video_upload for example usage.
        """
        return _GCS(self.storage_client(),
                    config.AUDIO_ALIGNED_BUCKET,
                    self.audio_aligned_name())

    @property
    def video_aligned(self):
        """Returns the GCS video_aligned object for this submission.

        See video_upload for example usage.
        """
        return _GCS(self.storage_client(),
                    config.VIDEO_ALIGNED_BUCKET,
                    self.video_aligned_name())

    def audio_reference_candidates(self):
        """Returns a list of candidate GCS objects for this submission's audio
        reference.

        Prefers a reference specific to this submission's parts, falling back to a
        generic reference for the song.

        See video_upload for example usage.
        """
        return [_GCS(self.storage_client(), config.AUDIO_EXTRACTED_BUCKET, name)
                for name in self.audio_reference_names()]
