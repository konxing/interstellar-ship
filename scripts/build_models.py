#!/usr/bin/env python3
"""Export every DSX-01 asset to glTF binary (.glb).

Usage
-----
    python3 scripts/build_models.py               # all assets
    python3 scripts/build_models.py --asset dsx-01_full_ship
    python3 scripts/build_models.py --list
    python3 scripts/build_models.py --out models/glb --report reports/model-validation.json

The script is dependency-free (NumPy only) and writes each scene with the
shared glTF writer, then reads every file back to confirm the binary round-trips
and to collect triangle/vertex/material statistics. A machine-readable manifest
is emitted alongside the models so the viewer and the test suite read the same
source of truth.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

# Make the repository root importable when run as a script.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from geometry.glb import read_glb, write_glb  # noqa: E402
from shipspec import assembly, constants as C  # noqa: E402


def _human_bytes(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def build_all(out_dir: str, only: set[str] | None = None, report_path: str | None = None) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    manifest = {
        "project": "Deep Space Exploration Ship - 3D Modelling Workbench",
        "vessel": C.VESSEL_NAME,
        "registry": C.VESSEL_REGISTRY,
        "generator": assembly.GENERATOR,
        "units": "metre",
        "exportFrame": "glTF 2.0 binary, Y-up",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "systems": dict(C.SYSTEMS),
        "assets": [],
    }

    total_tris = 0
    total_bytes = 0
    for asset in assembly.ASSETS:
        if only and asset.asset_id not in only:
            continue
        path = os.path.join(out_dir, asset.filename)
        t0 = time.time()
        scene = asset.build()
        stats = write_glb(path, scene, generator=assembly.GENERATOR, convert_z_up=True)
        dt = time.time() - t0
        size = os.path.getsize(path)

        # Read back to prove the binary is well-formed.
        rt = read_glb(path)
        rt_stats = rt["stats"]

        entry = {
            "assetId": asset.asset_id,
            "filename": asset.filename,
            "category": asset.category,
            "label": asset.label,
            "deckKey": asset.deck_key,
            "bytes": size,
            "bytesHuman": _human_bytes(size),
            "buildSeconds": round(dt, 3),
            "nodes": stats["nodeCount"],
            "meshes": stats["meshCount"],
            "primitives": stats.get("primitiveCount", rt_stats.get("primitiveCount")),
            "triangleCount": stats["triangleCount"],
            "vertexCount": stats["vertexCount"],
            "materialCount": stats["materialCount"],
            "bounds": stats.get("bounds"),
            "roundTrip": {
                "version": rt_stats.get("version"),
                "byteLength": rt_stats.get("byteLength"),
                "nodes": rt_stats.get("nodeCount"),
                "meshes": rt_stats.get("meshCount"),
                "materials": rt_stats.get("materialCount"),
                "accessors": rt_stats.get("accessorCount"),
                "bufferViews": rt_stats.get("bufferViewCount"),
                "triangleCount": rt_stats.get("triangleCount"),
                "vertexCount": rt_stats.get("vertexCount"),
                "matchesBuild": (
                    rt_stats.get("triangleCount") == stats["triangleCount"]
                    and rt_stats.get("vertexCount") == stats["vertexCount"]
                    and rt_stats.get("meshCount") == stats["meshCount"]
                ),
            },
        }
        manifest["assets"].append(entry)
        total_tris += stats["triangleCount"]
        total_bytes += size
        print(
            f"  wrote {asset.filename:<34} "
            f"{_human_bytes(size):>9}  "
            f"tris={stats['triangleCount']:<8} nodes={stats['nodeCount']:<4} "
            f"({dt:.2f}s)"
        )

    manifest["totals"] = {
        "assetCount": len(manifest["assets"]),
        "triangleCount": total_tris,
        "bytes": total_bytes,
        "bytesHuman": _human_bytes(total_bytes),
    }

    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"  manifest -> {manifest_path}")

    if report_path:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
        print(f"  report   -> {report_path}")

    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export DSX-01 assets to .glb")
    parser.add_argument("--out", default="models/glb", help="output directory")
    parser.add_argument("--asset", action="append", help="export only this asset id (repeatable)")
    parser.add_argument("--list", action="store_true", help="list asset ids and exit")
    parser.add_argument("--report", default=None, help="also write the manifest to this path")
    args = parser.parse_args(argv)

    if args.list:
        for asset in assembly.ASSETS:
            print(f"{asset.asset_id:<32} {asset.category:<12} {asset.filename}")
        return 0

    out_dir = args.out
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(_ROOT, out_dir)
    report = args.report
    if report and not os.path.isabs(report):
        report = os.path.join(_ROOT, report)

    print(f"Exporting DSX-01 assets -> {out_dir}")
    only = set(args.asset) if args.asset else None
    if only:
        unknown = only - {a.asset_id for a in assembly.ASSETS}
        if unknown:
            parser.error(f"unknown asset id(s): {', '.join(sorted(unknown))}")

    manifest = build_all(out_dir, only=only, report_path=report)
    totals = manifest["totals"]
    print(
        f"Done: {totals['assetCount']} assets, "
        f"{totals['triangleCount']:,} triangles, {totals['bytesHuman']} total."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
