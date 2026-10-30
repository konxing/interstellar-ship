# Blender pipeline

Native Blender sources and the headless bridge that regenerates them. The
Blender scene is built from the **same** NumPy geometry kernel and design
constants as the shipped glTF models (`shipspec/`, `geometry/`), so the
`.blend` originals can never drift from `models/glb/*.glb`.

## Layout

```
blender/
  build_asset.py     headless entry point: build one asset -> .blend / .glb
  build_all.sh       loop over all seven assets
  lib/
    dsx_blender.py   bridge: spec Part -> Blender object, materials, collections
```

## Requirements

- Blender 3.0+ (`blender` on PATH). The bridge uses only `bpy` and NumPy.
- The repository root must be intact (the bridge imports `shipspec`/`geometry`
  by adding the repo root to `sys.path`).

## Usage

Build the master original (full ship) plus a cross-check GLB:

```bash
blender -b -P blender/build_asset.py -- \
    --asset dsx-01_full_ship \
    --blend models/blend/dsx-01_full_ship.blend \
    --glb   /tmp/dsx-01_full_ship.blender.glb
```

Build every asset's `.blend` (and optional cross-check GLBs):

```bash
./blender/build_all.sh                    # -> models/blend/*.blend
./blender/build_all.sh --with-glb /tmp/x  # also -> /tmp/x/*.blender.glb
```

## Scene organisation

- One top-level **Collection** per asset, with a child collection per ship
  system (`SYS_HULL`, `SYS_COMMAND`, …), mirroring the glTF group hierarchy so
  system isolation works identically in Blender and the web viewer.
- One **Object** per spec `Part`, with a material slot per material and a
  per-face material index — matching the multi-primitive glTF meshes.
- Custom properties `partId`, `label`, `system`, `deck`, `description` on every
  object, so metadata survives a round trip through Blender.
- Materials are Principled BSDF nodes populated from the spec material library
  (base colour, metallic, roughness, emission, alpha blend, backface culling).

## Coordinate frame

Blender is Z-up natively and the ship frame is Z-up (`+X` bow, `+Y` starboard,
`+Z` up), so no conversion is applied inside the `.blend`. The glTF exporter
(`export_yup=True`) performs the Z-up → Y-up conversion on export, matching the
Python writer.

## Cross-validation

`scripts/run_tests.py` (and `reports/blender-validation.json`) compare the
Blender-exported GLB against the Python-exported GLB. Triangle and mesh counts
must match exactly; vertex counts intentionally differ because Blender splits
vertices per face for normals/UVs, and the material count differs because
Blender emits only materials actually referenced.
