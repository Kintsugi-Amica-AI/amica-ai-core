"""Vehicle body colour from a photo, with no AI.

This mirrors ``VehicleColourClassifier`` in the mobile app
(amica-mobile-app/lib/features/plate_scan/utils/vehicle_colour.dart). Keep
the thresholds in step so the evaluation here measures what the phone does.

Images are anything indexable as ``image[y][x] -> (r, g, b)`` with 0-255
channels: a numpy ``HxWx3`` array, or nested lists in tests.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

LOW_LIGHT_LUMA = 55.0
WARM_CAST_SHARE = 0.55
WARM_CAST_MAX_LUMA = 115.0
MIN_SHARE = 0.35
_GRID = 48
_SCENE_GRID = 32

COLOURS = (
    "white", "silver", "grey", "black", "red", "maroon",
    "orange", "yellow", "green", "blue", "brown",
)

# Colours a camera mixes up; never reported as a mismatch.
LOOK_ALIKES = {
    "white": {"silver"},
    "silver": {"white", "grey"},
    "grey": {"silver", "black"},
    "black": {"grey"},
    "red": {"maroon", "orange"},
    "maroon": {"red", "brown"},
    "orange": {"red", "yellow", "brown"},
    "yellow": {"orange"},
    "green": set(),
    "blue": set(),
    "brown": {"maroon", "orange"},
}


def colours_compatible(a: str, b: str) -> bool:
    return a == b or b in LOOK_ALIKES.get(a, set())


Box = tuple[float, float, float, float]  # left, top, right, bottom (pixels)


@dataclass(frozen=True)
class ColourReading:
    colour: Optional[str]
    share: float
    low_light: bool = False
    colour_cast: bool = False

    @property
    def is_reliable(self) -> bool:
        return (self.colour is not None and not self.low_light
                and not self.colour_cast and self.share >= MIN_SHARE)


def hue(r: int, g: int, b: int) -> float:
    max_c, min_c = max(r, g, b), min(r, g, b)
    d = float(max_c - min_c)
    if d == 0:
        return 0.0
    if max_c == r:
        h = ((g - b) / d) % 6
    elif max_c == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    h *= 60
    return h + 360 if h < 0 else h


def classify_pixel(r: int, g: int, b: int) -> str:
    max_c, min_c = max(r, g, b), min(r, g, b)
    v = max_c / 255
    chroma = max_c - min_c
    s = 0.0 if max_c == 0 else chroma / max_c
    if v < 0.18:
        return "black"
    if s < 0.20 or chroma < 28:
        if v >= 0.80:
            return "white"
        if v >= 0.55:
            return "silver"
        if v >= 0.30:
            return "grey"
        return "black"
    h = hue(r, g, b)
    if h < 12 or h >= 330:
        return "maroon" if v < 0.45 else "red"
    if h < 40:
        return "brown" if v < 0.55 else "orange"
    if h < 70:
        return "brown" if v < 0.50 else "yellow"
    if h < 165:
        return "green"
    if h < 290:
        return "blue"
    return "maroon"


def is_amber(r: int, g: int, b: int) -> bool:
    max_c, min_c = max(r, g, b), min(r, g, b)
    if max_c < 25:
        return False
    s = (max_c - min_c) / max_c
    h = hue(r, g, b)
    return s >= 0.30 and 15 <= h < 50


def _size(image: Sequence) -> tuple[int, int]:
    return len(image[0]), len(image)


def _pixel(image: Sequence, x: int, y: int) -> tuple[int, int, int]:
    p = image[y][x]
    return int(p[0]), int(p[1]), int(p[2])


def _clamp(box: Box, width: int, height: int) -> Box:
    left, top, right, bottom = box
    return (min(max(left, 0), width), min(max(top, 0), height),
            min(max(right, 0), width), min(max(bottom, 0), height))


def _area(box: Box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def body_region(width: int, height: int, plate: Optional[Box] = None,
                vehicle: Optional[Box] = None) -> Optional[Box]:
    region: Optional[Box] = None
    if plate is not None and _area(plate) > 0:
        pw, ph = plate[2] - plate[0], plate[3] - plate[1]
        region = (plate[0] - pw, plate[1] - ph * 2.2,
                  plate[2] + pw, plate[3] + ph * 0.3)
        if vehicle is not None:
            region = (max(region[0], vehicle[0]), max(region[1], vehicle[1]),
                      min(region[2], vehicle[2]), min(region[3], vehicle[3]))
    elif vehicle is not None and _area(vehicle) > 0:
        vw, vh = vehicle[2] - vehicle[0], vehicle[3] - vehicle[1]
        region = (vehicle[0] + vw * 0.15, vehicle[1] + vh * 0.35,
                  vehicle[2] - vw * 0.15, vehicle[1] + vh * 0.75)
    if region is None:
        return None
    clamped = _clamp(region, width, height)
    return clamped if _area(clamped) > 0 else None


def _scene_stats(image: Sequence) -> tuple[float, float]:
    width, height = _size(image)
    n = _SCENE_GRID
    luma, amber = 0.0, 0
    for gy in range(n):
        y = math.floor((gy + 0.5) * height / n)
        for gx in range(n):
            x = math.floor((gx + 0.5) * width / n)
            r, g, b = _pixel(image, x, y)
            luma += 0.299 * r + 0.587 * g + 0.114 * b
            if is_amber(r, g, b):
                amber += 1
    return luma / (n * n), amber / (n * n)


def classify(image: Sequence, plate: Optional[Box] = None,
             vehicle: Optional[Box] = None) -> ColourReading:
    width, height = _size(image)
    luma, amber_share = _scene_stats(image)
    low_light = luma < LOW_LIGHT_LUMA
    cast = luma < WARM_CAST_MAX_LUMA and amber_share >= WARM_CAST_SHARE

    region = body_region(width, height, plate, vehicle)
    if region is None or region[2] - region[0] < 4 or region[3] - region[1] < 4:
        return ColourReading(None, 0.0, low_light, cast)

    skip = None
    if plate is not None:
        pw, ph = plate[2] - plate[0], plate[3] - plate[1]
        skip = (plate[0] - pw * 0.15, plate[1] - ph * 0.15,
                plate[2] + pw * 0.15, plate[3] + ph * 0.15)
    votes: dict[str, int] = {}
    total = 0
    rw, rh = region[2] - region[0], region[3] - region[1]
    for gy in range(_GRID):
        y = region[1] + (gy + 0.5) * rh / _GRID
        for gx in range(_GRID):
            x = region[0] + (gx + 0.5) * rw / _GRID
            if skip and skip[0] <= x < skip[2] and skip[1] <= y < skip[3]:
                continue
            colour = classify_pixel(*_pixel(image, math.floor(x), math.floor(y)))
            votes[colour] = votes.get(colour, 0) + 1
            total += 1
    if total < 30:
        return ColourReading(None, 0.0, low_light, cast)
    # Ties keep the earlier colour, matching Dart's reduce.
    best = max(votes.items(), key=lambda kv: kv[1])
    share = best[1] / total
    return ColourReading(best[0] if share >= MIN_SHARE else None, share,
                         low_light, cast)
