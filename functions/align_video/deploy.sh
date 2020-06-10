#!/usr/bin/env bash

set -euo pipefail

# We rely on some filters added in ffmpeg 4, but the default distribution
# includes an older version of ffmpeg
echo 'Downloading ffmpeg'

mkdir ffmpeg-static

curl -sSL 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz' \
  | tar -xvJf - -C 'ffmpeg-static'

ffmpeg=$(find . -type f -name ffmpeg)

echo 'Deploying to gcloud'

gcloud functions deploy "$@" \
  --set-env-vars="FFMPEG=$ffmpeg"
