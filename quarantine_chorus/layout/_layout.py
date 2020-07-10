"""Layout class

All this code assumes videos are the same height.
"""

import itertools
import math

from .track import LayoutTrack


class Layout:
    def __init__(self, videos, aspect_ratio=16/9, pillarbox_width=0):
        self.videos = list(videos)
        self.aspect_ratio = aspect_ratio
        self.pillarbox_width = pillarbox_width
        self._arrange()

    PART_ORDER = {
        'treble': 0,
        'alto': 1,
        'tenor': 2,
        'bass': 3,
        'unknown': 4,
    }

    @classmethod
    def from_files(cls, filenames, *args, **kwargs):
        return cls(map(LayoutTrack.from_file, filenames), *args, **kwargs)

    def copy(self):
        return Layout([v.copy() for v in self.videos],
                      self.aspect_ratio,
                      self.pillarbox_width)

    @property
    def height(self):
        h = max(v.bottom for v in self.videos)
        # adjust height until the bounding box includes all videos
        w = max(v.right for v in self.videos)
        while h * self.aspect_ratio < w:
            h += self.videos[0].height
        return h

    @property
    def width(self):
        return self.height * self.aspect_ratio

    def blank_space(self):
        """Determines the amount of blank space in this layout."""
        layout_size = self.width * self.height
        video_size = sum((v.width * v.height for v in self.videos))
        # we've enforced (in _arrange) no overlaps, so this should be accurate
        return layout_size - video_size

    def _arrange(self):
        """Arranges videos so there are no overlaps."""
        # Sort by part, then by row, then by column
        self.videos.sort(key=lambda v: (self.PART_ORDER[v.part], v.top, v.left))

        # A single layout pass
        def arrange_pass(layout_width):
            for i, v in enumerate(self.videos):
                if i == 0:
                    v.move(0, 0)
                else:
                    prev = self.videos[i-1]
                    v.move(prev.right, prev.top)
                    if v.right > layout_width - self.pillarbox_width:
                        v.move(0, prev.bottom)  # next row

        # Run layout passes until we get one that works
        total_width = sum(v.width for v in self.videos)
        row_height = self.videos[0].height
        ideal_rows = int(math.sqrt(total_width / (row_height * self.aspect_ratio)))
        for rows in range(ideal_rows, ideal_rows + 10):
            layout_width = rows * row_height * self.aspect_ratio
            arrange_pass(layout_width)
            if self.width == layout_width:  # this pass worked
                break

    def center(self):
        """Centers each row of videos.

        _arrange() does not keep videos centered, so this should be called as a final
        step in the layout."""
        self._arrange()
        for _, row in itertools.groupby(self.videos, lambda v: v.top):
            row = list(row)
            offset = int((self.width - row[-1].right) / 2)
            for v in row:
                v.left += offset
        return self

    def justify(self):
        """Justifies each row of videos.

        _arrange() does not keep videos centered, so this should be called as a final
        step in the layout."""
        self._arrange()
        row_width = max(v.right for v in self.videos)
        offset = (self.width - row_width) / 2
        for _, row in itertools.groupby(self.videos, lambda v: v.top):
            row = list(row)
            justify_offset = (row_width - row[-1].right) / (len(row) - 1)
            for i, v in enumerate(row):
                v.left += int(offset + justify_offset * i)
        return self
