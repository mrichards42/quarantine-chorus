import logging
import shlex
import subprocess

from quarantine_chorus import ffmpeg


def ffmpeg_mix(tracks, width=None, height=None, audio_only=False):
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
            video = video.scale(w=t['width'], h=t['height'])
            video_streams.append(video)
            xstack_layout.append((t['left'], t['top']))
    # background for xstack
    if video_streams:
        video_tracks = [t for t in tracks if t.get('has_video')]
        w = width or int(max(t['left'] + t['width'] for t in video_tracks))
        h = height or int(max(t['top'] + t['height'] for t in video_tracks))
        background = ffmpeg.input(f'color=black:size={w}x{h}:duration=1:rate=30',
                                  format='lavfi')
        video_streams.insert(0, background)
        xstack_layout.insert(0, (0, 0))
    # Combine outputs and return all the streams
    streams = []
    if audio_streams:
        streams.append(ffmpeg.amix(audio_streams))
    if video_streams:
        streams.append(ffmpeg.xstack(video_streams, layout=xstack_layout))
    return streams


def _shjoin(args):
    return ' '.join(shlex.quote(arg) for arg in args)


def preview_thread(tracks, **kwargs):
    streams = ffmpeg_mix(tracks, **kwargs)
    # At least on mac, running ffplay using subprocess works when we're started from
    # the command line, but not when running the bundled app. Running ffmpeg works fine
    # either way, the ffplay window never pops up.
    # Instead, build a pipeline and run using the shell, which seems to work
    ffmpeg_cmd = (ffmpeg.output(*streams, 'pipe:', format='mpegts')
                  .compile(ffmpeg.EXECUTABLE))
    ffplay_cmd = [ffmpeg._play.EXECUTABLE, '-i', 'pipe:']
    cmd = _shjoin(ffmpeg_cmd) + ' | ' + _shjoin(ffplay_cmd)
    logging.info("Running preview command: %s", cmd)
    subprocess.Popen(cmd, shell=True)
