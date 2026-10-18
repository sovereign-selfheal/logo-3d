"""Command line entry point: build the parts and write the export files."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import fields
from pathlib import Path
from typing import get_type_hints

from build123d import Mesher, Part, Unit, export_step, export_stl

from logo_3d.params import DEFAULT, FILAMENTS, PETG_DENSITY, Params
from logo_3d.parts import build_coupon, build_keychain, build_plaque, build_stand, split_bands

DEFAULT_OUT = Path("out")

#: The parts, in the order they are exported.
PARTS: dict[str, Callable[[Params], Part]] = {
    "plaque": build_plaque,
    "keychain": build_keychain,
    "stand": build_stand,
    "coupon": build_coupon,
}

#: Chordal tolerance for STL and 3MF: well below what the printer resolves.
#: The text makes many small curves, so a finer value only adds triangles.
MESH_TOLERANCE = 0.01


def _add_param_options(parser: argparse.ArgumentParser) -> None:
    """Expose every field of :class:`Params` as a command line option."""
    group = parser.add_argument_group("parameters", "override any value in Params")
    # Resolved, not read as text: params.py uses postponed annotations, so
    # field.type is a string.
    hints = get_type_hints(Params)
    for field in fields(Params):
        flag = "--" + field.name.replace("_", "-")
        kind = hints[field.name]
        group.add_argument(
            flag,
            type=kind,
            metavar=kind.__name__,
            help=f"default: {getattr(DEFAULT, field.name)}",
        )


def params_from_args(args: argparse.Namespace) -> Params:
    """Fold the command line overrides into the default parameter set."""
    overrides = {
        field.name: getattr(args, field.name)
        for field in fields(Params)
        if getattr(args, field.name, None) is not None
    }
    return DEFAULT.replace(**overrides)


def export_part(part: Part, out_dir: Path, stem: str, step: bool = True) -> list[Path]:
    """Write ``part`` as STL and 3MF, and optionally STEP.

    STL is what every slicer reads, 3MF carries the units so nothing gets
    scaled by mistake, and STEP keeps the real surfaces for more CAD work.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    stl_path = out_dir / f"{stem}.stl"
    export_stl(part, stl_path, tolerance=MESH_TOLERANCE)
    written.append(stl_path)

    mesh_path = out_dir / f"{stem}.3mf"
    mesher = Mesher(unit=Unit.MM)
    mesher.add_shape(part, linear_deflection=MESH_TOLERANCE)
    mesher.write(mesh_path)
    written.append(mesh_path)

    if step:
        step_path = out_dir / f"{stem}.step"
        export_step(part, step_path)
        written.append(step_path)
    return written


def describe(name: str, part: Part, p: Params) -> str:
    """Size of a part and the filament of each color, as solid material.

    The slicer fills the inside with sparse infill, so the real figures are
    lower; the split between the colors is what matters here.
    """
    box = part.bounding_box()
    grams = ", ".join(
        f"{FILAMENTS[band].name.removeprefix('Prusament PETG ')} "
        f"{piece.volume / 1000 * PETG_DENSITY:.1f} g"
        for band, piece in split_bands(part, p).items()
    )
    return (
        f"{name}: {box.size.X:.1f} x {box.size.Y:.1f} x {box.size.Z:.2f} mm; solid material {grams}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logo-3d-export",
        description="Generate the printable logo parts of the Sovereign Self-Healing demo.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"directory for the exported files (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--only",
        choices=(*PARTS, "all"),
        default="all",
        help="which part to export (default: all)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="also render colored PNG views (needs the preview extra)",
    )
    parser.add_argument(
        "--no-step",
        action="store_true",
        help="skip the STEP export, the slowest of the three",
    )
    _add_param_options(parser)
    return parser


def _render_previews(part: Part, out_dir: Path, stem: str, p: Params) -> list[Path]:
    """Render previews; explain a missing extra instead of failing.

    The geometry is already written at this point, so a missing plotting
    library should not turn the run into an error.
    """
    try:
        from logo_3d.preview import STAND_VIEWS, VIEWS, render_views
    except ImportError:
        print(
            "note: previews need the optional extra; install it with "
            "`uv sync --extra preview`. The geometry was exported normally."
        )
        return []
    return render_views(part, out_dir, stem, p, STAND_VIEWS if stem == "stand" else VIEWS)


def _render_on_stand(plaque: Part, stand: Part, out_dir: Path, p: Params) -> list[Path]:
    """Render the plaque standing in the stand; like :func:`_render_previews`."""
    try:
        from logo_3d.preview import render_on_stand
    except ImportError:
        return []
    return [render_on_stand(plaque, stand, out_dir / "plaque_on_stand.png", p)]


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    params = params_from_args(args)
    names = list(PARTS) if args.only == "all" else [args.only]

    written: list[Path] = []
    built: dict[str, Part] = {}
    # The build is inside the guard too: a parameter set that validate() does
    # not reject yet should still reach the user as a sentence, not as an
    # OpenCascade traceback.
    try:
        params.validate()
        print(params.summary())
        print()
        for name in names:
            part = PARTS[name](params)
            # The name of the object in the 3MF file, and in the slicer.
            part.label = name
            built[name] = part
            print(describe(name, part, params))
            written += export_part(part, args.out, name, step=not args.no_step)
            if args.preview:
                written += _render_previews(part, args.out, name, params)
        if args.preview and "plaque" in built and "stand" in built:
            written += _render_on_stand(built["plaque"], built["stand"], args.out, params)
    except (ValueError, RuntimeError) as error:
        print(f"invalid parameters: {error}")
        return 2

    print()
    for path in written:
        print(f"wrote {path} ({path.stat().st_size / 1024:.0f} kB)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
