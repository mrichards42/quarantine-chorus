from pathlib import Path

import tomlkit

from .util import deep_merge

CONFIG = tomlkit.parse(Path('config.toml').read_text())

# -- GCS stuff we care about --

UPLOAD_BUCKET = CONFIG['gcs']['bucket']['video_upload']
AUDIO_EXTRACTED_BUCKET = CONFIG['gcs']['bucket']['audio_extracted']
AUDIO_ALIGNED_BUCKET = CONFIG['gcs']['bucket']['audio_aligned']
VIDEO_ALIGNED_BUCKET = CONFIG['gcs']['bucket']['video_aligned']
SUBMISSIONS_COLLECTION = CONFIG['gcs']['collection']['submissions']


# -- Singing config --

def singing(name):
    """Reads the config for a singing.

    Individual singings may override singing defaults.
    """
    return deep_merge(
        CONFIG['singing']['default'],
        CONFIG['singing'].get(name, {}),
    )


def song(singing_name, song_name):
    """Reads the config for a single song.

    Individual songs may override values from their singing
    """
    return deep_merge(
        singing(singing_name),
        CONFIG['singing'].get(singing_name, {}).get(song_name, {}),
    )
