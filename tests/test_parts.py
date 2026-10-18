"""Checks of the parts: color bands, fits and printable sizes."""

from __future__ import annotations

from math import cos, radians, sin

import numpy as np
import pytest
import zxingcpp
from build123d import Circle, GeomType, Part, Pos, Sketch, Text, Vector, offset

from logo_3d import parts
from logo_3d.cli import main
from logo_3d.mark import mark_outline, mark_sketches
from logo_3d.params import (
    BANDS,
    DEFAULT,
    EXTRUSION_WIDTH,
    MARK_CLOUD,
    MARK_LOCAL,
    MARK_NODE,
    MARK_STROKE,
)

p = DEFAULT
#: Distance of a probe point from a surface.
EPS = 0.05


@pytest.fixture(scope="module")
def plaque() -> Part:
    return parts.build_plaque(p)


@pytest.fixture(scope="module")
def keychain() -> Part:
    return parts.build_keychain(p)


@pytest.fixture(scope="module")
def keychain_name() -> Part:
    return parts.build_keychain_name(p)


@pytest.fixture(scope="module")
def stand() -> Part:
    return parts.build_stand(p)


@pytest.fixture(scope="module")
def coupon() -> Part:
    return parts.build_coupon(p)


@pytest.fixture(scope="module")
def qr_plaque() -> Part:
    return parts.build_qr_plaque(p)


@pytest.fixture(scope="module")
def all_parts(plaque, keychain, keychain_name, stand, coupon, qr_plaque) -> dict[str, Part]:
    return {
        "plaque": plaque,
        "keychain": keychain,
        "keychain_name": keychain_name,
        "stand": stand,
        "coupon": coupon,
        "qr_plaque": qr_plaque,
    }


def _union(sketches: dict[str, Sketch]) -> Sketch:
    result = None
    for sketch in sketches.values():
        result = sketch if result is None else result + sketch
    return result


def _address(params=p) -> Sketch:
    return parts.text_sketch(
        params.address,
        parts.address_font_size(params),
        0.0,
        -params.plaque_size / 2 + params.address_bottom,
    )


# --- Layers and color changes ------------------------------------------------


def test_color_changes_fall_on_whole_layers():
    changes = p.color_changes()
    assert [c.layer for c in changes] == [13, 17, 21]
    for change in changes:
        assert change.top == pytest.approx(change.layer * p.layer_height)
        assert p.band_bottom(change.band) == pytest.approx((change.layer - 1) * p.layer_height)
    assert p.total_height == pytest.approx(p.total_layers * p.layer_height)


def test_qr_plaque_has_one_change_to_black():
    (change,) = p.color_changes("qr")
    assert (change.band, change.layer) == ("qr_code", p.base_layers + 1)
    assert change.top == pytest.approx(change.layer * p.layer_height)


def test_summary_names_every_change():
    text = p.summary()
    for change in p.color_changes() + p.color_changes("qr"):
        assert f"layer {change.layer:3d}" in text
        assert f"top {change.top:.2f} mm" in text


# --- Every part --------------------------------------------------------------


def test_parts_are_single_valid_solids(all_parts):
    for name, part in all_parts.items():
        assert part.is_valid, name
        assert len(part.solids()) == 1, name


def test_parts_fit_the_bed(all_parts):
    for name, part in all_parts.items():
        size = part.bounding_box().size
        assert size.X <= p.bed_x - 2 * p.bed_margin, name
        assert size.Y <= p.bed_y - 2 * p.bed_margin, name


def test_heights(all_parts):
    for name in ("plaque", "keychain", "keychain_name", "coupon"):
        box = all_parts[name].bounding_box()
        assert box.min.Z == pytest.approx(0.0), name
        assert box.max.Z == pytest.approx(p.total_height), name
    assert all_parts["stand"].bounding_box().max.Z == pytest.approx(p.stand_height)
    assert all_parts["qr_plaque"].bounding_box().max.Z == pytest.approx(p.slabs("qr")[-1][2])


def test_split_bands_keeps_all_the_material(plaque, stand):
    pieces = parts.split_bands(plaque, p)
    assert list(pieces) == ["base", *BANDS]
    assert all(piece.volume > 0 for piece in pieces.values())
    assert sum(piece.volume for piece in pieces.values()) == pytest.approx(plaque.volume, rel=1e-4)
    assert list(parts.split_bands(stand, p, "plain")) == ["base"]


# --- The mark: each element ends at the top of its band -----------------------


def _check_column(part: Part, x: float, y: float, top: float) -> None:
    """Material from the bed up to ``top`` at (x, y), and nothing above it."""
    assert part.is_inside(Vector(x, y, EPS)), (x, y)
    assert part.is_inside(Vector(x, y, top - EPS)), (x, y, top)
    assert not part.is_inside(Vector(x, y, top + EPS)), (x, y, top)


@pytest.mark.parametrize("name", ["plaque", "keychain", "keychain_name"])
def test_each_element_shows_its_own_color(name, all_parts):
    part = all_parts[name]
    if name == "plaque":
        scale, shift = p.plaque_scale, p.plaque_mark_shift
        empty = (-50.0, -30.0)
    elif name == "keychain":
        scale, shift = p.keychain_scale, 0.0
        empty = (-14.0, -14.0)
    else:
        scale, shift = p.keychain_scale, 0.0
        empty = (-14.0, 8.0)

    def at(point):
        return point[0] * scale, point[1] * scale + shift

    _check_column(part, *at(MARK_NODE), p.band_top("gateway"))
    _check_column(part, *at(MARK_CLOUD[-1]), p.band_top("cloud"))
    _check_column(part, *at(MARK_LOCAL[-1]), p.band_top("local"))
    _check_column(part, *empty, p.base_height)


def test_strokes_are_wide_enough_for_the_nozzle():
    assert MARK_STROKE * p.keychain_scale >= 4 * EXTRUSION_WIDTH
    # The stem of an "l" is the thinnest stroke of the address.
    stem = Text("l", parts.address_font_size(p), font_path=str(parts.FONT)).bounding_box().size.X
    assert stem >= 2 * EXTRUSION_WIDTH


# --- Plaque, keychain, stand ---------------------------------------------------


def test_address_has_the_planned_width_and_stays_clear():
    address = _address()
    assert address.bounding_box().size.X == pytest.approx(p.address_width, abs=0.01)
    assert address.bounding_box().min.Y == pytest.approx(-p.plaque_size / 2 + p.address_bottom)
    inner = offset(mark_outline(p.plaque_size), amount=-4.0)
    assert (address - inner).area < 1e-6, "the address is closer than 4 mm to the edge"
    mark = _union(mark_sketches(p.plaque_scale, (0.0, p.plaque_mark_shift)))
    assert (address & offset(mark, amount=4.0)).area < 1e-6, "the address touches the mark"


@pytest.mark.parametrize("name", ["keychain", "keychain_name"])
def test_ring_hole_goes_through_and_clears_the_mark(name, all_parts):
    keychain = all_parts[name]
    x, y = parts.ring_hole_centre(p)
    assert not keychain.is_inside(Vector(x, y, p.base_height / 2))
    assert keychain.is_inside(Vector(x, y + p.ring_hole_dia / 2 + EPS, p.base_height / 2))
    mark = _union(mark_sketches(p.keychain_scale))
    grown = Pos(x, y, 0) * Circle(p.ring_hole_dia / 2 + 2 * EXTRUSION_WIDTH)
    assert (mark & grown).area < 1e-6


def test_name_is_printable_and_stays_clear(keychain_name, keychain):
    lines = parts.name_lines(p)
    assert len(lines) == len(p.name_text.split("|"))
    widths = [line.bounding_box().size.X for line in lines]
    assert max(widths) == pytest.approx(p.name_width, abs=0.01)
    assert parts.STEM * parts.name_font_size(p) >= 2 * EXTRUSION_WIDTH
    # The lines do not touch: two extrusions at least between them. (A 2D offset
    # of the letters fails in OpenCascade, so the check measures the distance.)
    for upper, lower in zip(lines, lines[1:], strict=False):
        assert upper.distance_to(lower) >= 2 * EXTRUSION_WIDTH
    mark = _union(mark_sketches(p.keychain_scale))
    assert min(line.distance_to(mark) for line in lines) >= p.name_gap - EPS
    # Every letter stands on the plate, at least 2 mm from the edge.
    box = keychain_name.bounding_box()
    for line in lines:
        text_box = line.bounding_box()
        assert text_box.min.X >= box.min.X + 2 and text_box.max.X <= box.max.X - 2
        assert text_box.min.Y >= box.min.Y + 2
    # The name is in the color of the gateway: it fills the top band, on top of
    # what the keychain without the name has there.
    text_area = sum(line.area for line in lines)
    named = parts.split_bands(keychain_name, p)["gateway"].volume
    plain = parts.split_bands(keychain, p)["gateway"].volume
    assert named - plain == pytest.approx(text_area * p.band_height, rel=1e-3)


def _plaque_in_stand(plaque: Part, sink: float = 0.0) -> Part:
    """The plaque in the slot; ``sink`` moves it further down along its own plane."""
    return parts.on_stand(p) * Pos(0, -sink, 0) * plaque


def test_qr_plaque_stands_in_the_slot_too(qr_plaque, stand):
    assert (stand & _plaque_in_stand(qr_plaque)).volume < 1e-3


def test_plaque_stands_in_the_slot(plaque, stand):
    placed = _plaque_in_stand(plaque)
    assert (stand & placed).volume < 1e-3, "the plaque does not fit the slot"
    # It rests on the floor of the slot: a little lower would cut into it.
    assert (stand & _plaque_in_stand(plaque, sink=0.2)).volume > 1e-3
    # It leans back by slot_lean, away from the people in front of it.
    top = placed.faces().sort_by(lambda face: face.center().Z)[-1].center()
    assert top.Y > parts.slot_bottom(p)[1]
    lean = radians(p.slot_lean)
    height = p.plaque_size * cos(lean) + p.base_height * sin(lean)
    assert placed.bounding_box().size.Z == pytest.approx(height, abs=0.01)


def test_stand_hides_no_part_of_the_address():
    assert p.address_bottom > p.slot_depth + 2


# --- Coupon --------------------------------------------------------------------


def test_coupon_has_a_pad_for_every_layer_count(coupon):
    tops = {
        round(face.center().Z, 3)
        for face in coupon.faces().filter_by(GeomType.PLANE)
        if face.normal_at().Z > 0.99
    }
    expected = {round(p.base_height, 3)}
    for band in BANDS:
        for count in range(1, p.band_layers + 1):
            expected.add(round(p.band_bottom(band) + count * p.layer_height, 3))
    assert tops == expected


# --- QR plaque -------------------------------------------------------------------


def _sample_modules(qr_plaque: Part) -> list[list[bool]]:
    """Read the code back from the solid: a dark module is material at its top height."""
    size = len(parts.qr_matrix(p))
    module = parts.qr_module_size(p)
    half = size * module / 2
    centre = parts.qr_centre_y(p)
    top = p.slabs("qr")[-1][2]
    return [
        [
            qr_plaque.is_inside(
                Vector(
                    -half + (col + 0.5) * module, centre + half - (row + 0.5) * module, top - EPS
                )
            )
            for col in range(size)
        ]
        for row in range(size)
    ]


def test_qr_plaque_carries_the_code_of_the_site(qr_plaque):
    modules = _sample_modules(qr_plaque)
    assert modules == parts.qr_matrix(p)
    # Decode it like a phone would: dark modules on a light margin of four modules.
    image = np.full((len(modules) + 8, len(modules) + 8), 255, dtype=np.uint8)
    image[4:-4, 4:-4] = np.where(np.array(modules), 0, 255)
    image = np.kron(image, np.ones((8, 8), dtype=np.uint8))
    texts = [result.text for result in zxingcpp.read_barcodes(image)]
    assert texts == [p.qr_url]


def test_qr_margin_stays_whole_above_the_stand(qr_plaque):
    module = parts.qr_module_size(p)
    margin = p.qr_quiet_zone * module
    assert module >= 5 * EXTRUSION_WIDTH
    half = len(parts.qr_matrix(p)) * module / 2
    centre = parts.qr_centre_y(p)
    top = p.slabs("qr")[-1][2]
    # Nothing dark just outside each side of the code.
    outside = [(0, centre + half), (0, centre - half), (half, centre), (-half, centre)]
    for (x, y), (dx, dy) in zip(outside, [(0, EPS), (0, -EPS), (EPS, 0), (-EPS, 0)], strict=True):
        assert not qr_plaque.is_inside(Vector(x + dx, y + dy, top - EPS)), (x, y)
    # A full margin above the code, and above the slot of the stand under it.
    assert p.plaque_size / 2 - (centre + half) == pytest.approx(margin)
    above_slot = (centre - half) - (-p.plaque_size / 2 + p.slot_depth)
    assert above_slot == pytest.approx(margin)
    assert p.plaque_size / 2 - half >= margin


# --- Parameters and command line ------------------------------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"keychain_size": 12.0},
        {"slot_depth": 20.0},
        {"band_layers": 0},
        {"plaque_size": 230.0},
        {"address": "  "},
        {"qr_error": "x"},
        {"qr_quiet_zone": 2},
        {"name_text": "sovereign-||selfheal"},
        {"name_line_pitch": 0.8},
    ],
)
def test_validate_refuses_bad_parameters(changes):
    with pytest.raises(ValueError):
        p.replace(**changes).validate()


def test_cli_exports_the_keychain(tmp_path, capsys):
    assert main(["--only", "keychain", "--no-step", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "keychain.stl").stat().st_size > 0
    assert (tmp_path / "keychain.3mf").stat().st_size > 0
    assert "layer  13" in capsys.readouterr().out


def test_cli_previews_the_plaques_on_their_stands(tmp_path):
    assert main(["--preview", "--no-step", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "plaque_on_stand.png").stat().st_size > 0
    assert (tmp_path / "qr_plaque_on_stand.png").stat().st_size > 0
    # The preview of the QR plaque is readable too.
    from PIL import Image

    image = Image.open(tmp_path / "qr_plaque_top.png")
    assert [result.text for result in zxingcpp.read_barcodes(image)] == [p.qr_url]


def test_cli_reports_bad_parameters(tmp_path, capsys):
    assert main(["--only", "keychain", "--band-layers", "0", "--out", str(tmp_path)]) == 2
    assert "invalid parameters" in capsys.readouterr().out
