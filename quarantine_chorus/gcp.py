"""Lazy wrappers around google cloud clients."""

from .decorators import static_cached_property


class GCP:
    @static_cached_property
    def storage_client():
        import google.cloud.storage
        return google.cloud.storage.Client()

    @static_cached_property
    def firestore_client():
        import google.cloud.firestore
        return google.cloud.firestore.Client()
