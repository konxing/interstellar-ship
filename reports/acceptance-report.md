# Acceptance Report — DSX-01 *ISV Kairos Horizon*

Measured results for the delivery, against `docs/acceptance-criteria.md`.
Generated on the `feat/spaceship-3d-workbench` branch.

## Summary

| Metric | Value |
|---|---|
| Branch | `feat/spaceship-3d-workbench` (main carries only the skeleton commit) |
| Feature commits | 4 staged milestone commits on top of the skeleton |
| Tracked files | 61 across assets/, blender/, geometry/, models/, reports/, scripts/, shipspec/, tests/, viewer/ |
| GLB assets | 7 (262 056 triangles, 8.3 MB) |
| Blender original | `models/blend/dsx-01_full_ship.blend` (6.5 MB, 29 objects) |
| Preview stills | 14 PNGs in `assets/preview/` |
| Automated tests | 33 passed, 0 failed (`scripts/run_tests.py`) |
| Blender↔Python cross-validation | all 7 assets match on triangle & mesh counts |
| Viewer smoke test | headless Chromium logs `DSX_VIEWER_READY` and builds the full UI/metadata |

## A. Repository & process — PASS

- A1 PASS: all source is inside the repository root; no external/temp project.
- A2 PASS: `main` = `c1685d2` (skeleton) only; all work is on the feature branch.
- A3 PASS: one clear English commit per milestone (geometry+export → viewer+previews → Blender → tests).
- A4 PASS: tree contains only generated models, docs, vendored three.js and source; `.gitignore` excludes caches; no credentials.

## B. Models — PASS

| Asset | Triangles | Vertices | Meshes | Materials | Bounds (m, export frame) |
|---|---|---|---|---|---|
| dsx-01_full_ship | 67 720 | 64 217 | 29 | 35 | 492.0 × 104.3 × 102.8 |
| dsx-02_deck_01_command | 16 984 | 23 009 | 7 | 35 | 140 × 8 × 64 |
| dsx-02_deck_02_operations | 14 508 | 20 236 | 6 | 35 | 140 × 9 × 64 |
| dsx-02_deck_03_habitat | 39 232 | 40 473 | 7 | 35 | 140 × 9 × 67 |
| dsx-02_deck_04_engineering | 21 144 | 26 391 | 7 | 35 | 140 × 8 × 64 |
| dsx-03_interior_compartments | 70 252 | 79 123 | 14 | 35 | 382 × 14 × 44 |
| dsx-04_propulsion_system | 32 216 | 25 283 | 9 | 35 | 50 × 27 × 28 |

- B5 PASS: every GLB round-trips through `geometry.glb.read_glb`; counts in the
  file equal the manifest (`roundTrip.matchesBuild = true` for all).
- B6 PASS: Blender-exported GLBs match the Python exporter on triangles and
  meshes for all seven assets (`reports/blender-validation.json`, allMatch=true).
  Vertex counts differ by design (Blender splits verts per face); material counts
  differ because Blender emits only referenced materials.
- B7 PASS: every part node carries partId/label/system/deck/materials/
  description/tags/bounds/triangleCount.

## C. Viewer — PASS

- C1 PASS: `viewer/` ships vendored three r160 (module + OrbitControls +
  GLTFLoader + BufferGeometryUtils); runs from any static server, no build step.
- C2 PASS: headless Chromium (software GL unavailable) still fetched the
  manifest, built the 7-asset switcher and 11-system isolation list, parsed the
  full-ship GLB (11 groups, radius 256.7 m) and logged `DSX_VIEWER_READY`.
  On a WebGL client the same code path rasterises; explode, presets, ring spin,
  wireframe/grid/starfield and the click-to-inspect panel are wired in
  `viewer/src/main.js`.
- C3 PASS: system labels resolve from the manifest `systems` map and part detail
  from node extras; no model structure is hard-coded.

## D. Documentation & validation — PASS

- D1 PASS: `docs/design-specification.md`, `docs/modeling-guide.md`,
  `docs/asset-contract.md`, `docs/viewer-user-guide.md`, `docs/acceptance-criteria.md`.
- D2 PASS: 33/33 tests green (geometry kernel, shipped assets, spec coherence).
- D3 PASS: this report.
- D4 PASS: 14 preview stills (full ship ×5 views, each deck, interior ×2, propulsion ×2).

## E. Deployability — PASS

- E1 PASS: `scripts/build_models.py` regenerates all assets with NumPy only;
  Blender step optional (`blender/build_all.sh`).
- E2 PASS: `scripts/serve.sh` + `viewer/README.md`.
- E3 PASS: `scripts/publish.sh <owner>` pushes the branch and prints PR guidance.

## Known limitations (honest)

- Materials are PBR **factors only** (no texture maps); surfaces read as clean
  hard-surface metal/emissives.
- The software preview renderer is a flat-shaded rasteriser for stills only;
  final interactive rendering is the Three.js viewer.
- WebGL rasterisation could not be screenshot-verified in this headless
  environment (no GPU); the viewer's data path was verified headlessly instead.
- Only the full-ship `.blend` is committed to keep the repository lean; the
  other six are one command away via `blender/build_all.sh`.
