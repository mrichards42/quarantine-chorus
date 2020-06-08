"""Lazy wrappers around google cloud clients."""

from .lazy import static_cached_property


class GCP:
    @static_cached_property
    def storage_client():
        import google.cloud.storage
        return google.cloud.storage.Client()

    @static_cached_property
    def firestore_client():
        import google.cloud.firestore
        return google.cloud.firestore.Client()






####### Local wrappers

import json
from pathlib import Path

import funcy as F


class LocalDocumentSnapshot:
    def __init__(self, data, exists):
        self.data = data
        self.exists = exists

    def get(self, k):
        return self.data[k]


class LocalFirestoreDocument:
    def __init__(self, path):
        self.path = path
        self.json_path = path.with_suffix(path.suffix + '.json')

    def get(self):
        try:
            return LocalDocumentSnapshot(json.loads(self.json_path.read_text()), True)
        except FileNotFoundError:
            return LocalDocumentSnapshot({}, False)

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
    root = 'firestore'

    @classmethod
    def document(cls, *path_parts):
        return LocalFirestoreDocument(Path(cls.root, *path_parts))
