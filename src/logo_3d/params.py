"""Every dimension of the printed logo lives here.

The model code reads measured values and derived properties from :class:`Params`;
it never hard-codes a number. All lengths are millimetres and all angles are
degrees, as in build123d.

The mark is the favicon of the demo site (``favicon.svg`` in the
``sovereign-selfheal.github.io`` repository): a dark rounded square with a red
line that ends in a node, the gateway, where it splits into two curves: one to
the cloud model (amber, up) and one to the local model (teal, down). The
``MARK_*`` constants copy its geometry in the 32 units of the SVG view box,
moved so that the centre of the square is the origin, with the y axis up.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import NamedTuple

#: Extrusion width of a 0.4 mm nozzle. Thin features stay at two extrusions or
#: more, so the slicer can draw them with real perimeters.
EXTRUSION_WIDTH = 0.4

#: Small separate parts of a text, such as a hyphen or the dot of an i, are made
#: at least this thick. On the first printed keychain the hyphen of Red Hat
#: Display Bold was 0.77 mm thick, and it did not print.
MIN_ISLAND = 3 * EXTRUSION_WIDTH

#: Density of PETG, for the filament estimate (Prusament PETG data sheet).
PETG_DENSITY = 1.27

# --- The mark, in the units of the favicon's 32 x 32 view box ---------------
MARK_UNITS = 32.0
#: Corner radius of the square (``rx`` in the SVG).
MARK_CORNER = 8.0
#: Width of the line and of the two curves.
MARK_STROKE = 2.4
#: The line, from its round end to the node.
MARK_LINE = ((-10.0, 0.0), (-3.0, 0.0))
#: The node where the line splits.
MARK_NODE = (-3.0, 0.0)
MARK_NODE_RADIUS = 3.2
#: Control points of the two cubic Bezier curves. Each curve ends in a dot.
MARK_CLOUD = ((-3.0, 0.0), (2.0, 0.0), (2.0, 7.0), (9.0, 7.0))
MARK_LOCAL = ((-3.0, 0.0), (2.0, 0.0), (2.0, -7.0), (9.0, -7.0))
MARK_DOT_RADIUS = 2.4


class Filament(NamedTuple):
    """A spool of the print, and the color that stands for it in the previews."""

    name: str
    preview: str


class ColorChange(NamedTuple):
    """A filament change: the first layer of a band and the height of its top."""

    band: str
    layer: int
    top: float


#: The colored parts of the logo, from the lowest to the highest. Each one has
#: its own band of layers on top of the base, and the filament changes at the
#: first layer of each band. The gateway is the highest: its node covers the
#: point where the two curves start, as in the SVG.
BANDS = ("local", "cloud", "gateway")

#: The spools: all Prusament PETG, so one temperature profile fits all of them.
#: The preview colors only approximate the real filaments.
FILAMENTS = {
    "base": Filament("Prusament PETG Jet Black", "#262626"),
    "local": Filament("Prusament PETG Jungle Green", "#2f8a46"),
    "cloud": Filament("Prusament PETG Yellow Gold", "#d8a62a"),
    "gateway": Filament("Prusament PETG Lipstick Red", "#c3102b"),
    # The QR plaque is dark on light, the only way that every phone reads it.
    "qr_base": Filament("Prusament PETG Signal White", "#e8e8e8"),
    "qr_code": Filament("Prusament PETG Jet Black", "#262626"),
}

#: What each color is used for.
BAND_CONTENT = {
    "base": "the plate",
    "local": "curve and dot of the local model",
    "cloud": "curve and dot of the cloud model",
    "gateway": "line and node of the gateway, and the address",
    "qr_base": "the plate of the QR plaque",
    "qr_code": "the QR code",
}

#: The colors of each kind of part, from the bed up: the base, then one band of
#: ``band_layers`` layers for each next color.
SCHEMES = {
    "logo": ("base", *BANDS),
    "qr": ("qr_base", "qr_code"),
    # The stand: one color from the bottom to the top.
    "plain": ("base",),
}

#: The modules of the QR code grow by this much on each side. Two modules that
#: touch only at a corner then overlap a little, and the solid stays manifold.
QR_OVERLAP = 0.01


@dataclass(frozen=True)
class Params:
    """Parameters of the printed parts, grouped by what they control."""

    # --- Printer and slicer ---------------------------------------------------
    #: Layer height of the slicer profile, also for the first layer. The base
    #: and the color bands are whole numbers of layers, so every color change
    #: falls exactly on a layer.
    layer_height: float = 0.2
    #: Layers of the base plate: 12 layers make 2.4 mm.
    base_layers: int = 12
    #: Layers of each color band. PETG can be a little translucent, so four
    #: layers (0.8 mm) hide the color below. The test coupon shows whether
    #: fewer layers are enough.
    band_layers: int = 4
    #: Print area of the Prusa MK4.
    bed_x: float = 250.0
    bed_y: float = 210.0
    #: Distance kept from the edges of the bed.
    bed_margin: float = 5.0

    # --- Plaque ---------------------------------------------------------------
    #: Side of the plaque, a rounded square like the favicon.
    plaque_size: float = 140.0
    #: The mark moves up by this much, to make room for the address below it.
    plaque_mark_shift: float = 9.0
    #: Text under the mark, in the color of the gateway.
    address: str = "sovereign-selfheal.github.io"
    #: Width of the line of text; the font size follows from it.
    address_width: float = 112.0
    #: Height of the lowest point of the text (the tail of the g) above the
    #: bottom edge of the plaque. It keeps the text clear of the stand.
    address_bottom: float = 16.0

    # --- Keychain -------------------------------------------------------------
    #: Side of a keychain.
    keychain_size: float = 40.0
    #: Hole for the key ring, at the top centre, so the logo hangs straight.
    ring_hole_dia: float = 5.0
    #: Material between the hole and the top edge.
    ring_hole_wall: float = 2.5

    # --- Keychain with the name -----------------------------------------------
    # As wide as the keychain and with the same mark and hole, but longer: the
    # name of the project goes under the mark, in the color of the gateway.
    #: The name; "|" starts a new line. On one line, 40 mm wide, its strokes
    #: would be too thin to print. No hyphen at the end of the first line: at
    #: this size it was too thin and did not print.
    name_text: str = "sovereign|selfheal"
    #: Width of the longest line; the font size follows from it.
    name_width: float = 34.0
    #: Distance between two baselines, in units of the font size: the tail of
    #: the g stays clear of the letters of the next line.
    name_line_pitch: float = 1.12
    #: Gap between the mark and the text.
    name_gap: float = 2.5
    #: Margin under the text, down to the bottom edge.
    name_margin: float = 3.5

    # --- Stand ----------------------------------------------------------------
    #: The stand is a block with a slot that holds the plaque, leaning back.
    stand_length: float = 90.0
    stand_depth: float = 45.0
    stand_height: float = 16.0
    #: How far the plaque goes into the slot, measured along the plaque.
    slot_depth: float = 10.0
    #: Gap between the plaque and the slot. Loose on purpose: the plaque leans
    #: on the back of the slot, so the fit does not need to be tight.
    slot_clearance: float = 0.6
    #: Angle of the plaque from the vertical.
    slot_lean: float = 15.0
    #: Distance from the front edge of the stand to the slot, on the top face.
    slot_front: float = 14.0
    #: Chamfer of the top edges of the stand.
    stand_chamfer: float = 1.5

    # --- Test coupon ----------------------------------------------------------
    #: Side of a square pad of the color ladder.
    pad_size: float = 6.0
    #: Gap between the pads, and between the pads and the edge.
    pad_gap: float = 3.0
    #: Part of the address, at the size it has on the plaque.
    sample_text: str = "github.io"

    # --- QR plaque ------------------------------------------------------------
    # As large and as thick as the plaque, so it stands in a second stand.
    #: Address in the QR code.
    qr_url: str = "https://sovereign-selfheal.github.io/"
    #: Error correction of the code: l, m, q or h. With "q" a reader still
    #: decodes the code when a quarter of it is damaged, for example by a string
    #: of filament.
    qr_error: str = "q"
    #: Light margin around the code, in modules. Readers need four.
    qr_quiet_zone: int = 4

    # --- Derived values -------------------------------------------------------

    @property
    def base_height(self) -> float:
        return self.base_layers * self.layer_height

    @property
    def band_height(self) -> float:
        return self.band_layers * self.layer_height

    def band_bottom(self, band: str) -> float:
        """Height where a color band starts: the top of the band below it."""
        return self.base_height + BANDS.index(band) * self.band_height

    def band_top(self, band: str) -> float:
        return self.band_bottom(band) + self.band_height

    @property
    def total_height(self) -> float:
        """Height of the highest band, the top of every part but the stand."""
        return self.band_top(BANDS[-1])

    @property
    def total_layers(self) -> int:
        return self.base_layers + len(BANDS) * self.band_layers

    @property
    def plaque_scale(self) -> float:
        """Millimetres per unit of the favicon, on the plaque."""
        return self.plaque_size / MARK_UNITS

    @property
    def keychain_scale(self) -> float:
        """Millimetres per unit of the favicon, on a keychain."""
        return self.keychain_size / MARK_UNITS

    @property
    def slot_width(self) -> float:
        return self.base_height + self.slot_clearance

    def slabs(self, scheme: str = "logo") -> list[tuple[str, float, float]]:
        """The slab of each color of a part: (filament, bottom, top), from the bed up."""
        base, *bands = SCHEMES[scheme]
        slabs = [(base, 0.0, self.base_height)]
        for index, band in enumerate(bands):
            bottom = self.base_height + index * self.band_height
            slabs.append((band, bottom, bottom + self.band_height))
        return slabs

    def color_changes(self, scheme: str = "logo") -> list[ColorChange]:
        """One filament change per band, at the first layer of the band."""
        changes = []
        for band, bottom, _top in self.slabs(scheme)[1:]:
            layer = round(bottom / self.layer_height) + 1
            changes.append(ColorChange(band, layer, layer * self.layer_height))
        return changes

    def replace(self, **changes: object) -> Params:
        return replace(self, **changes)

    def validate(self) -> None:
        """Refuse a parameter set that gives a part you cannot print or use."""
        problems = []
        if not 0.05 <= self.layer_height <= 0.3:
            problems.append(f"layer height {self.layer_height} mm is outside 0.05-0.3 mm")
        if self.base_layers < 6:
            problems.append("the base needs at least 6 layers to be stiff")
        if self.band_layers < 1:
            problems.append("each color band needs at least one layer")
        stroke = MARK_STROKE * self.keychain_scale
        if stroke < 4 * EXTRUSION_WIDTH:
            problems.append(
                f"on a {self.keychain_size} mm keychain the curves are {stroke:.2f} mm wide, "
                f"less than four extrusions"
            )
        usable_x = self.bed_x - 2 * self.bed_margin
        usable_y = self.bed_y - 2 * self.bed_margin
        if self.plaque_size > min(usable_x, usable_y):
            problems.append(f"a {self.plaque_size} mm plaque does not fit the bed")
        if self.stand_length > usable_x or self.stand_depth > usable_y:
            problems.append("the stand does not fit the bed")
        if self.ring_hole_wall < 3 * EXTRUSION_WIDTH:
            problems.append("the wall above the ring hole is thinner than three extrusions")
        if self.slot_clearance < 0.2:
            problems.append("a slot clearance under 0.2 mm will not take the plaque")
        if not 0 <= self.slot_lean <= 30:
            problems.append("lean the plaque between 0 and 30 degrees")
        if self.slot_depth + 2 > self.address_bottom:
            problems.append("the stand would hide the address: raise address_bottom")
        slot_floor = self.stand_height - self.slot_depth
        if slot_floor < 3:
            problems.append("the slot is too deep for the height of the stand")
        if not self.address.strip() or not self.sample_text.strip():
            problems.append("the address and the sample text must not be empty")
        if not all(line.strip() for line in self.name_text.split("|")):
            problems.append("the name of the keychain has an empty line")
        if self.name_line_pitch < 1.0:
            problems.append("lines of the name closer than 1.0 font size would touch")
        if not self.qr_url.strip():
            problems.append("the QR code needs an address")
        if self.qr_error not in ("l", "m", "q", "h"):
            problems.append(f"QR error correction {self.qr_error!r} is not one of l, m, q, h")
        if self.qr_quiet_zone < 4:
            problems.append("QR readers need a light margin of at least four modules")
        if problems:
            raise ValueError("; ".join(problems))

    def summary(self) -> str:
        """The layer plan, with the color changes to set in the slicer."""
        lines = [
            f"Layers of {self.layer_height:.2f} mm: base {self.base_height:.2f} mm "
            f"({self.base_layers} layers), then {len(BANDS)} color bands of "
            f"{self.band_height:.2f} mm ({self.band_layers} layers) each.",
            f"Start with {FILAMENTS['base'].name}: {BAND_CONTENT['base']}.",
            "Color changes (PrusaSlicer, after slicing: select the layer on the vertical "
            "slider and click +):",
        ]
        for change in self.color_changes():
            lines.append(
                f"  layer {change.layer:3d}  (top {change.top:.2f} mm)  "
                f"{FILAMENTS[change.band].name:30s} {BAND_CONTENT[change.band]}"
            )
        lines.append(
            f"Last layer: {self.total_layers} (top {self.total_height:.2f} mm). "
            f"The stand has no color changes."
        )
        qr_base, qr_code = self.slabs("qr")
        (change,) = self.color_changes("qr")
        lines += [
            "",
            f"QR plaque: start with {FILAMENTS[qr_base[0]].name}: {BAND_CONTENT[qr_base[0]]}.",
            f"  layer {change.layer:3d}  (top {change.top:.2f} mm)  "
            f"{FILAMENTS[change.band].name:30s} {BAND_CONTENT[change.band]}",
            f"Last layer: {round(qr_code[2] / self.layer_height)} (top {qr_code[2]:.2f} mm).",
        ]
        return "\n".join(lines)


DEFAULT = Params()
