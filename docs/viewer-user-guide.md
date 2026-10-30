# Viewer User Guide

The interactive workbench at `viewer/` lets you explore every DSX-01 asset in the
browser with no build step and no network access (Three.js is vendored).

## Start it

```bash
./scripts/serve.sh            # serves the repo root on :8000
# open http://localhost:8000/viewer/
```

Any static server rooted at the repository works; the viewer fetches
`../models/glb/manifest.json` and the `.glb` files relative to itself.

## Controls

| Area | What it does |
|---|---|
| **Assets** | Switch between the full ship, the four deck cutaways, the interior layout and the propulsion study. |
| **Systems** | Toggle any of the eleven ship systems on/off to isolate or peel apart the vessel (this is also how you isolate a single deck's hardware on the full ship). |
| **Explode** | Slider separates system groups radially from the hull centre for a maintenance-view explosion. |
| **Camera presets** | `hero`, `starboard`, `bow`, `stern`, `top`, `ring` (centrifuge close-up). |
| **Wireframe** | Show the underlying triangulation. |
| **Grid** | Reference grid on the ship's horizontal plane. |
| **Auto-rotate** | Slow turntable. |
| **Spin ring** | Animate the centrifuge gravity ring about the ship's axis. |
| **Starfield** | Background star shell. |
| **Mouse** | Drag = orbit, scroll = zoom, right-drag = pan, click a part = info panel. |

## Info panel

Clicking any component opens a panel reading that node's `extras`: part id,
system (resolved to a friendly label), deck, triangle count, bounding size in
metres, a one-line description and the material chips. Nothing here is
hard-coded — it all comes from the exporter metadata, so new components appear
automatically.

## HUD

Bottom-left shows the loaded asset's label, triangle/mesh/material counts and
overall dimensions in metres, recomputed from the live scene.

## Tips

- To study one deck on the full ship, untick every system except that deck's
  system, or load the dedicated deck asset for the fitted-interior cutaway.
- Combine **Explode** with a single enabled system to see how a subsystem
  (radiators, centrifuge, spine) attaches to the hull.
- The propulsion asset is a single-engine study; use the `stern` preset on the
  full ship to see all three drives in place.

## Limitations

- Rendering is real-time PBR with factor-only materials (no texture maps), so
  surfaces read as clean hard-surface metal/emissives rather than weathered hulls.
- On clients without WebGL the viewer degrades to parse-only mode: the asset and
  system lists, metadata and model parsing still work, but nothing rasterises.
