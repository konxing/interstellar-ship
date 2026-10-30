# Acceptance Criteria

The checklist the delivery is measured against. Each criterion states the
requirement, how it is verified, and where the evidence lives. The filled-in
results are in `reports/acceptance-report.md`.

## A. Repository & process

| # | Criterion | Verification |
|---|---|---|
| A1 | All source lives in the `deep-space-exploration-ship` repo root (no stray temp project). | `git ls-files` shows geometry/, shipspec/, scripts/, blender/, viewer/, models/, docs/, tests/, reports/, assets/. |
| A2 | Work happens on branch `feat/spaceship-3d-workbench`; `main` untouched beyond the initial skeleton. | `git log main..HEAD` contains all feature commits; `main` has only the skeleton commit. |
| A3 | Committed at each important stage with clear English messages. | `git log --oneline` shows one commit per milestone. |
| A4 | No secrets, tokens or personal data committed. | No credential patterns in tree; `.gitignore` covers caches; only generated models/docs. |

## B. Models

| # | Criterion | Verification |
|---|---|---|
| B1 | Blender original model + modelling scripts present. | `models/blend/dsx-01_full_ship.blend`; `blender/build_asset.py`, `blender/build_all.sh`, `blender/lib/dsx_blender.py`. |
| B2 | Complete ship GLB present. | `models/glb/dsx-01_full_ship.glb` (67 720 tris). |
| B3 | Four deck-level models present. | `models/glb/dsx-02_deck_0{1..4}_*.glb`. |
| B4 | Interior compartment + propulsion models present. | `models/glb/dsx-03_interior_compartments.glb`, `dsx-04_propulsion_system.glb`. |
| B5 | All GLBs are well-formed glTF 2.0 binary and round-trip. | `tests/test_glb_assets.py`; `reports/model-validation.json` round-trip block. |
| B6 | Blender and Python exporters agree. | `reports/blender-validation.json` (triangle/mesh parity, all pass). |
| B7 | Models are self-describing for tooling. | `tests/test_glb_assets.py::test_mesh_nodes_carry_viewer_extras`; `docs/asset-contract.md`. |

## C. Viewer

| # | Criterion | Verification |
|---|---|---|
| C1 | Interactive Three.js viewer present and offline-capable. | `viewer/` with vendored three r160; `viewer/README.md`. |
| C2 | Loads every asset and exposes isolation/explode/presets/info. | `viewer/src/main.js`; headless smoke test logs `DSX_VIEWER_READY` per asset. |
| C3 | Viewer reads structure from metadata, not hard-coded names. | Info panel + system list built from node extras / manifest. |

## D. Documentation & validation

| # | Criterion | Verification |
|---|---|---|
| D1 | Design spec, modelling guide, asset contract, viewer guide present. | `docs/*.md`. |
| D2 | Test suite present and green. | `scripts/run_tests.py` → 33 passed, 0 failed. |
| D3 | Acceptance report summarises measured results. | `reports/acceptance-report.md`. |
| D4 | Preview imagery for every asset. | `assets/preview/*.png` (14 stills). |

## E. Deployability

| # | Criterion | Verification |
|---|---|---|
| E1 | Project regenerates from source with only NumPy (+ optional Blender). | `docs/modeling-guide.md` "Regenerating everything". |
| E2 | Viewer serves from any static server rooted at the repo. | `scripts/serve.sh`; `viewer/README.md`. |
| E3 | Publish helper provided for pushing the branch and opening a PR. | `scripts/publish.sh`. |
