#!/usr/bin/env bash
set -euo pipefail

# Look for all functions in functions/*
# Create a hash of their contents
# Deploy if contents have changed since the last deploy

# Each function should have a `deploy-flags.yml` file with deploy
# confuguration, using the format described at:
# https://cloud.google.com/sdk/gcloud/reference/topic/flags-file

MD5_LABEL_KEY='content-hash-md5'

for d in functions/*; do
  pushd "$d"

  # Replace all symlinks with copies of their original
  find . -maxdepth 1 -type l \
    -exec sh -c 'original=$(readlink "$1"); rm "$1"; cp -R "$original" "$1"' _ {} \;

  function_name=$(basename "$d")
  echo "Checking function '$function_name' for updates"

  # This isn't completely foolproof, but it's pretty good (fails for files with
  # newlines in the name). The initial attempt used tar, but it included too
  # much metadata (including last modified time), which didn't work right in CI
  local_md5=$(gcloud meta list-files-for-upload \
                | sort \
                | xargs -I {} /bin/sh -c 'echo "$0"; cat "$0"' {} \
                | md5sum \
                | cut -d' ' -f1)
  echo "local_md5=$local_md5"

  remote_md5=$(gcloud functions describe "$function_name" --format "value(labels.$MD5_LABEL_KEY)") || true
  echo "remote_md5=$remote_md5"

  if [[ "$local_md5" != "$remote_md5" ]]; then
    echo 'Updating function since contents have changed'
    if [[ -x "deploy.sh" ]]; then
      ./deploy.sh "$function_name" \
        --update-labels="$MD5_LABEL_KEY=$local_md5" \
        --flags-file=deploy-flags.yml
    else
      gcloud functions deploy "$function_name" \
        --update-labels="$MD5_LABEL_KEY=$local_md5" \
        --flags-file=deploy-flags.yml
    fi
  else
    echo 'Skipping update: function has not changed'
  fi

  popd
done
