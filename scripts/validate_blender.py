#!/usr/bin/env python3
"""Cross-validate the Python glTF exporter against Blender's glTF exporter.

Compares each shipped model in models/glb/ with a Blender-exported GLB of the
same asset and writes reports/blender-validation.json.

Usage
-----
    python3 scripts/validate_blender.py /tmp/dsx_blender_glbs
    python3 scripts/validate_blender.py            # defaults to /tmp/dsx_blender_glbs

Triangle and mesh counts must match exactly. Vertex counts intentionally differ
(Blender splits vertices per face for normals/UVs) and the material count
differs (Blender emits only referenced materials), so those are reported but not
treated as failures.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from geometry.glb import read_glb  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blender_dir", nargs="?", default="/tmp/dsx_blender_glbs")
    parser.add_argument("--report", default=os.path.join(_ROOT, "reports", "blender-validation.json"))
    args = parser.parse_args(argv)

    glb_dir = os.path.join(_ROOT, "models", "glb")
    manifest = json.load(open(os.path.join(glb_dir, "manifest.json"), encoding="utf-8"))

    entries = []
    failures = []
    for asset in manifest["assets"]:
        ours = os.path.join(glb_dir, asset["filename"])
        theirs = os.path.join(args.blender_dir, asset["filename"].replace(".glb", ".blender.glb"))
        if not os.path.exists(theirs):
            entries.append({"assetId": asset["assetId"], "status": "missing-blender-glb"})
            continue
        a = read_glb(ours)["stats"]
        b = read_glb(theirs)["stats"]
        tris_ok = a["triangleCount"] == b["triangleCount"]
        meshes_ok = a["meshCount"] == b["meshCount"]
        ok = tris_ok and meshes_ok
        if not ok:
            failures.append(asset["assetId"])
        entries.append({
            "assetId": asset["assetId"],
            "status": "pass" if ok else "FAIL",
            "python": {"triangles": a["triangleCount"], "vertices": a["vertexCount"],
                       "meshes": a["meshCount"], "materials": a["materialCount"]},
            "blender": {"triangles": b["triangleCount"], "vertices": b["vertexCount"],
                        "meshes": b["meshCount"], "materials": b["materialCount"]},
            "trianglesMatch": tris_ok,
            "meshesMatch": meshes_ok,
        })

    report = {
        "purpose": "Cross-validate Python glTF exporter vs Blender glTF exporter",
        "blenderDir": args.blender_dir,
        "assets": entries,
        "allMatch": not failures,
        "failures": failures,
    }
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    for e in entries:
        if "python" in e:
            print(f"  {e['assetId']:<30} {e['status']:<5} "
                  f"py_tris={e['python']['triangles']:<7} bl_tris={e['blender']['triangles']:<7}")
        else:
            print(f"  {e['assetId']:<30} {e['status']}")
    print(f"report -> {args.report}")
    print("ALL MATCH:" , report["allMatch"])
    return 0 if report["allMatch"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
