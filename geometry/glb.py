"""Minimal, dependency-free glTF 2.0 binary (.glb) writer and reader.

Only the features the project needs are implemented:

* PBR metallic-roughness materials (base colour, metallic, roughness, emissive,
  double sided, alpha mode)
* one mesh primitive per part, POSITION + NORMAL + indices accessors
* a node hierarchy with ``extras`` metadata consumed by the Three.js viewer
* Z-up (ship convention) to Y-up (glTF convention) coordinate conversion

The output is a valid .glb that three.js ``GLTFLoader``, Blender's glTF
importer and ``gltf-transform inspect`` all accept.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import numpy as np

from .mesh import Mesh

GLB_MAGIC = 0x46546C67  # 'glTF'
GLB_VERSION = 2
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

COMPONENT_FLOAT = 5126
COMPONENT_USHORT = 5123
COMPONENT_UINT = 5125

TARGET_ARRAY_BUFFER = 34962
TARGET_ELEMENT_ARRAY_BUFFER = 34963

# Ship space (+X bow, +Y starboard, +Z up) -> glTF space (+X right, +Y up, +Z viewer)
Z_UP_TO_Y_UP = np.array(
    [[1.0, 0.0, 0.0, 0.0],
     [0.0, 0.0, 1.0, 0.0],
     [0.0, -1.0, 0.0, 0.0],
     [0.0, 0.0, 0.0, 1.0]],
    dtype=np.float64,
)


@dataclass
class Material:
    """PBR metallic-roughness material."""

    name: str
    base_color: Sequence[float] = (0.8, 0.8, 0.8, 1.0)
    metallic: float = 0.0
    roughness: float = 0.9
    emissive: Sequence[float] = (0.0, 0.0, 0.0)
    double_sided: bool = False
    alpha_mode: str = "OPAQUE"

    def to_gltf(self) -> dict[str, Any]:
        r, g, b = (max(0.0, min(1.0, float(c))) for c in self.emissive)
        data: dict[str, Any] = {
            "name": self.name,
            "pbrMetallicRoughness": {
                "baseColorFactor": [float(c) for c in self.base_color],
                "metallicFactor": float(self.metallic),
                "roughnessFactor": float(self.roughness),
            },
            "doubleSided": bool(self.double_sided),
        }
        if r or g or b:
            data["emissiveFactor"] = [r, g, b]
        if self.alpha_mode != "OPAQUE":
            data["alphaMode"] = self.alpha_mode
        return data


@dataclass
class MeshNode:
    """A leaf node holding one glTF mesh.

    Either a single ``(mesh, material)`` pair or a list of primitives, in which
    case the exported glTF mesh carries several primitives - the standard way to
    render a multi-material component as one selectable node.
    """

    name: str
    mesh: Mesh | None = None
    material: str | None = None
    primitives: Sequence[tuple[Mesh, str]] | None = None
    extras: dict[str, Any] = field(default_factory=dict)
    translation: Sequence[float] | None = None
    rotation: Sequence[float] | None = None  # quaternion xyzw
    scale: Sequence[float] | None = None

    def resolved_primitives(self) -> list[tuple[Mesh, str]]:
        if self.primitives:
            return [(mesh, material) for mesh, material in self.primitives if not mesh.is_empty()]
        if self.mesh is not None and self.material is not None and not self.mesh.is_empty():
            return [(self.mesh, self.material)]
        return []

    def triangle_count(self) -> int:
        return sum(int(mesh.triangle_count) for mesh, _ in self.resolved_primitives())

    def vertex_count(self) -> int:
        return sum(int(mesh.vertex_count) for mesh, _ in self.resolved_primitives())


@dataclass
class GroupNode:
    """A transform/group node with children (groups or meshes)."""

    name: str
    children: list[Any] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)
    translation: Sequence[float] | None = None
    rotation: Sequence[float] | None = None
    scale: Sequence[float] | None = None


@dataclass
class SceneGraph:
    """Root of an exportable glTF scene."""

    name: str
    roots: list[Any] = field(default_factory=list)
    materials: dict[str, Material] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)

    def add(self, node: Any) -> Any:
        self.roots.append(node)
        return node

    def register_material(self, material: Material) -> Material:
        self.materials[material.name] = material
        return material

    def register_materials(self, materials: Iterable[Material]) -> None:
        for material in materials:
            self.register_material(material)

    def walk(self) -> Iterable[Any]:
        stack = list(self.roots)
        while stack:
            node = stack.pop()
            yield node
            if isinstance(node, GroupNode):
                stack.extend(node.children)

    def mesh_nodes(self) -> Iterable[MeshNode]:
        for node in self.walk():
            if isinstance(node, MeshNode):
                yield node

    def stats(self) -> dict[str, Any]:
        nodes = list(self.walk())
        meshes = list(self.mesh_nodes())
        triangles = sum(node.triangle_count() for node in meshes)
        vertices = sum(node.vertex_count() for node in meshes)
        return {
            "nodeCount": len(nodes),
            "meshCount": len(meshes),
            "triangleCount": int(triangles),
            "vertexCount": int(vertices),
            "materialCount": len(self.materials),
        }


class _BufferBuilder:
    """Accumulates binary payload with glTF-compliant 4-byte alignment."""

    def __init__(self) -> None:
        self.chunks: list[bytes] = []
        self.views: list[dict[str, Any]] = []
        self.length = 0

    def add_view(self, data: bytes, target: int | None) -> int:
        padding = (-len(data)) % 4
        self.chunks.append(data)
        self.chunks.append(b"\x00" * padding)
        view = {
            "buffer": 0,
            "byteOffset": self.length,
            "byteLength": len(data),
        }
        if target is not None:
            view["target"] = target
        self.views.append(view)
        self.length += len(data) + padding
        return len(self.views) - 1

    def payload(self) -> bytes:
        return b"".join(self.chunks)


def write_glb(
    path: str,
    scene: SceneGraph,
    *,
    generator: str = "DSX-01 Kairos Horizon procedural modeller",
    convert_z_up: bool = True,
) -> dict[str, Any]:
    """Serialise ``scene`` to a .glb file and return export statistics."""
    builder = _BufferBuilder()
    accessors: list[dict[str, Any]] = []
    meshes: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    node_index: dict[int, int] = {}
    converted_cache: list[Mesh] = []

    transform = Z_UP_TO_Y_UP if convert_z_up else np.eye(4)

    def emit_primitive(mesh: Mesh, material_name: str) -> dict[str, Any]:
        if mesh.is_empty():
            raise ValueError(f"node '{node.name}' contains an empty primitive")
        converted = mesh.copy().transform(transform)
        positions = np.ascontiguousarray(converted.vertices, dtype=np.float32)
        normals = np.ascontiguousarray(converted.normals, dtype=np.float32)
        max_index = int(converted.indices.max()) if converted.indices.size else 0
        if max_index < 65535 and converted.vertex_count < 65535:
            indices = np.ascontiguousarray(converted.indices, dtype=np.uint16).ravel()
            component_type = COMPONENT_USHORT
        else:
            indices = np.ascontiguousarray(converted.indices, dtype=np.uint32).ravel()
            component_type = COMPONENT_UINT

        pos_view = builder.add_view(positions.tobytes(), TARGET_ARRAY_BUFFER)
        nrm_view = builder.add_view(normals.tobytes(), TARGET_ARRAY_BUFFER)
        idx_view = builder.add_view(indices.tobytes(), TARGET_ELEMENT_ARRAY_BUFFER)

        accessors.append({
            "bufferView": pos_view,
            "componentType": COMPONENT_FLOAT,
            "count": int(positions.shape[0]),
            "type": "VEC3",
            "min": positions.min(axis=0).tolist(),
            "max": positions.max(axis=0).tolist(),
        })
        pos_accessor = len(accessors) - 1
        accessors.append({
            "bufferView": nrm_view,
            "componentType": COMPONENT_FLOAT,
            "count": int(normals.shape[0]),
            "type": "VEC3",
        })
        normal_accessor = len(accessors) - 1
        accessors.append({
            "bufferView": idx_view,
            "componentType": component_type,
            "count": int(indices.shape[0]),
            "type": "SCALAR",
        })
        index_accessor = len(accessors) - 1

        if material_name not in scene.materials:
            raise KeyError(f"material '{material_name}' used by '{node.name}' is not registered")
        material_index = list(scene.materials).index(material_name)
        converted_cache.append(converted)
        return {
            "attributes": {"POSITION": pos_accessor, "NORMAL": normal_accessor},
            "indices": index_accessor,
            "material": material_index,
            "mode": 4,
        }

    def emit_mesh_node(node: MeshNode) -> int:
        primitives = node.resolved_primitives()
        if not primitives:
            raise ValueError(f"mesh node '{node.name}' has no geometry")
        converted_cache.clear()
        gltf_primitives = [emit_primitive(mesh, material) for mesh, material in primitives]

        meshes.append({"name": node.name, "primitives": gltf_primitives})
        gltf_node: dict[str, Any] = {"name": node.name, "mesh": len(meshes) - 1}
        _apply_transform(gltf_node, node, transform)
        if node.extras:
            gltf_node["extras"] = _clean_extras(node, converted_cache)
        nodes.append(gltf_node)
        return len(nodes) - 1

    def emit_group_node(node: GroupNode) -> int:
        gltf_node: dict[str, Any] = {"name": node.name}
        children_indices = [emit(child) for child in node.children]
        if children_indices:
            gltf_node["children"] = children_indices
        _apply_transform(gltf_node, node, transform)
        if node.extras:
            gltf_node["extras"] = _clean_extras(node, None)
        nodes.append(gltf_node)
        return len(nodes) - 1

    def emit(node: Any) -> int:
        if id(node) in node_index:
            return node_index[id(node)]
        index = emit_group_node(node) if isinstance(node, GroupNode) else emit_mesh_node(node)
        node_index[id(node)] = index
        return index

    root_indices = [emit(root) for root in scene.roots]

    payload = builder.payload()
    gltf: dict[str, Any] = {
        "asset": {
            "version": "2.0",
            "generator": generator,
            "copyright": "Original design - DSX-01 Kairos Horizon project",
        },
        "scene": 0,
        "scenes": [{
            "name": scene.name,
            "nodes": root_indices,
            **({"extras": scene.extras} if scene.extras else {}),
        }],
        "nodes": nodes,
        "meshes": meshes,
        "accessors": accessors,
        "bufferViews": builder.views,
        "buffers": [{"byteLength": len(payload)}],
        "materials": [m.to_gltf() for m in scene.materials.values()],
    }

    json_bytes = json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    json_bytes += b" " * ((-len(json_bytes)) % 4)
    bin_bytes = payload + b"\x00" * ((-len(payload)) % 4)
    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)

    with open(path, "wb") as handle:
        handle.write(struct.pack("<III", GLB_MAGIC, GLB_VERSION, total_length))
        handle.write(struct.pack("<II", len(json_bytes), CHUNK_JSON))
        handle.write(json_bytes)
        handle.write(struct.pack("<II", len(bin_bytes), CHUNK_BIN))
        handle.write(bin_bytes)

    stats = scene.stats()
    stats["file"] = path
    stats["byteLength"] = total_length
    stats["bounds"] = _scene_bounds(scene, transform)
    return stats


def _apply_transform(gltf_node: dict[str, Any], node: Any, transform: np.ndarray) -> None:
    """Write node TRS, converting translations through the coordinate change."""
    if getattr(node, "translation", None) is not None:
        vec = np.array(list(node.translation) + [1.0], dtype=np.float64)
        gltf_node["translation"] = (transform @ vec)[:3].tolist()
    if getattr(node, "rotation", None) is not None:
        gltf_node["rotation"] = [float(c) for c in node.rotation]
    if getattr(node, "scale", None) is not None:
        gltf_node["scale"] = [float(c) for c in node.scale]


def _clean_extras(node: Any, converted: Sequence[Mesh] | None) -> dict[str, Any]:
    extras = dict(node.extras)
    meshes = [m for m in (converted or []) if m is not None and not m.is_empty()]
    if meshes:
        points = np.concatenate([m.vertices for m in meshes], axis=0)
        lo = points.min(axis=0)
        hi = points.max(axis=0)
        extras.setdefault("bounds", {
            "min": [round(float(v), 4) for v in lo],
            "max": [round(float(v), 4) for v in hi],
        })
        extras.setdefault("triangleCount", sum(int(m.triangle_count) for m in meshes))
    return extras


def _scene_bounds(scene: SceneGraph, transform: np.ndarray) -> dict[str, Any]:
    points = []
    for node in scene.mesh_nodes():
        for mesh, _material in node.resolved_primitives():
            points.append(mesh.copy().transform(transform).vertices)
    if not points:
        return {"min": [0, 0, 0], "max": [0, 0, 0], "size": [0, 0, 0]}
    all_points = np.concatenate(points, axis=0)
    lo = all_points.min(axis=0)
    hi = all_points.max(axis=0)
    return {
        "min": [round(float(v), 4) for v in lo],
        "max": [round(float(v), 4) for v in hi],
        "size": [round(float(v), 4) for v in (hi - lo)],
    }


# --------------------------------------------------------------------------- #
# Reader (used by the validation suite)
# --------------------------------------------------------------------------- #
def read_glb(path: str) -> dict[str, Any]:
    """Parse a .glb file and return ``{"gltf": dict, "bin": bytes, "stats": dict}``."""
    with open(path, "rb") as handle:
        data = handle.read()
    if len(data) < 12:
        raise ValueError(f"{path}: file too small to be a GLB")
    magic, version, length = struct.unpack("<III", data[:12])
    if magic != GLB_MAGIC:
        raise ValueError(f"{path}: bad GLB magic 0x{magic:08X}")
    if version != GLB_VERSION:
        raise ValueError(f"{path}: unsupported GLB version {version}")
    if length != len(data):
        raise ValueError(f"{path}: header length {length} != file size {len(data)}")

    offset = 12
    json_chunk = None
    bin_chunk = b""
    while offset + 8 <= len(data):
        chunk_length, chunk_type = struct.unpack("<II", data[offset:offset + 8])
        offset += 8
        payload = data[offset:offset + chunk_length]
        if len(payload) != chunk_length:
            raise ValueError(f"{path}: truncated chunk at offset {offset}")
        offset += chunk_length
        if chunk_type == CHUNK_JSON:
            json_chunk = json.loads(payload.decode("utf-8"))
        elif chunk_type == CHUNK_BIN:
            bin_chunk = payload
    if json_chunk is None:
        raise ValueError(f"{path}: missing JSON chunk")

    stats = {
        "file": path,
        "byteLength": len(data),
        "version": version,
        "nodeCount": len(json_chunk.get("nodes", [])),
        "meshCount": len(json_chunk.get("meshes", [])),
        "materialCount": len(json_chunk.get("materials", [])),
        "accessorCount": len(json_chunk.get("accessors", [])),
        "bufferViewCount": len(json_chunk.get("bufferViews", [])),
        "triangleCount": 0,
        "vertexCount": 0,
    }
    for mesh in json_chunk.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            index_accessor = primitive.get("indices")
            if index_accessor is not None:
                stats["triangleCount"] += json_chunk["accessors"][index_accessor]["count"] // 3
            position = primitive.get("attributes", {}).get("POSITION")
            if position is not None:
                stats["vertexCount"] += json_chunk["accessors"][position]["count"]
    return {"gltf": json_chunk, "bin": bin_chunk, "stats": stats}
