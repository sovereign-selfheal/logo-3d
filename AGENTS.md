# AGENTS.md: `logo-3d` repository

Guidance for AI coding agents and humans working in this repo. Read it fully before you change anything.

## 1. Purpose

The logo of the demo as printable parts, for events where the demo is presented (the first one is
Linux Day Milano, 2026-10-24): a table plaque with the address of the site, a plaque with a QR code of
the site, keychains (one with the name of the project), a stand for the plaques and a test coupon.
The model is written in build123d and exported to STL, 3MF and STEP. This repo changes no cluster,
and no other repo depends on it.

## 2. Contracts

| Owner | Items |
|---|---|
| `logo-3d` (this repo) | The parts, their parameters, the color bands and the spools (`src/logo_3d/params.py`) |
| `sovereign-selfheal.github.io` | The mark: `favicon.svg`. The `MARK_*` constants copy its geometry; when the favicon changes, change them and export again. The address of the site is in `address` and in `qr_url` |

## 3. Rules

1. **One color per layer.** The printer has one nozzle. Every colored element starts on top of the
   base and ends at the top of its own band (`BANDS` in `params.py`). The base and every band are
   whole numbers of layers, so each color change falls on a layer. The exporter prints the table of
   the changes; keep it, the README table and the tests in step.
2. **No support material.** Every part prints flat, with vertical walls. The only slanted walls are
   the ones of the slot of the stand, at `slot_lean` degrees from the vertical (keep it under 45).
3. **Printable sizes.** The strokes of the mark stay at four extrusions (0.4 mm) or more, the strokes
   of the text at two or more. `Params.validate()` refuses combinations that give a part you cannot
   use; add a check there when you find a new one.
4. **Every dimension in `params.py`.** The model code has no millimetre values. Each field of
   `Params` is also an option of the exporter.
5. **Only the mark of the demo.** Never add the Red Hat logo or another trademark to a part.
6. **A QR code that every phone reads.** Dark modules on a light plate, error correction `q` or
   higher, a light margin of four modules, modules of five extrusions or more. The tests read the
   code back from the solid and decode it with zxing-cpp; keep that test.

## 4. Layout

```
src/logo_3d/
  params.py     every dimension, the favicon geometry, the spools and the bands
  mark.py       the mark as flat sketches, one per band
  parts.py      plaque, keychains, stand, coupon and QR plaque; on_stand() places a plaque in the stand,
                split_bands() cuts a part by color
  preview.py    colored PNG previews (matplotlib)
  cli.py        the exporter (scripts/export.py runs it from the repo)
  fonts/        Red Hat Display Bold and its license (SIL OFL 1.1)
tests/          geometry checks
docs/           the previews of the README
```

## 5. Conventions

- **Python tools with uv** (`uv sync`, `uv run`), never pip. `uv.lock` and `.python-version` are
  committed. build123d is pinned; change the pin on purpose and run the tests.
- On a Linux machine without a desktop, OpenCascade still needs `libGL.so.1` and `libX11.so.6` at
  import time (README, "Getting started").
- **Tests for every change** (`uv run pytest -q`); `uv run ruff check .` must pass.
- `out/` is not committed. When the look changes, export with `--preview` and copy the new images
  into `docs/`.
- Comments, docs and commit messages in **English**, level B2/C1: short, clear sentences, no idioms.
