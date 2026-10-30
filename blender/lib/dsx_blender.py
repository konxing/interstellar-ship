"""Bridge between the DSX-01 procedural spec and the Blender data API.

The bridge re-uses the *same* NumPy geometry kernel and design constants that
feed the glTF exporter, so the Blender scene can never drift from the shipped
models. It converts each :class:`shipspec.part.Part` into a single Blender
object with one material slot per material and a per-face material index, and
organises objects into collections per ship system.

Blender is Z-up natively, which matches the ship frame, so no axis conversion
is applied here. The glTF exporter performs the Z-up -> Y-up conversion on
export, exactly like the Python writer.
"""

from __future__ import annotations

import os
import sys

import numpy as np

# Make the repository root importable from within Blender.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import bpy  # noqa: E402  (provided by the Blender runtime)

from shipspec import constants as C  # noqa: E402
from shipspec.part import Part  # noqa: E402


def repo_root() -> str:
    return _REPO_ROOT


# --------------------------------------------------------------------------- #
# Materials
# --------------------------------------------------------------------------- #
_material_cache: dict[str, "bpy.types.Material"] = {}


def get_material(name: str) -> "bpy.types.Material":
    """Return (and cache) a Blender material matching the spec material."""
    if name in _material_cache:
        return _material_cache[name]
    spec = C.MATERIALS.get(name)
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if spec is not None and bsdf is not None:
        r, g, b, a = spec.base_color
        bsdf.inputs["Base Color"].default_value = (r, g, b, a)
        bsdf.inputs["Metallic"].default_value = float(spec.metallic)
        bsdf.inputs["Roughness"].default_value = float(spec.roughness)
        if spec.emissive is not None:
            er, eg, eb = spec.emissive
            # Blender 3.x uses "Emission" colour + strength.
            if "Emission" in bsdf.inputs:
                bsdf.inputs["Emission"].default_value = (er, eg, eb, 1.0)
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = 1.6
        if spec.alpha_mode == "BLEND":
            mat.blend_method = "BLEND"
        mat.use_backface_culling = not spec.double_sided
    _material_cache[name] = mat
    return mat


# --------------------------------------------------------------------------- #
# Mesh construction
# --------------------------------------------------------------------------- #
def _add_mesh_object(
    name: str,
    vertices: np.ndarray,
    triangles: np.ndarray,
    face_materials: np.ndarray,
    slot_names: list[str],
    collection: "bpy.types.Collection",
) -> "bpy.types.Object":
    """Create a Blender object from raw vertex/triangle arrays (fast path)."""
    me = bpy.data.meshes.new(name)
    n_vert = vertices.shape[0]
    n_tri = triangles.shape[0]

    me.vertices.add(n_vert)
    me.vertices.foreach_set("co", np.ascontiguousarray(vertices, dtype=np.float32).ravel())

    me.loops.add(n_tri * 3)
    me.loops.foreach_set("vertex_index", np.ascontiguousarray(triangles, dtype=np.int32).ravel())

    me.polygons.add(n_tri)
    me.polygons.foreach_set("loop_start", (np.arange(n_tri, dtype=np.int32) * 3))
    me.polygons.foreach_set("loop_total", np.full(n_tri, 3, dtype=np.int32))
    me.update()

    for slot in slot_names:
        me.materials.append(get_material(slot))
    if n_tri:
        me.polygons.foreach_set("material_index", np.ascontiguousarray(face_materials, dtype=np.int32))
    me.update()
    me.validate(verbose=False)

    obj = bpy.data.objects.new(name, me)
    collection.objects.link(obj)
    return obj


def part_to_object(part: Part, collection: "bpy.types.Collection") -> "bpy.types.Object":
    """Convert one spec Part into a single multi-material Blender object."""
    verts_chunks, tri_chunks, face_mat = [], [], []
    slots: list[str] = []
    slot_index: dict[str, int] = {}
    offset = 0
    for mesh, mat_name in part.primitives:
        if mesh.is_empty():
            continue
        if mat_name not in slot_index:
            slot_index[mat_name] = len(slots)
            slots.append(mat_name)
        verts_chunks.append(np.asarray(mesh.vertices, dtype=np.float32))
        tri_chunks.append(np.asarray(mesh.indices, dtype=np.int32) + offset)
        face_mat.append(np.full(mesh.triangle_count, slot_index[mat_name], dtype=np.int32))
        offset += mesh.vertex_count

    if not verts_chunks:
        return None
    vertices = np.concatenate(verts_chunks, axis=0)
    triangles = np.concatenate(tri_chunks, axis=0)
    face_materials = np.concatenate(face_mat, axis=0)
    return _add_mesh_object(part.name, vertices, triangles, face_materials, slots, collection)


# --------------------------------------------------------------------------- #
# Collections / scene assembly
# --------------------------------------------------------------------------- #
def get_collection(name: str, parent: "bpy.types.Collection | None" = None) -> "bpy.types.Collection":
    existing = bpy.data.collections.get(name)
    if existing is not None:
        return existing
    coll = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def clear_scene() -> None:
    """Remove all objects, meshes, materials and collections for a clean build."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.collections):
        for item in list(block):
            if item.users == 0:
                block.remove(item)
    _material_cache.clear()


def build_builder_into_scene(builder, asset_name: str) -> dict:
    """Populate the Blender scene from a spec Builder, grouped by system."""
    clear_scene()
    root = get_collection(asset_name)
    counts = {"objects": 0, "triangles": 0}
    by_system: dict[str, list[Part]] = {}
    for part in builder.parts:
        by_system.setdefault(part.system, []).append(part)
    for system in sorted(by_system):
        coll = get_collection(system, root)
        for part in by_system[system]:
            obj = part_to_object(part, coll)
            if obj is None:
                continue
            obj["partId"] = part.name
            obj["label"] = part.label
            obj["system"] = part.system
            obj["deck"] = part.deck if part.deck is not None else -1
            obj["description"] = part.description
            counts["objects"] += 1
            counts["triangles"] += part.triangle_count
    return counts


def save_blend(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path)


def export_glb(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_materials="EXPORT",
        export_extras=True,
    )
