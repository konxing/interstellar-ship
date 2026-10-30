"""Part / assembly bookkeeping shared by every builder module.

A :class:`Part` is one logical component of the ship. It may be built from
several meshes with different materials - they are exported as multiple
primitives of a single glTF mesh, so the Three.js viewer sees one selectable
node per component instead of dozens of fragments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from geometry.glb import GroupNode, MeshNode, SceneGraph
from geometry.mesh import Mesh, merge

Primitive = tuple[Mesh, str]


@dataclass
class Part:
    """A single named component with viewer metadata."""

    name: str
    label: str
    system: str
    primitives: list[Primitive]
    deck: int | None = None
    description: str = ""
    tags: tuple[str, ...] = ()

    # -- construction helpers --------------------------------------------- #
    @staticmethod
    def solid(
        name: str,
        label: str,
        system: str,
        material: str,
        mesh: Mesh,
        **kwargs: Any,
    ) -> "Part":
        return Part(name, label, system, [(mesh, material)], **kwargs)

    @staticmethod
    def multi(
        name: str,
        label: str,
        system: str,
        primitives: Iterable[Primitive],
        **kwargs: Any,
    ) -> "Part":
        return Part(name, label, system, _merge_by_material(primitives), **kwargs)

    # -- introspection ---------------------------------------------------- #
    @property
    def triangle_count(self) -> int:
        return sum(int(m.triangle_count) for m, _ in self.primitives)

    @property
    def vertex_count(self) -> int:
        return sum(int(m.vertex_count) for m, _ in self.primitives)

    @property
    def material_names(self) -> list[str]:
        return [mat for _, mat in self.primitives]

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        lows, highs = [], []
        for mesh, _ in self.primitives:
            lo, hi = mesh.bounds()
            lows.append(lo)
            highs.append(hi)
        if not lows:
            return np.zeros(3, dtype=np.float32), np.zeros(3, dtype=np.float32)
        return np.min(np.array(lows), axis=0), np.max(np.array(highs), axis=0)

    def is_empty(self) -> bool:
        return all(mesh.is_empty() for mesh, _ in self.primitives)

    def extras(self) -> dict[str, Any]:
        return {
            "partId": self.name,
            "label": self.label,
            "system": self.system,
            "deck": self.deck,
            "materials": self.material_names,
            "description": self.description,
            "tags": list(self.tags),
        }


def _merge_by_material(primitives: Iterable[Primitive]) -> list[Primitive]:
    """Merge every mesh that shares a material into a single primitive."""
    grouped: dict[str, list[Mesh]] = {}
    order: list[str] = []
    for mesh, material in primitives:
        if mesh.is_empty():
            continue
        if material not in grouped:
            grouped[material] = []
            order.append(material)
        grouped[material].append(mesh)
    return [(merge(grouped[material], material), material) for material in order]


class Builder:
    """Collects parts and turns them into exportable scene graphs."""

    def __init__(self, name: str = "assembly") -> None:
        self.name = name
        self.parts: list[Part] = []
        self._seen: set[str] = set()

    # -- authoring -------------------------------------------------------- #
    def add(self, part: Part) -> Part:
        if part.name in self._seen:
            raise ValueError(f"duplicate part name '{part.name}' in builder '{self.name}'")
        if part.is_empty():
            raise ValueError(f"part '{part.name}' produced no geometry")
        if not part.primitives:
            raise ValueError(f"part '{part.name}' has no primitives")
        self._seen.add(part.name)
        self.parts.append(part)
        return part

    def solid(
        self,
        name: str,
        label: str,
        system: str,
        material: str,
        mesh: Mesh,
        **kwargs: Any,
    ) -> Part:
        return self.add(Part.solid(name, label, system, material, mesh, **kwargs))

    def multi(
        self,
        name: str,
        label: str,
        system: str,
        primitives: Iterable[Primitive],
        **kwargs: Any,
    ) -> Part:
        return self.add(Part.multi(name, label, system, primitives, **kwargs))

    def add_all(self, parts: Iterable[Part]) -> list[Part]:
        return [self.add(part) for part in parts]

    # -- queries ---------------------------------------------------------- #
    def filter(self, *, system: str | None = None, deck: int | None = None) -> list[Part]:
        return [
            p for p in self.parts
            if (system is None or p.system == system) and (deck is None or p.deck == deck)
        ]

    def bounds(self, parts: Iterable[Part] | None = None) -> tuple[np.ndarray, np.ndarray]:
        selected = list(parts if parts is not None else self.parts)
        if not selected:
            zero = np.zeros(3, dtype=np.float32)
            return zero, zero.copy()
        lows, highs = [], []
        for part in selected:
            lo, hi = part.bounds()
            lows.append(lo)
            highs.append(hi)
        return np.min(np.array(lows), axis=0), np.max(np.array(highs), axis=0)

    def stats(self) -> dict[str, Any]:
        return {
            "partCount": len(self.parts),
            "triangleCount": sum(p.triangle_count for p in self.parts),
            "vertexCount": sum(p.vertex_count for p in self.parts),
        }

    # -- scene graph ------------------------------------------------------ #
    def scene(
        self,
        name: str,
        materials: Iterable[Any],
        extras: dict[str, Any] | None = None,
        group_by: Callable[[Part], str] | None = None,
        offset: Sequence[float] | None = None,
        parts: Iterable[Part] | None = None,
    ) -> SceneGraph:
        scene = SceneGraph(name=name, extras=dict(extras or {}))
        scene.register_materials(materials)
        selected = list(parts if parts is not None else self.parts)
        shift = np.array(offset, dtype=np.float32) if offset is not None else None

        if group_by is None:
            for part in selected:
                scene.add(_mesh_node(part, shift))
            return scene

        groups: dict[str, list[Part]] = {}
        for part in selected:
            groups.setdefault(group_by(part), []).append(part)
        for key in sorted(groups):
            node = GroupNode(name=key, extras={"groupId": key, "groupLabel": key})
            for part in groups[key]:
                node.children.append(_mesh_node(part, shift))
            scene.add(node)
        return scene


def _mesh_node(part: Part, shift: np.ndarray | None) -> MeshNode:
    if shift is None:
        primitives = part.primitives
    else:
        primitives = [
            (mesh.copy().translate(*shift.tolist()), material)
            for mesh, material in part.primitives
        ]
    return MeshNode(
        name=part.name,
        mesh=None,
        material=None,
        primitives=primitives,
        extras=part.extras(),
    )


def recenter_offset(builder: Builder, parts: Iterable[Part] | None = None) -> np.ndarray:
    """Translation that moves the bounding-box centre of ``parts`` to the origin."""
    lo, hi = builder.bounds(parts)
    return -((lo + hi) * 0.5)
