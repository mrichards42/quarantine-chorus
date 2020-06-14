"""Local filesystem shims around GCP clients.

This is a drop-in replacement for the lazy gcp module.
"""

import json
import shutil
from pathlib import Path

import funcy as F

from .decorators import static_cached_property


class GCP:
    ROOT = '.'

    @static_cached_property
    def storage_client():
        return LocalStorage

    @static_cached_property
    def firestore_client():
        return LocalFirestore


def init(root='.'):
    """Set up a local filesystem shim for GCP firestore and cloud storage."""
    from . import submission
    GCP.ROOT = root
    submission.Submission.GCP = GCP


# == Firestore =======================================================================


class LocalSnapshot:
    def __init__(self, data, exists):
        self.data = data
        self.exists = exists

    def get(self, k):
        return self.data[k]


class LocalDocument:
    def __init__(self, path):
        self.path = path
        self.json_path = path.with_suffix(path.suffix + '.json')

    def get(self):
        try:
            return LocalSnapshot(json.loads(self.json_path.read_text()), True)
        except FileNotFoundError:
            return LocalSnapshot({}, False)

    def _write(self, data):
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        self.json_path.write_text(json.dumps(data))

    def set(self, data, merge=False):
        if merge:
            old = self.get().data
            # shallow merge. I can't tell from the docs if it should be shallow or deep
            data = {**old, **data}
        self._write(data)

    def update(self, updates):
        data = self.get().data
        for k, v in updates.items():
            data = F.set_in(data, k.split('.'), v)
        self._write(data)


class LocalFirestore:
    path = 'firestore'

    @classmethod
    def document(cls, *path_parts):
        return LocalDocument(Path(GCP.ROOT, cls.path).resolve().joinpath(*path_parts))


# == Cloud Storage ===================================================================


class LocalBlob:
    def __init__(self, path):
        self.path = path

    def download_to_filename(self, filename):
        shutil.copyfile(self.path, filename)

    def upload_from_filename(self, filename):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(filename, self.path)

    def exists(self):
        return self.path.exists()

    def create_resumable_upload_session(self, *args, **kwargs):
        # We aren't going to implement a full resumable upload interface anywhere for
        # the local filesystem, so just return the blob's location as a uri
        return self.path.as_uri()


class LocalBucket:
    def __init__(self, path):
        self.path = path

    def blob(self, name):
        return LocalBlob(self.path.joinpath(name))


class LocalStorage:
    path = 'storage'

    @classmethod
    def bucket(cls, name):
        return LocalBucket(Path(GCP.ROOT, cls.path).resolve().joinpath(name))
