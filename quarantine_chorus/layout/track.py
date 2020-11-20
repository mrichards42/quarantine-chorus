"""A track that can be moved around."""

import dataclasses as dc
from typing import Optional


@dc.dataclass
class LayoutTrack:
    name: str = ''
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0
    original_width: int = 0
    original_height: int = 0
    scale_factor: float = 1.0
    singer_count: int = 1
    part: Optional[str] = None

    def __post_init__(self):
        if not self.original_width:
            self.original_width = self.width
        if not self.original_height:
            self.original_height = self.height
        if self.part is None:
            import re
            pat = re.compile(r'(?:^|\W|_)(treble|alto|tenor|bass)(?:\W|_|$)', re.I)
            m = pat.search(self.name)
            if m:
                self.part = m.group(1).lower()
            else:
                self.part = 'unknown'

    @classmethod
    def from_files(cls, filename):
        from .. import ffmpeg
        probe = ffmpeg.probe(filename)
        return cls(
            name=filename,
            width=probe.width,
            height=probe.height,
        )

    def copy(self):
        return LayoutTrack(
            name=self.name,
            left=self.left,
            top=self.top,
            width=self.width,
            height=self.height,
            original_width=self.original_width,
            original_height=self.original_height,
            scale_factor=self.scale_factor,
            singer_count=self.singer_count,
            part=self.part,
        )

    @property
    def right(self):
        return self.left + self.width

    @property
    def bottom(self):
        return self.top + self.height

    @property
    def centerx(self):
        return self.left + self.width / 2

    @property
    def centery(self):
        return self.top + self.height / 2

    def move(self, left, top):
        """Moves the position to (left, top)."""
        self.left = int(left)
        self.top = int(top)
        return self

    def crop_width(self, amount):
        """Crops the width by `amount`."""
        self.width = int(max(0, min(self.width - amount,
                                    self.original_width * self.scale_factor)))
        return self

    def crop_ratio(self):
        """Returns the ratio of original_width to current width.

        1 means no cropping; 0.5 means half the width has been cropped.
        """
        return self.width / (self.original_width * self.scale_factor)

    def crop_amount(self):
        """Returns the number of pixels that the width is cropped"""
        return int(self.original_width * self.scale_factor) - self.width

    def scale(self, width=None, height=None):
        """Sets the scaling factor, based on the original size.

        Selects the smallest scaling factor that will completely enclose the video
        within the width x height bounding box.
        """
        # Unscale
        unscaled_width = self.width / self.scale_factor
        unscaled_height = self.height / self.scale_factor
        # Compute the new scaling factor
        if width or height:
            self.scale_factor = min(
                width / self.original_width if width else float('inf'),
                height / self.original_height if height else float('inf'),
            )
        else:
            self.scale_factor = 1.0
        # Rescale
        self.width = int(unscaled_width * self.scale_factor)
        self.height = int(unscaled_height * self.scale_factor)
        return self
