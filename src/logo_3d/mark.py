"""The mark of the demo as flat sketches, one per color band.

The geometry comes from the favicon constants in :mod:`logo_3d.params`, scaled
to millimetres. :mod:`logo_3d.parts` raises each sketch to the top of its band.
"""

from __future__ import annotations

from build123d import Bezier, Circle, Pos, RectangleRounded, Sketch, SlotCenterToCenter, trace

from logo_3d.params import (
    MARK_CLOUD,
    MARK_CORNER,
    MARK_DOT_RADIUS,
    MARK_LINE,
    MARK_LOCAL,
    MARK_NODE,
    MARK_NODE_RADIUS,
    MARK_STROKE,
    MARK_UNITS,
)

Point = tuple[float, float]


def mark_sketches(scale: float, centre: Point = (0.0, 0.0)) -> dict[str, Sketch]:
    """Return the mark at ``scale`` millimetres per favicon unit, by band.

    The keys are the names in :data:`logo_3d.params.BANDS`. The ends of the
    curves are flat, but each one is inside a circle (the node or a dot), so the
    visible shape matches the round line caps of the SVG.
    """

    def at(point: Point) -> tuple[float, float, float]:
        return (centre[0] + point[0] * scale, centre[1] + point[1] * scale, 0.0)

    stroke = MARK_STROKE * scale

    # The line has a visible round end on the left: a slot gives it. Its right
    # end is inside the node.
    start, end = at(MARK_LINE[0]), at(MARK_LINE[1])
    line = Pos((start[0] + end[0]) / 2, start[1], 0) * SlotCenterToCenter(end[0] - start[0], stroke)
    node = Pos(*at(MARK_NODE)) * Circle(MARK_NODE_RADIUS * scale)

    def curve(points: tuple[Point, ...]) -> Sketch:
        path = Bezier(*(at(point) for point in points))
        dot = Pos(*at(points[-1])) * Circle(MARK_DOT_RADIUS * scale)
        return trace(path, line_width=stroke) + dot

    return {"local": curve(MARK_LOCAL), "cloud": curve(MARK_CLOUD), "gateway": line + node}


def mark_outline(size: float) -> Sketch:
    """The rounded square of the favicon, ``size`` millimetres wide."""
    return RectangleRounded(size, size, MARK_CORNER * size / MARK_UNITS)
