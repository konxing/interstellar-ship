"""Unit tests for the NumPy geometry kernel and the glTF writer/reader."""

from __future__ import annotations

import os
import sys
import tempfile

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from geometry.glb import Material, MeshNode, SceneGraph, read_glb, write_glb  # noqa: E402
from geometry.mesh import (  # noqa: E402
    Mesh,
    merge,
    primitive_box,
    primitive_cylinder,
    primitive_sphere,
    primitive_torus,
    primitive_tube,
)

TOL = 1e-4


def _close(a, b, tol=TOL):
    assert abs(float(a) - float(b)) <= tol, f"{a} != {b}"


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #
def test_box_dimensions():
    m = primitive_box(4.0, 2.0, 1.0)
    lo, hi = m.bounds()
    _close(lo[0], -2.0); _close(hi[0], 2.0)
    _close(lo[1], -1.0); _close(hi[1], 1.0)
    _close(lo[2], -0.5); _close(hi[2], 0.5)
    assert m.triangle_count == 12


def test_cylinder_bounds_and_caps():
    capped = primitive_cylinder(2.0, 6.0, segments=16, caps=True)
    lo, hi = capped.bounds()
    _close(hi[2] - lo[2], 6.0)
    assert max(abs(lo[0]), abs(hi[0])) <= 2.0 + TOL
    openEnded = primitive_cylinder(2.0, 6.0, segments=16, caps=False)
    assert capped.triangle_count > openEnded.triangle_count


def test_sphere_radius():
    m = primitive_sphere(3.0, segments=20, rings=12)
    lo, hi = m.bounds()
    _close(hi[0], 3.0, tol=1e-2)
    _close(lo[2], -3.0, tol=1e-2)


def test_torus_extent():
    m = primitive_torus(10.0, 1.5, major_segments=24, minor_segments=8)
    lo, hi = m.bounds()
    _close(hi[0], 11.5, tol=1e-2)
    _close(hi[2], 1.5, tol=1e-2)


def test_tube_is_hollow():
    tube = primitive_tube(4.0, 3.0, 5.0, segments=16)
    solid = primitive_cylinder(4.0, 5.0, segments=16, caps=True)
    lo, hi = tube.bounds()
    _close(hi[0], 4.0, tol=1e-2)
    # A hollow tube carries an inner wall, so more vertices than a capped solid.
    assert tube.vertex_count > solid.vertex_count


# --------------------------------------------------------------------------- #
# Transforms
# --------------------------------------------------------------------------- #
def test_translate_moves_bounds():
    m = primitive_box(2, 2, 2).translate(10, -5, 3)
    c = m.center()
    _close(c[0], 10); _close(c[1], -5); _close(c[2], 3)


def test_rotate_z_swaps_extents():
    m = primitive_box(8, 2, 1).rotate(rz=np.pi / 2)
    lo, hi = m.bounds()
    _close(hi[0] - lo[0], 2.0, tol=1e-3)
    _close(hi[1] - lo[1], 8.0, tol=1e-3)


def test_mirror_flips_axis():
    m = primitive_box(2, 2, 2).translate(0, 5, 0).mirror(axis="y")
    c = m.center()
    _close(c[1], -5)


def test_scale_extents():
    m = primitive_box(2, 2, 2).scale(3, 1, 0.5)
    lo, hi = m.bounds()
    _close(hi[0] - lo[0], 6.0)
    _close(hi[2] - lo[2], 1.0)


def test_merge_combines():
    a = primitive_box(1, 1, 1)
    b = primitive_box(1, 1, 1).translate(5, 0, 0)
    m = merge([a, b], "pair")
    assert m.triangle_count == a.triangle_count + b.triangle_count
    lo, hi = m.bounds()
    _close(hi[0], 5.5)


def test_recompute_normals_unit_length():
    # A box has no degenerate triangles, so every facet normal must be unit.
    m = primitive_box(2, 2, 2).recompute_normals()
    lengths = np.linalg.norm(m.normals, axis=1)
    assert np.allclose(lengths, 1.0, atol=1e-3)


# --------------------------------------------------------------------------- #
# glTF round trip
# --------------------------------------------------------------------------- #
def _tiny_scene() -> SceneGraph:
    scene = SceneGraph(name="tiny")
    scene.register_material(Material("Mat", (0.5, 0.5, 0.5, 1.0), 0.2, 0.6))
    scene.register_material(Material("Glow", (0.1, 0.1, 0.1, 1.0), 0.0, 0.3, emissive=(0.2, 0.8, 1.0)))
    node = MeshNode(
        name="Part",
        primitives=[(primitive_box(2, 2, 2), "Mat"), (primitive_sphere(1.0, 10, 6), "Glow")],
        extras={"partId": "Part", "label": "Part", "system": "SYS_HULL"},
    )
    scene.add(node)
    return scene


def test_glb_roundtrip_counts():
    scene = _tiny_scene()
    expected = scene.stats()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "tiny.glb")
        write_glb(path, scene)
        rt = read_glb(path)
    stats = rt["stats"]
    assert stats["triangleCount"] == expected["triangleCount"]
    assert stats["vertexCount"] == expected["vertexCount"]
    assert stats["meshCount"] == expected["meshCount"]
    assert stats["materialCount"] == 2


def test_glb_node_extras_survive():
    scene = _tiny_scene()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "tiny.glb")
        write_glb(path, scene)
        rt = read_glb(path)
    node = next(n for n in rt["gltf"]["nodes"] if n.get("name") == "Part")
    assert node["extras"]["partId"] == "Part"
    assert node["extras"]["system"] == "SYS_HULL"
    assert "bounds" in node["extras"]
    assert "triangleCount" in node["extras"]


def test_glb_material_pbr_fields():
    mat = Material("M", (0.2, 0.4, 0.6, 1.0), 0.7, 0.3, emissive=(0.1, 0.1, 0.1))
    gltf = mat.to_gltf()
    pbr = gltf["pbrMetallicRoughness"]
    _close(pbr["metallicFactor"], 0.7)
    _close(pbr["roughnessFactor"], 0.3)
    assert _close_tuple(pbr["baseColorFactor"], (0.2, 0.4, 0.6, 1.0))


def _close_tuple(a, b, tol=TOL):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def test_glb_index_type_selection():
    # >65535 vertices must promote indices to uint32.
    big = primitive_sphere(1.0, segments=512, rings=256)
    assert big.vertex_count > 65535
    scene = SceneGraph(name="big")
    scene.register_material(Material("Mat"))
    scene.add(MeshNode(name="Big", primitives=[(big, "Mat")]))
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "big.glb")
        write_glb(path, scene)
        rt = read_glb(path)
    accessor = rt["gltf"]["accessors"][rt["gltf"]["meshes"][0]["primitives"][0]["indices"]]
    assert accessor["componentType"] == 5125  # UNSIGNED_INT
