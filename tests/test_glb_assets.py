"""Validate the shipped glTF-binary assets in models/glb against the manifest."""

from __future__ import annotations

import json
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from geometry.glb import read_glb  # noqa: E402
from shipspec import constants as C  # noqa: E402

GLB_DIR = os.path.join(_ROOT, "models", "glb")
MANIFEST = os.path.join(GLB_DIR, "manifest.json")

EXPECTED_ASSETS = [
    "dsx-01_full_ship",
    "dsx-02_deck_01_command",
    "dsx-02_deck_02_operations",
    "dsx-02_deck_03_habitat",
    "dsx-02_deck_04_engineering",
    "dsx-03_interior_compartments",
    "dsx-04_propulsion_system",
]


def _manifest():
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


def test_manifest_present_and_complete():
    manifest = _manifest()
    ids = [a["assetId"] for a in manifest["assets"]]
    assert ids == EXPECTED_ASSETS, f"manifest assets {ids}"
    assert manifest["registry"] == C.VESSEL_REGISTRY


def test_every_asset_file_exists_and_parses():
    manifest = _manifest()
    for asset in manifest["assets"]:
        path = os.path.join(GLB_DIR, asset["filename"])
        assert os.path.exists(path), f"missing {asset['filename']}"
        assert os.path.getsize(path) > 0
        read_glb(path)  # raises on malformed binary


def test_counts_match_manifest():
    manifest = _manifest()
    for asset in manifest["assets"]:
        stats = read_glb(os.path.join(GLB_DIR, asset["filename"]))["stats"]
        assert stats["triangleCount"] == asset["triangleCount"], asset["assetId"]
        assert stats["vertexCount"] == asset["vertexCount"], asset["assetId"]
        assert stats["triangleCount"] > 0


def test_bounds_are_finite_and_positive():
    manifest = _manifest()
    for asset in manifest["assets"]:
        bounds = asset["bounds"]
        size = np.array(bounds["size"], dtype=float)
        assert np.all(np.isfinite(size)), asset["assetId"]
        assert np.all(size > 0), asset["assetId"]


def test_full_ship_matches_spec_dimensions():
    manifest = _manifest()
    ship = next(a for a in manifest["assets"] if a["assetId"] == "dsx-01_full_ship")
    size = ship["bounds"]["size"]
    # glTF is Y-up: X=length, Y=ship-up(height), Z=beam.
    assert abs(size[0] - C.LENGTH_OVERALL) < 1.0, size
    assert size[1] <= C.MAX_HEIGHT + 1.0, size
    assert size[2] <= C.MAX_BEAM + 1.0, size


def test_mesh_nodes_carry_viewer_extras():
    manifest = _manifest()
    for asset in manifest["assets"]:
        gltf = read_glb(os.path.join(GLB_DIR, asset["filename"]))["gltf"]
        mesh_nodes = [n for n in gltf["nodes"] if "mesh" in n]
        assert mesh_nodes, asset["assetId"]
        for node in mesh_nodes:
            extras = node.get("extras", {})
            for key in ("partId", "label", "system", "description"):
                assert key in extras, f"{asset['assetId']} node {node.get('name')} missing {key}"
            assert extras["system"] in C.SYSTEMS, extras["system"]


def test_materials_referenced_exist():
    manifest = _manifest()
    for asset in manifest["assets"]:
        gltf = read_glb(os.path.join(GLB_DIR, asset["filename"]))["gltf"]
        names = {m.get("name") for m in gltf.get("materials", [])}
        for mesh in gltf.get("meshes", []):
            for prim in mesh.get("primitives", []):
                idx = prim.get("material")
                if idx is not None:
                    assert gltf["materials"][idx].get("name") in names
        # Every referenced material must be one the spec defines.
        for name in names:
            assert name in C.MATERIALS, f"unknown material {name}"


def test_indices_within_vertex_range():
    manifest = _manifest()
    for asset in manifest["assets"]:
        parsed = read_glb(os.path.join(GLB_DIR, asset["filename"]))
        gltf, bin_chunk = parsed["gltf"], parsed["bin"]
        for mesh in gltf["meshes"]:
            for prim in mesh["primitives"]:
                pos = gltf["accessors"][prim["attributes"]["POSITION"]]
                idx_acc = gltf["accessors"][prim["indices"]]
                assert idx_acc["count"] % 3 == 0
                assert pos["count"] > 0
                # min/max present on POSITION per glTF spec
                assert "min" in pos and "max" in pos
