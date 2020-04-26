#!/usr/bin/env bash

# We rely on some filters added in ffmpeg 4, but the default distribution
# includes an older version of ffmpeg
echo 'Downloading ffmpeg'

mkdir ffmpeg-static

curl -sSL 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz' \
  | tar -xvjf - -C 'ffmpeg-static'

ffmpeg=$(find . -type f -name ffmpeg)

echo 'Deploying to gcloud'

echo gcloud functions deploy "$@" --update-env-vars "FFMPEG=$ffmpeg"