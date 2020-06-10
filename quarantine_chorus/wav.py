import ffmpeg


def read(filename, samplerate=44100):
    """Reads PCM audio from a file, returning a numpy array."""
    # This is both faster (slightly) and uses less memory (significantly) than doing
    # this via pydub.AudioSegment
    import numpy as np
    proc = (ffmpeg
            .input(filename)
            .output('-', format='s16le', acodec='pcm_s16le', ac=1, ar=samplerate)
            .overwrite_output()
            .run_async(pipe_stdout=True))
    return np.frombuffer(proc.stdout.read(), dtype=np.dtype('<i2'))