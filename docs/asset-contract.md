# Asset Contract

The machine-readable agreement between the exporter, the models, the viewer and
the tests. Anything that consumes a DSX-01 asset may rely on the guarantees
below; anything that produces one must uphold them.

## Files

- `models/glb/<asset>.glb` — glTF 2.0 binary, Y-up, one file per asset.
- `models/glb/manifest.json` — registry: asset id, filename, category, label,
  byte size, node/mesh/triangle/vertex/material counts, bounds, round-trip
  stats, plus the top-level `systems` map and `totals`.
- `models/blend/<asset>.blend` — native Blender original (master: full ship).
- `assets/preview/<asset>__<view>.png` — software-rendered stills.

## Scene hierarchy

- Exactly one glTF scene; its root nodes are **system groups** named by system
  id (`SYS_HULL`, `SYS_COMMAND`, …). Group `extras` carry
  `{groupId, groupLabel}`.
- Each group's children are **part nodes** (glTF nodes with a `mesh`). One node
  per logical component; a node's mesh has one primitive per material.
- No transform is baked into part nodes beyond identity; all geometry is in the
  asset's shared frame, so parts keep their true position.

## Node extras (part nodes)

Every part node MUST carry:

| Key | Type | Meaning |
|---|---|---|
| `partId` | string | stable component id, e.g. `HULL_PressureShell_HabBlock` |
| `label` | string | human-readable name for UI |
| `system` | string | one of `C.SYSTEMS` keys |
| `deck` | int or null | 1..4 when the part belongs to a deck, else null |
| `materials` | string[] | material names used by this part |
| `description` | string | one-sentence blurb for the info panel |
| `tags` | string[] | free-form facets for filtering |
| `bounds` | object | `{min:[3], max:[3]}` in export frame (added by writer) |
| `triangleCount` | int | triangles in this node (added by writer) |

The writer injects `bounds` and `triangleCount`; builders supply the rest.

## Scene extras

The glTF scene carries a self-describing block: `project`, `vessel`,
`registry`, `vesselClass`, `buildYard`, `crewComplement`, `missionProfile`,
`units` ("metre"), `shipFrame`, `exportFrame`, `systems` (id→label),
`dimensions`, and per-asset `assetId`, `category`, `label` plus, where relevant,
`deck`, `decks`, `performance`, `summary`, `compartments`. The viewer reads
`systems` from the manifest and per-part data from node extras; it never
hard-codes structure.

## Materials

- Names come exclusively from `C.MATERIALS`.
- Emitted as glTF `pbrMetallicRoughness` (baseColorFactor, metallicFactor,
  roughnessFactor), `emissiveFactor`, `alphaMode` (`OPAQUE`/`BLEND`) and
  `doubleSided`.
- The viewer and Blender map these 1:1; no texture images are used (pure
  procedural PBR factors), keeping assets small and dependency-free.

## Frame and units

- Source frame: ship Z-up metres. Export frame: glTF Y-up via
  `[[1,0,0],[0,0,1],[0,-1,0]]`.
- `bounds` in extras/manifest are in the **export** frame.
- Lengths are metres; the viewer displays dimensions directly.

## Indices and accessors

- POSITION accessors carry `min`/`max` (glTF requirement).
- Indices use `UNSIGNED_SHORT` when the mesh fits, else `UNSIGNED_INT`.
- Buffer views are 4-byte aligned; a single binary chunk per file.

## Validation

- `tests/test_glb_assets.py` enforces: files parse, counts match the manifest,
  bounds finite/positive, part nodes carry the required extras, materials are
  known, index counts are multiples of three, POSITION has min/max.
- `scripts/validate_blender.py` enforces triangle/mesh parity between the
  Python and Blender exporters.
