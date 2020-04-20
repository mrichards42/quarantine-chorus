"""Alignment plots using matplotlib"""

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import scipy.signal as signal

from . import util

def top_lines(data, n):
    # Pull off the top 100 * n indices; hopefully at least n of those will be
    # far enough apart to show on the graph
    sample_n = 100 * n
    top_indices = np.argpartition(data, -sample_n)[-sample_n:]
    top_indices = sorted(top_indices, key=lambda i: data[i], reverse=True)
    # Indices that are too close together won't show up on a graph, so make
    # sure there's some separation between consecutive lines
    separation = int(len(data) / 100)
    # Find the top `n` from `top_indices`, ensuring that they are at least
    # `separation` indices apart from each other
    l = []
    for idx in top_indices:
        nearest = min(abs(idx - x) for x in l) if l else separation + 1
        if nearest > separation:
            l.append(idx)
    return np.array(l[:n])

COLORS = ['red', 'greenyellow', 'orange', 'deepskyblue', 'violet']

class Plotter():
    def __init__(self, samplerate, ref, subj, corr, analysis):
        self.samplerate = samplerate
        self.corr = corr
        self.analysis = analysis
        # Time axis
        max_samples = max(len(ref), len(subj))
        self.time = np.linspace(0., max_samples / samplerate, max_samples)
        # Pad wavs with 0s on the end so they are the same length
        self.ref = np.pad(ref, [0, max_samples - len(ref)])
        self.subj = np.pad(subj, [0, max_samples - len(subj)])

    def seconds(self, samples):
        return samples / self.samplerate

    def samples(self, seconds):
        return seconds * self.samplerate


    def plot_wav(self, subplot, data, vlines):
        # Plot the wav
        subplot.plot(self.time, data)
        # Draw alignment lines
        for i, x in enumerate(vlines):
            subplot.axvline(x=x, color=COLORS[i], zorder=0)
        # Hide quiet samples
        # subplot.axvspan(0, util.quiet_count(data, 10) / self.samplerate,
        #                 facecolor='white', zorder=2.5)
        # subplot.axvspan((len(data) - util.quiet_count(data[::-1], 10)) / self.samplerate, len(data),
        #                 facecolor='white', zorder=2.5)

    def make_plot(self, opts={}):
        # Setup subplots
        fig, subplots = plt.subplots(4, 1, figsize=opts.get('plot-size', [10, 7]))
        (ax_ref, ax_subj, ax_corr, ax_corr_zoom) = subplots

        for s in subplots:
            s.margins(x=0, y=0.1)
            s.xaxis.set_minor_locator(ticker.AutoMinorLocator())

        # X Axes
        corr_time = np.linspace(self.analysis['correlation_start_seconds'],
                                self.analysis['correlation_end_seconds'],
                                len(self.corr))

        # Alignment annotations (in axis units, i.e. seconds)
        corr_vline = self.analysis['correlation_shift_seconds'] # best correlation location
        subj_vlines = top_lines(self.subj, 5) / self.samplerate
        ref_vlines = subj_vlines + self.analysis['correlation_shift_seconds']

        # Audio files
        ax_ref.set_title('Reference Audio')
        self.plot_wav(ax_ref, self.ref, ref_vlines)
        ax_subj.set_title('Subject Audio')
        self.plot_wav(ax_subj, self.subj, subj_vlines)

        # Correlation
        ax_corr.plot(corr_time, self.corr)
        ax_corr.axvspan(self.analysis['correlation_window_min_seconds'],
                        self.analysis['correlation_window_max_seconds'],
                        facecolor='#FFCCCC', zorder=0)
        # best correlation
        ax_corr.axvline(x=corr_vline, color='red', zorder=0)
        ax_corr.set_title('Cross-correlation')

        # Zoomed correlation -- some correlations have multiple reasonable peaks,
        # and it can be useful to see them highlighted in a zoomed plot
        # Zoom to 2 seconds on either side
        zoom_min = self.analysis['correlation_shift'] - self.samples(2)
        zoom_max = self.analysis['correlation_shift'] + self.samples(2)
        corr_zoom = self.corr[-self.analysis['correlation_start'] + zoom_min:
                              -self.analysis['correlation_start'] + zoom_max]
        corr_zoom_time = np.linspace(self.seconds(zoom_min),
                                     self.seconds(zoom_max),
                                     len(corr_zoom))

        ax_corr_zoom.plot(corr_zoom_time, corr_zoom)

        # best correlation
        # TODO: tooltip?
        ax_corr_zoom.axvline(x=corr_vline, color='red', zorder=0)

        # correlation peaks
        peak_idx = self.analysis['correlation_shift'] - self.analysis['correlation_start']
        max_height = self.corr[peak_idx]
        peaks, _ = signal.find_peaks(abs(corr_zoom),
                                     # at least 5/100ths of a second apart
                                     distance=self.samplerate / 20,
                                     # within 90% of the max peak
                                     height=max_height * 0.9)
        for idx in peaks:
            offset = corr_zoom_time[idx]
            # TODO: tooltip?
            ax_corr_zoom.axvline(x=offset, zorder=-1, color='darkorange')

        ax_corr_zoom.set_title('Cross-correlation (zoomed to shift window)')

        fig.tight_layout()

        return fig

    def save_plot(self, fig, filename):
        fig.canvas.print_figure(filename)
