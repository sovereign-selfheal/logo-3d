"""Colored previews of the parts, to check the look without a slicer.

Each part is cut into the slab of the base and the slab of each band, and every
slab is drawn in the color of its filament. So the preview shows what the
printer makes: the top of each element in its own color, and on the sides the
stripes of the colors below.

Importing this module needs the optional ``preview`` extra (matplotlib).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

# Chosen before pyplot is imported: previews go to files, and an interactive
# backend fails on a machine without a display.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  (must follow the backend choice)
import numpy as np  # noqa: E402
from build123d import Part  # noqa: E402
from matplotlib.colors import to_rgb  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from logo_3d.params import DEFAULT, FILAMENTS, Params  # noqa: E402
from logo_3d.parts import split_bands  # noqa: E402

#: Views rendered by default, as (name, elevation, azimuth) in degrees.
VIEWS = (("top", 90.0, -90.0), ("iso", 35.0, -60.0))
#: The stand from the side shows the lean of the slot.
STAND_VIEWS = (("iso", 35.0, -60.0), ("side", 0.0, 0.0))


def _eye_vector(elev: float, azim: float) -> np.ndarray:
    """Unit vector from the scene towards the camera."""
    e, a = np.radians(elev), np.radians(azim)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def _triangles(part: Part, tolerance: float = 0.05) -> np.ndarray:
    """The surface of ``part`` as an ``(n, 3, 3)`` array of triangle corners."""
    vertices, faces = part.tessellate(tolerance)
    points = np.array([(v.X, v.Y, v.Z) for v in vertices])
    return points[np.array(faces)]


def render(part: Part, path: Path, elev: float, azim: float, p: Params = DEFAULT) -> Path:
    """Draw one view of ``part``, colored by band, and write it to ``path``."""
    eye = _eye_vector(elev, azim)
    light = eye + np.array([0.3, 0.2, 0.6])
    light /= np.linalg.norm(light)

    fig = plt.figure(figsize=(9, 9), dpi=100)
    ax = fig.add_subplot(projection="3d")
    ax.set_proj_type("ortho")
    # One collection per slab, drawn from the lowest to the highest. Seen from
    # above, a slab can only hide the slabs below it, and matplotlib's depth
    # sort of single triangles gets this wrong with the large faces of the base.
    ax.computed_zorder = False

    all_tris = []
    for order, (name, piece) in enumerate(split_bands(part, p).items()):
        tris = _triangles(piece)
        normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        lengths = np.linalg.norm(normals, axis=1, keepdims=True)
        normals = np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)
        # Facets that face away from the camera are dropped: depth sorting alone
        # cannot resolve the inside of the letters and of the slot.
        keep = normals @ eye > 1e-6
        tris, normals = tris[keep], normals[keep]
        shade = 0.45 + 0.55 * np.clip(normals @ light, 0, 1)
        base = np.array(to_rgb(FILAMENTS[name].preview))
        colors = np.clip(shade[:, None] * base[None, :], 0, 1)
        # Edges in the color of their face hide the seams between triangles.
        faces = Poly3DCollection(tris, facecolors=colors, edgecolors=colors, linewidths=0.3)
        faces.set_zorder(order)
        ax.add_collection3d(faces)
        all_tris.append(tris)

    corners = np.concatenate(all_tris).reshape(-1, 3)
    centre = (corners.max(axis=0) + corners.min(axis=0)) / 2
    reach = (corners.max(axis=0) - corners.min(axis=0)).max() / 2
    for axis, mid in zip("xyz", centre, strict=True):
        getattr(ax, f"set_{axis}lim")(mid - reach, mid + reach)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)
    return path


def render_views(
    part: Part,
    out_dir: Path,
    stem: str,
    p: Params = DEFAULT,
    views: tuple[tuple[str, float, float], ...] = VIEWS,
) -> list[Path]:
    """Render each view of ``views`` and return the files written."""
    return [
        render(part, out_dir / f"{stem}_{name}.png", elev, azim, p) for name, elev, azim in views
    ]
