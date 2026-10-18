"""The printable parts: plaque, keychain, stand, test coupon and QR plaque.

A single-nozzle printer prints one color per layer. So every colored element
starts on top of the base and ends at the top of its own band (see
:data:`logo_3d.params.BANDS`): the filament changes at the first layer of each
band, and seen from above each element shows the color of its top layers. The
sides of the higher elements show thin stripes of the colors below; from the
front they do not show.

All parts print flat, with no overhangs, so no support material is needed.
"""

from __future__ import annotations

from functools import cache
from math import cos, radians, sin
from pathlib import Path

import segno
from build123d import (
    Align,
    Axis,
    Box,
    Circle,
    Location,
    Part,
    Pos,
    Rectangle,
    RectangleRounded,
    Rot,
    Sketch,
    Text,
    TextAlign,
    chamfer,
    extrude,
)

from logo_3d.mark import mark_outline, mark_sketches
from logo_3d.params import (
    BANDS,
    DEFAULT,
    EXTRUSION_WIDTH,
    MARK_CORNER,
    MARK_DOT_RADIUS,
    MARK_LOCAL,
    MARK_UNITS,
    QR_OVERLAP,
    Params,
)

#: Thickness of the stem of an "l" in Red Hat Display Bold, in units of the
#: font size: the thinnest stroke of the text.
STEM = 0.137

FONT = Path(__file__).with_name("fonts") / "RedHatDisplay-Bold.ttf"

#: Font size used to measure a text before it is scaled to its width.
_PROBE_SIZE = 10.0


def _raise(sketch: Sketch, p: Params, top: float) -> Part:
    """Extrude a flat sketch from the top of the base up to ``top``."""
    return Pos(0, 0, p.base_height) * extrude(sketch, amount=top - p.base_height)


def _raise_mark(part: Part, sketches: dict[str, Sketch], p: Params) -> Part:
    for band in BANDS:
        part += _raise(sketches[band], p, p.band_top(band))
    return part


@cache
def _text_width(text: str) -> float:
    return Text(text, _PROBE_SIZE, font_path=str(FONT)).bounding_box().size.X


def address_font_size(p: Params = DEFAULT) -> float:
    """Font size that makes the address exactly as wide as ``address_width``."""
    return _PROBE_SIZE * p.address_width / _text_width(p.address)


def text_sketch(text: str, size: float, centre_x: float, bottom: float) -> Sketch:
    """``text`` in Red Hat Display Bold, centred on ``centre_x``, lowest point at ``bottom``."""
    sketch = Text(text, size, font_path=str(FONT))
    box = sketch.bounding_box()
    return Pos(centre_x - box.center().X, bottom - box.min.Y, 0) * sketch


def build_plaque(p: Params = DEFAULT) -> Part:
    """The table plaque: the mark, and the address of the site under it."""
    p.validate()
    plaque = extrude(mark_outline(p.plaque_size), amount=p.base_height)
    plaque = _raise_mark(plaque, mark_sketches(p.plaque_scale, (0.0, p.plaque_mark_shift)), p)
    address = text_sketch(
        p.address, address_font_size(p), 0.0, -p.plaque_size / 2 + p.address_bottom
    )
    return plaque + _raise(address, p, p.band_top("gateway"))


def ring_hole_centre(p: Params = DEFAULT) -> tuple[float, float]:
    return (0.0, p.keychain_size / 2 - p.ring_hole_wall - p.ring_hole_dia / 2)


def build_keychain(p: Params = DEFAULT) -> Part:
    """A small copy of the mark, with a hole for a key ring at the top."""
    p.validate()
    hole = Pos(*ring_hole_centre(p), 0) * Circle(p.ring_hole_dia / 2)
    keychain = extrude(mark_outline(p.keychain_size) - hole, amount=p.base_height)
    return _raise_mark(keychain, mark_sketches(p.keychain_scale), p)


def name_font_size(p: Params = DEFAULT) -> float:
    """Font size that makes the longest line of the name ``name_width`` wide."""
    longest = max(_text_width(line) for line in p.name_text.split("|"))
    return _PROBE_SIZE * p.name_width / longest


def name_lines(p: Params = DEFAULT) -> list[Sketch]:
    """The lines of the name, centred on x = 0, the first one just under the mark.

    The lines are placed by their baselines, ``name_line_pitch`` font sizes
    apart, so a line with a g and a line without one keep the same rhythm.
    """
    size = name_font_size(p)
    mark_bottom = (MARK_LOCAL[-1][1] - MARK_DOT_RADIUS) * p.keychain_scale
    lines, baseline = [], None
    for line in p.name_text.split("|"):
        # Bottom alignment puts the baseline of the line at y = 0.
        text = Text(
            line, size, font_path=str(FONT), text_align=(TextAlign.CENTER, TextAlign.BOTTOM)
        )
        if baseline is None:
            baseline = mark_bottom - p.name_gap - text.bounding_box().max.Y
        else:
            baseline -= p.name_line_pitch * size
        lines.append(Pos(0, baseline, 0) * text)
    return lines


def build_keychain_name(p: Params = DEFAULT) -> Part:
    """The keychain with the name of the project under the mark.

    The top is the same as on :func:`build_keychain` (outline, mark and ring
    hole); the keychain is longer, to make room for the name, in the color of
    the gateway.
    """
    p.validate()
    if STEM * name_font_size(p) < 2 * EXTRUSION_WIDTH:
        raise ValueError("the name is too small to print: shorten the lines or widen them")
    lines = name_lines(p)
    top = p.keychain_size / 2
    bottom = min(line.bounding_box().min.Y for line in lines) - p.name_margin
    corner = MARK_CORNER * p.keychain_size / MARK_UNITS
    outline = Pos(0, (top + bottom) / 2, 0) * RectangleRounded(
        p.keychain_size, top - bottom, corner
    )
    hole = Pos(*ring_hole_centre(p), 0) * Circle(p.ring_hole_dia / 2)
    keychain = extrude(outline - hole, amount=p.base_height)
    keychain = _raise_mark(keychain, mark_sketches(p.keychain_scale), p)
    for line in lines:
        keychain += _raise(line, p, p.band_top("gateway"))
    return keychain


def slot_bottom(p: Params = DEFAULT) -> tuple[float, float, float]:
    """Centre of the floor of the slot, where the bottom edge of the plaque rests."""
    lean = radians(p.slot_lean)
    top_y = -p.stand_depth / 2 + p.slot_front
    return (0.0, top_y - p.slot_depth * sin(lean), p.stand_height - p.slot_depth * cos(lean))


def build_stand(p: Params = DEFAULT) -> Part:
    """A block with a slot that holds the plaque, leaning back by ``slot_lean``.

    The front of the stand is towards -y. The slot runs through the whole
    length, and its walls are only ``slot_lean`` degrees from the vertical, so
    it prints without support.
    """
    p.validate()
    block = Box(
        p.stand_length, p.stand_depth, p.stand_height, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    block = chamfer(block.edges().group_by(Axis.Z)[-1], p.stand_chamfer)
    # Long enough to leave the block through the top face at any lean.
    slot = Box(
        p.stand_length + 2,
        p.slot_width,
        p.slot_depth + p.stand_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    return block - Pos(*slot_bottom(p)) * Rot(-p.slot_lean, 0, 0) * slot


def on_stand(p: Params = DEFAULT) -> Location:
    """Where the plaque goes when it stands in the slot of the stand.

    Its front faces -y, like the front of the stand, and its bottom edge rests
    on the floor of the slot, in the middle of its width.
    """
    return (
        Pos(*slot_bottom(p))
        * Rot(90 - p.slot_lean, 0, 0)
        * Pos(0, p.plaque_size / 2, -p.base_height / 2)
    )


def build_coupon(p: Params = DEFAULT) -> Part:
    """A short test print: a color ladder and a sample of the address.

    The ladder has a row for each band, from the lowest (bottom row) to the
    highest. In a row, the pads from left to right have 1, 2, ... up to
    ``band_layers`` layers of that color, over the same colors that are under it
    in the logo. The thinnest pad that hides the color below shows how many
    layers a band needs.
    """
    p.validate()
    size = address_font_size(p)
    gap, pad_size = p.pad_gap, p.pad_size
    sample_height = Text(p.sample_text, size, font_path=str(FONT)).bounding_box().size.Y
    sample_width = _text_width(p.sample_text) * size / _PROBE_SIZE
    pads_width = p.band_layers * pad_size + (p.band_layers - 1) * gap
    # From the bottom: margin, sample text, gap, one row of pads per band with a
    # gap between rows, margin. Margins are two gaps, to clear the corners.
    width = max(pads_width, sample_width) + 4 * gap
    height = 2 * gap + sample_height + gap + len(BANDS) * (pad_size + gap) - gap + 2 * gap
    bottom = -height / 2

    coupon = extrude(RectangleRounded(width, height, gap), amount=p.base_height)
    pad = RectangleRounded(pad_size, pad_size, pad_size / 6)
    first_row = bottom + 2 * gap + sample_height + gap + pad_size / 2
    for row, band in enumerate(BANDS):
        y = first_row + row * (pad_size + gap)
        for count in range(1, p.band_layers + 1):
            x = -pads_width / 2 + pad_size / 2 + (count - 1) * (pad_size + gap)
            top = p.band_bottom(band) + count * p.layer_height
            coupon += _raise(Pos(x, y, 0) * pad, p, top)
    sample = text_sketch(p.sample_text, size, 0.0, bottom + 2 * gap)
    return coupon + _raise(sample, p, p.band_top("gateway"))


def qr_matrix(p: Params = DEFAULT) -> list[list[bool]]:
    """The modules of the QR code of ``qr_url``, rows from the top; True is dark."""
    code = segno.make(p.qr_url, error=p.qr_error, boost_error=False, micro=False)
    return [[bool(module) for module in row] for row in code.matrix]


def qr_module_size(p: Params = DEFAULT) -> float:
    """Side of one module: the code and its light margin fill the plaque above the slot.

    The bottom of the plaque goes into the slot of the stand, so the margin under
    the code starts ``slot_depth`` above the bottom edge: it stays whole when the
    plaque stands.
    """
    return (p.plaque_size - p.slot_depth) / (len(qr_matrix(p)) + 2 * p.qr_quiet_zone)


def qr_centre_y(p: Params = DEFAULT) -> float:
    """The code is half a slot above the centre of the plaque."""
    return p.slot_depth / 2


def _qr_sketch(matrix: list[list[bool]], module: float, centre_y: float) -> Sketch:
    """The dark modules, one rectangle for each run of them in a row, centred on x = 0."""
    half = len(matrix) * module / 2
    runs = []
    for row, cells in enumerate(matrix):
        col = 0
        while col < len(cells):
            if not cells[col]:
                col += 1
                continue
            start = col
            while col < len(cells) and cells[col]:
                col += 1
            x = -half + (start + col) * module / 2
            y = centre_y + half - (row + 0.5) * module
            size = (col - start) * module + 2 * QR_OVERLAP, module + 2 * QR_OVERLAP
            runs.append(Pos(x, y, 0) * Rectangle(*size))
    return Sketch() + runs


def build_qr_plaque(p: Params = DEFAULT) -> Part:
    """A plaque with the QR code of the site: dark modules on a light plate.

    It is as large and as thick as the plaque, so it stands in a second stand,
    with the code above the slot. The corners are rounded no more than the light
    margin is wide, so the margin stays whole at the corners of the code.
    """
    p.validate()
    matrix = qr_matrix(p)
    module = qr_module_size(p)
    margin = p.qr_quiet_zone * module
    if module < 5 * EXTRUSION_WIDTH:
        raise ValueError(f"QR modules of {module:.2f} mm are too small: make the plaque larger")
    plate = extrude(RectangleRounded(p.plaque_size, p.plaque_size, margin), amount=p.base_height)
    top = p.slabs("qr")[-1][2]
    return plate + _raise(_qr_sketch(matrix, module, qr_centre_y(p)), p, top)


def split_bands(part: Part, p: Params = DEFAULT, scheme: str = "logo") -> dict[str, Part]:
    """Cut ``part`` into one slab per color of its ``scheme`` (see ``SCHEMES``).

    The keys are the filaments of the scheme, from the bed up. A part of the
    "plain" scheme, the stand, comes back whole.
    """
    slabs = p.slabs(scheme)
    if len(slabs) == 1:
        return {slabs[0][0]: part}
    box = part.bounding_box()
    pieces = {}
    for name, low, high in slabs:
        cutter = Pos(box.center().X, box.center().Y, (low + high) / 2) * Box(
            box.size.X + 2, box.size.Y + 2, high - low
        )
        pieces[name] = part & cutter
    return pieces
