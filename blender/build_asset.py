"""Build a DSX-01 asset inside headless Blender and save .blend / .glb.

Run through the Blender binary, not the system Python:

    blender -b -P blender/build_asset.py -- --asset dsx-01_full_ship \
        --blend models/blend/dsx-01_full_ship.blend \
        --glb   /tmp/dsx-01_full_ship.blender.glb

The geometry comes from the shared spec (see blender/lib/dsx_blender.py), so the
Blender scene is provably identical to the models shipped in models/glb.
"""

from __future__ import annotations

import json
import os
import sys


def _parse(argv: list[str]) -> dict:
    opts = {"asset": "dsx-01_full_ship", "blend": None, "glb": None}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--":
            i += 1
            continue
        if arg in ("--asset", "-a") and i + 1 < len(argv):
            opts["asset"] = argv[i + 1]
            i += 2
        elif arg == "--blend" and i + 1 < len(argv):
            opts["blend"] = argv[i + 1]
            i += 2
        elif arg == "--glb" and i + 1 < len(argv):
            opts["glb"] = argv[i + 1]
            i += 2
        else:
            i += 1
    return opts


def _builder_for(asset_id: str):
    from shipspec import constants as C
    from shipspec import decks as decks_mod
    from shipspec import hull as hull_mod
    from shipspec import interiors as interiors_mod
    from shipspec import propulsion as propulsion_mod

    if asset_id == "dsx-01_full_ship":
        return hull_mod.build_exterior()
    if asset_id.startswith("dsx-02_"):
        key = asset_id[len("dsx-02_"):]
        return decks_mod.build_deck(C.DECK_BY_KEY[key])
    if asset_id == "dsx-03_interior_compartments":
        return interiors_mod.build_interiors()
    if asset_id == "dsx-04_propulsion_system":
        return propulsion_mod.build_propulsion()
    raise SystemExit(f"unknown asset id: {asset_id}")


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    from lib import dsx_blender as bridge  # noqa: E402

    opts = _parse(sys.argv[1:])
    builder = _builder_for(opts["asset"])
    counts = bridge.build_builder_into_scene(builder, opts["asset"])

    result = {"asset": opts["asset"], **counts}
    if opts["blend"]:
        bridge.save_blend(opts["blend"])
        result["blend"] = opts["blend"]
        result["blendBytes"] = os.path.getsize(opts["blend"])
    if opts["glb"]:
        bridge.export_glb(opts["glb"])
        result["glb"] = opts["glb"]
        result["glbBytes"] = os.path.getsize(opts["glb"])

    print("DSX_BLENDER_RESULT " + json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
