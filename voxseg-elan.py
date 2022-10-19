#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# A short script to that wraps the Voxseg DNN-based voice activity detection
# package (https://github.com/NickWilkinson37/voxseg) to act as a local
# recognizer in ELAN.

# TODO: Could also add a high-pass filter (above 2800-3000Hz or so), then
# amp the segments to make sure we catch those high-pitched, noisy semgents.
# See https://github.com/jiaaro/pydub/blob/master/pydub/effects.py#L187
# for pydub.effects.high_pass_filter


import os
import os.path
import re
import shutil
import subprocess
import sys
import tempfile

import pydub
import pydub.silence
import voxseg
import tensorflow.keras


# Begin by tracking down the ffmpeg(1) executable that this recognizer will use
# to process audio materials.  If ffmpeg(1) doesn't exist in the current path, 
# exit now to save everyone some heartbreak later on.
ffmpeg = shutil.which('ffmpeg')
if not ffmpeg:
    sys.exit(-1)

# Read in all of the parameters that ELAN passes to this local recognizer on
# standard input.
params = {}
for line in sys.stdin:
    match = re.search(r'<param name="(.*?)".*?>(.*?)</param>', line)
    if match:
        params[match.group(1)] = match.group(2).strip()


# Create a temporary directory in which to create the Kaldi-style set of
# files that Voxseg expects as its input.  This should eventually contain
# two files and one subdirectory:
#
#   input_dir/
#       wav.scp
#       wavs/
#           converted_source_audio.wav
input_dir = tempfile.TemporaryDirectory()

# Create a subdirectory of the temporary directory in which to hold the
# converted input audio ("input_dir/wavs").
input_wavs_dir = os.path.join(input_dir.name, 'wavs')
os.mkdir(input_wavs_dir)

# Use ffmpeg(1) to convert the 'source' audio file into a temporary 16-bit
# mono 16KHz WAV, storing the result in "input_dir/wavs/temp_input.wav".
##print("PROGRESS: 0.2 Converting source audio", flush = True)
tmp_wav_file = os.path.join(input_wavs_dir, "temp_input.wav")
subprocess.call([ffmpeg, '-y', '-v', '0', \
    '-i', params['source'], \
    '-ac', '1',
    '-ar', '16000',
    '-sample_fmt', 's16',
    '-acodec', 'pcm_s16le', \
    tmp_wav_file])

# Now store a reference to the (full path of) the converted audio in
# "input_dir/wav.scp".
input_audio_list = open(os.path.join(input_dir.name, "wav.scp"), "w")
input_audio_list.write("vad_audio %s\n" % tmp_wav_file)
input_audio_list.close()


# Now turn the show over to Voxseg, preparing the audio in the (Kaldi-style)
# input directory, extracting features, then normalizing them.
voxseg_data = voxseg.extract_feats.prep_data(input_dir.name)
feats = voxseg.extract_feats.extract(voxseg_data)
norm_feats = voxseg.extract_feats.normalize(feats)

# Load the pre-trained Voxseg VAD model, then apply it to the features
# extracted above to produce a set of labels (i.e., intervals of speech and
# non-speech).
model = tensorflow.keras.models.load_model(\
    os.path.join(os.curdir, 'voxseg', 'voxseg', 'models', 'cnn_bilstm.h5'))
targets = voxseg.run_cnnlstm.predict_targets(model, norm_feats)
predicted_labels = voxseg.run_cnnlstm.decode(targets, \
    float(params['speech_threshold']))

# Read in the amount of time users want to add/subtract from the start and
# end times of each of the segments produced by this recognizer.  (A quick-
# and-dirty way of working around results that may clip the starts or ends
# of annotations, but are otherwise fine)
adjust_start_s = float(params['adjust_start_ms']) / 1000.0
adjust_end_s = float(params['adjust_end_ms']) / 1000.0

# Since Voxseg often misses the starts of segments (particularly noisy
# consonants like /s/), we allow users the option of applying a post-hoc,
# silence-detection-based adjustment to the beginnings and ends of the
# segments that Voxseg returns.
#
# In practical terms, this involves moving a sliding window (by default,
# 10ms wide) running over an additional bit (by default, 250ms) over audio
# shortly before and after the start and end of each segment, seeing if
# that audio exceeds a user-specified volume threshold (by default,
# relative to the volume of the segment itself).
#
# We also use pydub's silence detection facilities to detect longer periods
# of silence within the segments that Voxseg returns -- it tends to return
# quite large chunks on its own, and we can often find smaller chunks within
# those that are separated by (near) silence.
do_silence_detection = (params['do_silence_detection'] == 'Enable')
if do_silence_detection:
    audio = pydub.AudioSegment.from_wav(tmp_wav_file)

    search_window_ms = 250
    window_ms = 10
    edge_threshold_factor = 1.0 + (float(params['edge_threshold']) / 100)
    internal_threshold_factor = 1.0+(float(params['internal_threshold']) / 100)

    adjusted_labels = [dict(\
        [('start', int(predicted_labels['start'][i] * 1000)), \
         ('end', int(predicted_labels['end'][i] * 1000))]) \
           for i in predicted_labels.index]

    for i in range(len(adjusted_labels)):
        orig_start_ms = adjusted_labels[i]['start']
        orig_end_ms = adjusted_labels[i]['end']
        orig_clip = audio[orig_start_ms:orig_end_ms]
        orig_avg_vol = orig_clip.dBFS
        threshold_vol = orig_clip.dBFS * edge_threshold_factor

        # Now, starting from $search_window_ms before the original start time
        # for this segment, step in $window_ms increments over the audio,
        # checking to see whether or not this snippet falls above or below
        # the volume threshold (relative to the average volume of the original
        # segment).
        new_start_ms = max(0, orig_start_ms - search_window_ms)
        for window in range(new_start_ms, orig_end_ms, window_ms):
            window_clip = audio[window:window + window_ms]
            window_clip_avg_vol = window_clip.dBFS

            # If we're under or at the threshold, then treat this window as
            # silence and adjust the start time of this segment accordingly.
            if window_clip_avg_vol <= threshold_vol:
                adjusted_labels[i]['start'] = window
            # Otherwise, if we're over the threshold, then this window contains
            # non-silence, and we should stop where we are and quit trying to
            # adjust the start times for this segment.
            else:
                adjusted_labels[i]['start'] = window - window_ms
                break

        # Now apply the same logic to the end of the segment, stepping back-
        # wards in $window_ms increments to see where our relative volume
        # threshold is exceeded (and adjusting the end of this segment up to
        # that point).
        new_end_ms = min(orig_end_ms + search_window_ms, len(audio)) 
        for window in range(new_end_ms - window_ms, \
                            adjusted_labels[i]['start'], -window_ms):
            window_clip = audio[window:window + window_ms]
            window_clip_avg_vol = window_clip.dBFS

            if window_clip_avg_vol <= threshold_vol:
                adjusted_labels[i]['end'] = window
            else:
#                adjusted_labels[i]['end'] = window + window_ms
                adjusted_labels[i]['end'] = window
                break

    # Now look for longer periods of silence *within* these segments, splitting
    # up longer segments into smaller sections of non-silence.
    split_labels = []
    keep_silence_ms = 50
    for i in range(len(adjusted_labels)):
        start_ms = adjusted_labels[i]['start']
        end_ms = adjusted_labels[i]['end']

        clip = audio[start_ms:end_ms]
        avg_vol = clip.dBFS
        threshold_vol = avg_vol * internal_threshold_factor

        segs = pydub.silence.detect_nonsilent(clip, min_silence_len = 500, \
            silence_thresh = threshold_vol, seek_step = 10)

        for (i, [seg_start_ms, seg_end_ms]) in enumerate(segs):
            # Keep a bit of silence on either end of each of the new segments.
            if i != 0:
                seg_start_ms -= keep_silence_ms
            if i != len(segs) - 1:
                seg_end_ms += keep_silence_ms

            split_labels.append(dict(\
                [('start', start_ms + seg_start_ms), \
                 ('end', start_ms + seg_end_ms)]))

    adjusted_labels = split_labels

# Then open 'output_segments' for writing, and return all of the new speech
# segments recognized by Voxseg as the contents of <span> elements (see
# below).
with open(params['output_segments'], 'w', encoding = 'utf-8') as output_segs:
    # Write document header.
    output_segs.write('<?xml version="1.0" encoding="UTF-8"?>\n')

    # Write out the adjusted annotations if the user requested that silence
    # detection be applied.
    if do_silence_detection:
        output_segs.write('<TIER xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="file:avatech-tier.xsd" columns="VoxsegOutput-Adjusted">\n')
        for a in adjusted_labels:
            output_segs.write(\
                '    <span start="%.3f" end="%.3f"><v></v></span>\n' %\
                ((a['start'] / 1000.0) + adjust_start_s, \
                 (a['end'] / 1000.0) + adjust_end_s))

        output_segs.write('</TIER>\n')
    # Otherwise, just write out whatever Voxseg gave us (with any user-
    # specified adjustments to the start and end times of each segment).
    else:
        output_segs.write('<TIER xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="file:avatech-tier.xsd" columns="VoxsegOutput">\n')
        for i in predicted_labels.index:
            output_segs.write(\
                '    <span start="%.3f" end="%.3f"><v></v></span>\n' %\
                (predicted_labels['start'][i] + adjust_start_s, \
                 predicted_labels['end'][i] + adjust_end_s))

        output_segs.write('</TIER>\n')

# Finally, tell ELAN that we're done.
print('RESULT: DONE.', flush = True)
