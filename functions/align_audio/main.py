import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from pydub import AudioSegment
from google.cloud import firestore
from google.cloud import storage

import align

storage_client = storage.Client()
db = firestore.Client()

AUDIO_BUCKET = os.environ['AUDIO_BUCKET']
ALIGNED_AUDIO_BUCKET = os.environ['ALIGNED_AUDIO_BUCKET']
SUBMISSIONS_COLLECTION = os.environ['SUBMISSIONS_COLLECTION']

logging.basicConfig(level=logging.INFO)

def gcs_url(bucket, object_name):
    return f'gs://{bucket}/{object_name}'

def find_part(object_name):
    m = re.search(r'^((^|_)(alto|bass|tenor|treble))+', object_name)
    if m:
        return m.group(0)

def reference_blob(object_name):
    path = str(Path(object_name).parent)
    part = find_part(Path(object_name).name)
    if not part:
        logging.warning('Unable to find part in object %s', object_name)
        return
    bucket = storage_client.bucket(AUDIO_BUCKET)
    names = [part + '_lead.m4a', 'lead.m4a']
    for name in names:
        blob = bucket.get_blob(path + '/' + name)
        if blob:
            return blob
        logging.info('Reference file %s does not exist; trying for fallback',
                     gcs_url(AUDIO_BUCKET, name))

def write_aligned_file(subj_file, out_file, analysis):
    filters = []
    if analysis['pad'] > 0:
        pad_ms = round(analysis['pad_seconds'] * 1000)
        filters.append(f'adelay={pad_ms}|{pad_ms}')
    elif analysis['trim'] > 0:
        filters.append(f'atrim={"%0.3f" % analysis["trim_seconds"]}')
        # atrim messes with pts, so reset here
        filters.append('asetpts=PTS-STARTPTS')
    filters.append(align.loudnorm_filter(analysis['loudnorm']))
    # loudnorm upsamples to 192k, which is excessive
    filters.append(f'aresample=44100:first_pts=0')
    # Run ffmpeg
    cmd = ['ffmpeg', '-y', '-i', subj_file,
           '-af', ','.join(filters),
           '-c:a', 'aac', '-b:a', '128k', '-ac', '1',
           out_file]
    return subprocess.run(cmd,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          check=True)

def align_audio_files(ref_file, subj_file, out_file):
    # Read files
    logging.info('Reading reference file')
    ref = AudioSegment.from_file(ref_file, parameters=['-ar', '44100'])
    logging.info('Reading subject file')
    subj = AudioSegment.from_file(subj_file, parameters=['-ar', '44100'])
    assert ref.frame_rate == subj.frame_rate
    samplerate = ref.frame_rate
    ref_wav = np.array(ref.get_array_of_samples())
    subj_wav = np.array(subj.get_array_of_samples())
    del ref, subj
    # Preprocess
    ref_processed = align.Preprocessor(ref_wav).loudness_75()
    subj_processed = align.Preprocessor(subj_wav).loudness_75()
    del ref_wav, subj_wav
    # Cross-correlate
    logging.info('Running cross-correlation analysis')
    analysis, corr = align.cross_correlate(samplerate, ref_processed, subj_processed)
    del ref_processed, subj_processed
    # Loudnorm
    logging.info('Running loudnorm analysis')
    loudnorm = align.loudnorm_analysis(subj_file, analysis['trim_seconds'])
    analysis['loudnorm'] = loudnorm
    logging.info('Analysis output: %s', json.dumps(analysis))
    # Dump aligned file
    write_aligned_file(subj_file, out_file, analysis)
    return analysis

def align_audio(data, context):
    # Find subject
    url = gcs_url(data['bucket'], data['name'])
    subj_blob = storage_client.bucket(data['bucket']).get_blob(data['name'])
    logging.info('Triggered with %s', url)
    if not subj_blob:
        logging.warning('Blob %s does not exist! Aborting.', url)
        return

    # Find reference
    ref_blob = reference_blob(subj_blob.name)
    if ref_blob:
        logging.info('Found reference audio %s',
                     gcs_url(ref_blob.bucket.name, ref_blob.name))
    if not ref_blob:
        logging.warning('Unable to find appropriate reference audio! Aborting.')
        return

    _, temp_subj = tempfile.mkstemp(Path(data['name']).suffix)
    _, temp_ref = tempfile.mkstemp('.m4a')
    _, temp_out = tempfile.mkstemp('.m4a')
    try:
        # Download files
        logging.info('Downloading reference %s',
                     gcs_url(ref_blob.bucket.name, ref_blob.name))
        ref_blob.download_to_filename(temp_ref)
        logging.info('Downloading subject %s', url)
        subj_blob.download_to_filename(temp_subj)
        # Analyze and align subject
        logging.info('Aligning audio files %s', url)
        analysis = align_audio_files(temp_ref, temp_subj, temp_out)
        # Send analysis to firestore
        logging.info('Saving analysis data to firestore')
        doc_name = str(Path(data['name']).with_suffix(''))
        ref = db.collection(SUBMISSIONS_COLLECTION).document(doc_name)
        ref.set({'analysis': analysis}, merge=True)
        # Send output to cloud storage
        logging.info('Saving aligned audio file to %s',
                     gcs_url(ALIGNED_AUDIO_BUCKET, data['name']))
        aligned_bucket = storage_client.bucket(ALIGNED_AUDIO_BUCKET)
        aligned_bucket.blob(data['name']).upload_from_filename(temp_out)
    finally:
        os.remove(temp_subj)
        os.remove(temp_ref)
        os.remove(temp_out)
