import json
import logging
import os
import re
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

def run_alignment(ref_segment, subj_segment):
    assert ref_segment.frame_rate == subj_segment.frame_rate
    samplerate = ref_segment.frame_rate
    # Read and preprocess
    ref_wav = np.array(ref_segment.get_array_of_samples())
    subj_wav = np.array(subj_segment.get_array_of_samples())
    ref_processed = align.Preprocessor(ref_wav).loudness_75()
    subj_processed = align.Preprocessor(subj_wav).loudness_75()
    # Cross-correlate
    analysis, corr = align.cross_correlate(samplerate, ref_processed, subj_processed)
    return analysis

def get_aligned_segment(subj, analysis):
    if analysis['pad'] > 0:
        # Get silent samples
        # pydub doesn't have a way to create silence in samples, so instead we
        # create silence + 1 second and then slice to the exact length we want
        silence = AudioSegment.silent(duration=(analysis['pad_seconds'] + 1) * 1000,
                                      frame_rate=subj.frame_rate)
        silence = silence.get_sample_slice(0, analysis['pad'])
        return silence + subj
    elif analysis['trim'] > 0:
        return subj.get_sample_slice(analysis['trim'])
    else:
        return subj

def align_audio_files(ref_file, subj_file, out_file):
    logging.info('Reading reference file')
    ref = AudioSegment.from_file(ref_file, parameters=['-ar', '44100'])
    logging.info('Reading subject file')
    subj = AudioSegment.from_file(subj_file, parameters=['-ar', '44100'])
    # Analysis
    logging.info('Running cross-correlation analysis')
    analysis = run_alignment(ref, subj)
    logging.info('Analysis output: %s', json.dumps(analysis))
    # Dump aligned file
    out = get_aligned_segment(subj, analysis)
    out.export(out_file, format='mp4', bitrate='128k')
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
        ref = db.collection(SUBMISSIONS_COLLECTION).document(data['name'])
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
