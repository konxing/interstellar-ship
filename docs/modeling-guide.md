# Modelling Guide

How the DSX-01 geometry is generated, and how to extend it. The entire vessel is
**procedural**: there are no hand-authored meshes. Everything derives from
`shipspec/constants.py` through a small NumPy kernel, so a change to one
constant propagates consistently to the glTF models, the Blender original, the
previews and the tests.

## Architecture

```
shipspec/constants.py   frozen dimensions, decks, systems, materials   <- single source of truth
geometry/mesh.py        NumPy mesh kernel: primitives, transforms, merge
geometry/glb.py         glTF 2.0 binary writer + reader (PBR, extras, Z-up->Y-up)
shipspec/part.py        Part/Builder bookkeeping; multi-material primitives
shipspec/fixtures.py    reusable detail components (consoles, bunks, dishes, ...)
shipspec/hull.py        full exterior assembly
shipspec/decks.py       per-deck cutaway band + fitted compartments
shipspec/interiors.py   interior compartment layout + service corridor
shipspec/propulsion.py  fusion torch drive study
shipspec/assembly.py    scene assembly + asset registry (ASSETS)
scripts/build_models.py export all assets -> models/glb/*.glb + manifest
blender/                native Blender bridge -> models/blend/*.blend
scripts/render_preview.py  software rasteriser -> assets/preview/*.png
viewer/                 Three.js workbench over models/glb
```

## The kernel in one paragraph

A `Mesh` holds `vertices (N,3)`, `normals (N,3)` and `indices (M,3)` as NumPy
arrays. Primitives (`primitive_box`, `primitive_cylinder`, `primitive_sphere`,
`primitive_torus`, `primitive_tube`, `primitive_prism`, `primitive_loft`,
`lattice_truss`, `grid_panel`, `beam_between`) return meshes in local space;
`translate/rotate/scale/mirror/transform` move them; `merge` concatenates.
`primitive_loft` sweeps a 2-D profile along +X to make the hull; `clip_profile_to_band`
(decks) slices a profile to a deck's Z range with Sutherland–Hodgman so each deck
cutaway matches the hull exactly.

## Parts, materials and nodes

A `Part` is one logical component. It may combine meshes with different
materials; `Part.multi` merges meshes that share a material so the exporter
emits **one glTF mesh with several primitives** — the viewer therefore sees one
selectable node per component, not dozens of fragments. Each part carries
`extras` (partId, label, system, deck, materials, description, tags) that
survive into glTF node extras and drive the viewer's info panel.

`Builder.scene(..., group_by=...)` wraps parts into one `GroupNode` per system,
which is what makes system isolation work identically in glTF, Blender
collections and the viewer.

## Adding a new component

1. If it is reusable detail, add a fixture in `shipspec/fixtures.py` returning a
   `Fixture` (list of `(mesh, material)` in local space).
2. In the appropriate builder (`hull.py`, `decks.py`, `interiors.py`,
   `propulsion.py`), register a part:
   `builder.multi("SYSX_Name", "Human Label", "SYS_X", primitives, deck=n,
   description="...", tags=(...))`.
3. Use only material names from `C.MATERIALS` and system ids from `C.SYSTEMS`
   (enforced by `tests/test_spec_consistency.py`).
4. Re-run `scripts/build_models.py`, `scripts/run_tests.py` and, if the shape
   changed, `scripts/render_preview.py --all`.

## Adding a new asset

Register it in `shipspec/assembly.py::ASSETS` (asset id, filename, category,
label, build callable). `scripts/build_models.py`, the manifest, the viewer's
asset switcher and the test suite all pick it up automatically. Add it to
`blender/build_all.sh::ASSETS` if it should also have a `.blend`.

## Regenerating everything

```bash
python3 scripts/build_models.py --report reports/model-validation.json
./blender/build_all.sh                      # optional .blend originals
python3 scripts/validate_blender.py /tmp/dsx_blender_glbs   # cross-check
python3 scripts/run_tests.py
python3 scripts/render_preview.py --all
./scripts/serve.sh                          # then open /viewer/
```

## Conventions

- Units are metres; ship frame Z-up (see design specification §2).
- Keep triangle budgets modest: the kernel targets clean low-poly hard-surface
  geometry, not subdivision surfaces.
- Never hard-code model structure in the viewer; read it from node extras.
- No third-party runtime dependencies beyond NumPy. Blender and Three.js are the
  only external tools, and Three.js is vendored.
