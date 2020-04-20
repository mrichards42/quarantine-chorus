import numpy as np

def quiet_count(a, threshold):
    "Returns the number of 'quiet' values (below threshold) at the front of a."
    return int(np.argmax(a > threshold))
