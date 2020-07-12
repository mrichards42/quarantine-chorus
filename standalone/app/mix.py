import logging
import os
import shlex
import subprocess

from quarantine_chorus import ffmpeg


def ffmpeg_mix(tracks, width=None, height=None, audio_only=False, scale=1):
    """Mixes all tracks, returning a list of output streams."""
    audio_streams = []
    video_streams = []
    xstack_layout = []
    # FFMPEG filters
    for t in tracks:
        stream = ffmpeg.input(t['path'])
        if t.get('has_audio'):
            audio = stream.audio
            if t.get('alignment_analysis'):
                audio = audio.align_audio(t['alignment_analysis'])
            # Volume adjust
            in_loudness = t.get('loudness_analysis', {}).get('L')
            if in_loudness:
                # From https://github.com/mltframework/mlt/blob/7da01504d6844412b6e26c03b7c98214a1730343/src/modules/plus/filter_loudness.c#L160-L169
                target_db = t['loudness_analysis']['program']
                delta_db = target_db - in_loudness
                audio = audio.volume(dB=delta_db)
            audio_streams.append(audio)
        if t.get('has_video') and not audio_only:
            video = stream.video
            if t.get('alignment_analysis'):
                video = video.align_video(t['alignment_analysis'])
            video = video.scale(w=int(t['width'] * scale), h=int(t['height'] * scale))
            video_streams.append(video)
            xstack_layout.append((int(t['left'] * scale), int(t['top'] * scale)))
    # background for xstack
    if video_streams:
        video_tracks = [t for t in tracks if t.get('has_video')]
        w = int((width or max(t['left'] + t['width'] for t in video_tracks)) * scale)
        h = int((height or max(t['top'] + t['height'] for t in video_tracks)) * scale)
        background = ffmpeg.input(f'color=black:size={w}x{h}:duration=1:rate=30',
                                  format='lavfi')
        video_streams.insert(0, background)
        xstack_layout.insert(0, (0, 0))
    # Combine outputs and return all the streams
    streams = []
    if audio_streams:
        streams.append(ffmpeg.amix(audio_streams, dropout_transition=1000)
                       # amix reduces volume of each track to `1/n`, so increase the
                       # result by a factor of `n` to get it back to normal. Hopefully
                       # we've already applied some volume normalization, so this
                       # shouldn't be too loud. AFAICT Shotcut doesn't do any kind of
                       # volume reduction when it mixes tracks, so this should be
                       # closer to what it will sound like in Shotcut anyways.
                       .volume(len(audio_streams)))
    if video_streams:
        streams.append(ffmpeg.xstack(video_streams, layout=xstack_layout))
    return streams


def _shjoin(args):
    return ' '.join(shlex.quote(arg) for arg in args)


def preview_thread(tracks, **kwargs):
    streams = ffmpeg_mix(tracks, **kwargs)
    if os.name == 'nt':
        ffmpeg_proc = (ffmpeg.output(*streams, 'pipe:', format='mpegts')
                       .run_async(pipe_stdout=True))
        ffmpeg.play('pipe:', window_title='Preview', stdin=ffmpeg_proc.stdout)
        # No need to keep the ffmpeg process around after ffplay has stopped
        ffmpeg_proc.stdout.close()
        ffmpeg_proc.terminate()
    else:
        # At least on mac, running ffplay using subprocess works when we're started
        # from the command line, but not when running the bundled app. Running ffmpeg
        # works fine either way, the ffplay window never pops up. Instead, build a
        # pipeline and run using the shell, which seems to work
        ffmpeg_cmd = (ffmpeg.output(*streams, 'pipe:', format='mpegts')
                      .compile(ffmpeg.EXECUTABLE))
        ffplay_cmd = [ffmpeg._play.EXECUTABLE, '-i', 'pipe:']
        cmd = _shjoin(ffmpeg_cmd) + ' | ' + _shjoin(ffplay_cmd)
        logging.info("Running preview command: %s", cmd)
        subprocess.Popen(cmd, shell=True)
