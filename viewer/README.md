# DSX-01 Interactive 3D Viewer

A dependency-light, offline-capable Three.js workbench for the
**ISV Kairos Horizon (DSX-01)** deep space exploration vessel. It loads the
glTF-binary assets produced by `scripts/build_models.py` and lets you explore
the complete ship, each isolated deck, the interior compartment layout and the
fusion torch drive study.

Everything is vendored — `three.module.js`, `OrbitControls`, `GLTFLoader` and
`BufferGeometryUtils` live in `viewer/vendor/`, so the viewer runs with no
network access and no build step.

## Running

The viewer fetches models over HTTP, so it must be served (not opened via
`file://`). From the repository root:

```bash
./scripts/serve.sh            # defaults to port 8000
# then open http://localhost:8000/viewer/
```

Or with any static server rooted at the repository:

```bash
python3 -m http.server 8000
# open http://localhost:8000/viewer/
```

## Features

- **Asset switcher** — full ship, four deck-level models, interior
  compartments, propulsion system (read from `models/glb/manifest.json`).
- **System isolation** — toggle any of the eleven ship systems (hull, command,
  operations, habitat, engineering, spine, thermal, centrifuge, propulsion,
  sensors, utility) to peel the vessel apart.
- **Exploded view** — slider separates system groups radially from the hull
  centre.
- **Camera presets** — hero, starboard, bow, stern, top and a centrifuge-ring
  close-up.
- **Info panel** — click any component to read its `partId`, system, deck,
  triangle count, bounding size, description and material list. All of this is
  driven by the node `extras` written by the exporter; the viewer hard-codes
  nothing about model structure.
- **Toggles** — wireframe, reference grid, auto-rotate, centrifuge ring spin,
  starfield.
- **Live HUD** — triangle / mesh / material counts and overall dimensions for
  the loaded asset.

## Layout

```
viewer/
  index.html            importmap + UI shell
  src/main.js           application logic (ES module)
  src/styles.css        dark sci-fi theme
  vendor/               three.module.js + addons (controls, loaders, utils)
```

## Coordinate frame

The exporter converts the ship's Z-up frame (`+X` bow, `+Y` starboard, `+Z` up)
to glTF's Y-up convention. In the viewer, "up" is therefore glTF `+Y`, and the
ship's longitudinal axis lies along glTF `+X`. The centrifuge spin rotates the
`SYS_CENTRIFUGE` group about that axis.

## Extending

Add a new asset by registering it in `shipspec/assembly.py` (`ASSETS`) and
re-running `scripts/build_models.py`; the manifest and the viewer's asset
switcher pick it up automatically.
