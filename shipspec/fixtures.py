"""Reusable detail components (fixtures) used by every builder module.

Each fixture returns a :class:`Fixture`, which is a list of ``(mesh, material)``
pairs expressed in local space. Callers position them with :meth:`Fixture.at`
and merge them into parts, so the same components populate the deck models, the
interior compartment models and the Blender scene.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np

from geometry.mesh import (
    Mesh,
    beam_between,
    compose_matrix,
    grid_panel,
    lattice_truss,
    merge,
    primitive_box,
    primitive_cone,
    primitive_cylinder,
    primitive_sphere,
    primitive_torus,
    primitive_tube,
    transform_mesh,
)

TWO_PI = math.pi * 2.0


class Fixture(list):
    """List of ``(Mesh, material_name)`` pairs with placement helpers."""

    def add(
        self,
        mesh: Mesh,
        material: str,
        loc: Sequence[float] = (0.0, 0.0, 0.0),
        rot: Sequence[float] = (0.0, 0.0, 0.0),
        scale: Sequence[float] = (1.0, 1.0, 1.0),
    ) -> "Fixture":
        if mesh.is_empty():
            return self
        placed = transform_mesh(mesh, location=list(loc), rotation=list(rot), scale=list(scale))
        self.append((placed, material))
        return self

    def extend_at(
        self,
        other: Iterable[tuple[Mesh, str]],
        loc: Sequence[float] = (0.0, 0.0, 0.0),
        rot: Sequence[float] = (0.0, 0.0, 0.0),
    ) -> "Fixture":
        matrix = compose_matrix(location=list(loc), rotation=list(rot))
        for mesh, material in other:
            if mesh.is_empty():
                continue
            self.append((mesh.copy().transform(matrix), material))
        return self

    def shift(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> "Fixture":
        self[:] = [(mesh.copy().translate(x, y, z), material) for mesh, material in self]
        return self

    def merge_per_material(self) -> list[tuple[Mesh, str]]:
        grouped: dict[str, list[Mesh]] = {}
        order: list[str] = []
        for mesh, material in self:
            if material not in grouped:
                grouped[material] = []
                order.append(material)
            grouped[material].append(mesh)
        return [(merge(grouped[m], m), m) for m in order if grouped[m]]

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        lows, highs = [], []
        for mesh, _ in self:
            lo, hi = mesh.bounds()
            lows.append(lo)
            highs.append(hi)
        if not lows:
            zero = np.zeros(3, dtype=np.float32)
            return zero, zero.copy()
        return np.min(np.array(lows), axis=0), np.max(np.array(highs), axis=0)


# --------------------------------------------------------------------------- #
# Room shell
# --------------------------------------------------------------------------- #
def room_shell(
    length: float,
    width: float,
    height: float,
    wall: float = 0.18,
    rib_every: float = 3.0,
    rib_depth: float = 0.22,
    floor_material: str = "InteriorFloor",
    wall_material: str = "InteriorWall",
    trim_material: str = "InteriorTrim",
    ceiling_lights: bool = True,
) -> Fixture:
    """A rectangular compartment: deck, ceiling, two side walls, ribs and lights.

    The room is centred on the origin, floor at ``z = 0``.
    """
    fx = Fixture()
    hl, hw = length * 0.5, width * 0.5
    fx.add(primitive_box(length, width, wall), floor_material, loc=(0, 0, -wall * 0.5))
    fx.add(primitive_box(length, width, wall * 0.6), wall_material, loc=(0, 0, height + wall * 0.3))
    for side in (-1, 1):
        fx.add(
            primitive_box(length, wall, height),
            wall_material,
            loc=(0, side * (hw + wall * 0.5), height * 0.5),
        )
    # Structural ribs + cable conduits along both walls.
    count = max(2, int(round(length / rib_every)))
    for i in range(count + 1):
        x = -hl + length * i / count
        for side in (-1, 1):
            y = side * (hw - rib_depth * 0.5)
            fx.add(primitive_box(rib_depth, rib_depth, height), trim_material, loc=(x, y, height * 0.5))
            fx.add(
                primitive_cylinder(0.09, length * 0.0 + rib_depth * 1.4, 8),
                "PipingSteel",
                loc=(x, side * (hw - 0.32), height - 0.55),
                rot=(0, math.pi / 2, 0),
            )
    # Bulkhead at the aft end and a hatch on the forward end.
    fx.add(primitive_box(wall, width, height), wall_material, loc=(-hl - wall * 0.5, 0, height * 0.5))
    fx.extend_at(hatch(1.05, 2.05), loc=(-hl - wall, 0, 0))
    fx.add(primitive_box(wall * 0.6, width * 0.55, height * 0.72), trim_material, loc=(hl, 0, height * 0.36))
    if ceiling_lights:
        for i in range(max(2, count)):
            x = -hl + length * (i + 0.5) / count
            fx.add(primitive_box(length / count * 0.55, 0.34, 0.08), "LightStrip", loc=(x, 0, height - 0.06))
    return fx


def hatch(radius: float = 1.0, height: float = 2.0, thickness: float = 0.22) -> Fixture:
    """Pressure hatch: ring, door leaf, dogging wheel and hazard outline."""
    fx = Fixture()
    fx.add(primitive_torus(radius + 0.14, 0.12, 22, 8), "InteriorTrim")
    fx.add(primitive_cylinder(radius, thickness, 22), "DeckPlate", rot=(0, math.pi / 2, 0))
    fx.add(primitive_torus(radius * 0.55, 0.06, 18, 6), "PipingSteel")
    for i in range(6):
        a = TWO_PI * i / 6
        fx.add(
            primitive_box(0.06, radius * 1.0, 0.06),
            "PipingSteel",
            loc=(thickness * 0.6, 0, 0),
            rot=(a, 0, 0),
        )
    fx.add(primitive_box(0.05, radius * 2.5, 0.05), "DeckHazard", loc=(0, 0, -height * 0.5 + 0.05))
    return fx


def door(width: float = 1.1, height: float = 2.1) -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(0.24, width + 0.3, height + 0.3), "InteriorTrim", loc=(0, 0, height * 0.5))
    fx.add(primitive_box(0.30, width * 0.48, height - 0.1), "DeckPlate", loc=(0, -width * 0.25, height * 0.5))
    fx.add(primitive_box(0.30, width * 0.48, height - 0.1), "DeckPlate", loc=(0, width * 0.25, height * 0.5))
    fx.add(primitive_box(0.06, 0.3, 0.16), "ScreenGlow", loc=(0.18, width * 0.62, height * 0.55))
    return fx


def light_strip(length: float, width: float = 0.3) -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(length, width, 0.07), "LightStrip")
    fx.add(primitive_box(length, width + 0.12, 0.04), "InteriorTrim", loc=(0, 0, 0.05))
    return fx


# --------------------------------------------------------------------------- #
# Command / operations furniture
# --------------------------------------------------------------------------- #
def console(width: float = 2.4, depth: float = 0.9, height: float = 1.05, tilt: float = 0.5) -> Fixture:
    """Operator console with a raked display bank."""
    fx = Fixture()
    fx.add(primitive_box(depth, width, height * 0.62), "ConsoleBody", loc=(0, 0, height * 0.31))
    fx.add(primitive_box(depth * 0.9, width * 0.96, 0.06), "InteriorTrim", loc=(0, 0, height * 0.64))
    fx.add(
        primitive_box(0.08, width * 0.9, height * 0.52),
        "ScreenGlow",
        loc=(-depth * 0.3, 0, height * 0.95),
        rot=(0, tilt, 0),
    )
    fx.add(
        primitive_box(0.05, width * 0.4, height * 0.2),
        "ScreenAmber",
        loc=(depth * 0.12, width * 0.22, height * 0.78),
        rot=(0, -0.35, 0),
    )
    for i in range(3):
        fx.add(
            primitive_box(0.16, 0.16, 0.05),
            "InteriorTrim",
            loc=(depth * 0.18, -width * 0.3 + i * width * 0.3, height * 0.68),
        )
    return fx


def command_chair() -> Fixture:
    fx = Fixture()
    fx.add(primitive_cylinder(0.32, 0.08, 14), "InteriorTrim", loc=(0, 0, 0.04))
    fx.add(primitive_cylinder(0.09, 0.42, 10), "PipingSteel", loc=(0, 0, 0.25))
    fx.add(primitive_box(0.52, 0.56, 0.14), "FabricBlue", loc=(0, 0, 0.52))
    fx.add(primitive_box(0.16, 0.56, 0.78), "FabricBlue", loc=(-0.22, 0, 0.92), rot=(0, -0.16, 0))
    fx.add(primitive_box(0.1, 0.1, 0.34), "InteriorTrim", loc=(-0.05, 0.32, 0.72))
    fx.add(primitive_box(0.1, 0.1, 0.34), "InteriorTrim", loc=(-0.05, -0.32, 0.72))
    fx.add(primitive_box(0.3, 0.5, 0.06), "ConsoleBody", loc=(0.24, 0, 0.76), rot=(0, 0, 0.3))
    return fx


def holo_table(radius: float = 1.5, height: float = 0.95) -> Fixture:
    fx = Fixture()
    fx.add(primitive_cylinder(radius * 0.28, height, 14), "ConsoleBody", loc=(0, 0, height * 0.5))
    fx.add(primitive_cylinder(radius, 0.12, 26), "InteriorTrim", loc=(0, 0, height))
    fx.add(primitive_torus(radius * 0.98, 0.06, 26, 8), "ScreenGlow", loc=(0, 0, height + 0.1))
    fx.add(
        primitive_sphere(radius * 0.42, 18, 12),
        "Glass",
        loc=(0, 0, height + radius * 0.62),
    )
    fx.add(primitive_torus(radius * 0.6, 0.02, 24, 6), "PlasmaCore", loc=(0, 0, height + radius * 0.62), rot=(math.pi / 2, 0, 0))
    return fx


def workstation(length: float = 2.0, depth: float = 0.8) -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(depth, length, 0.06), "InteriorTrim", loc=(0, 0, 0.74))
    for y in (-1, 1):
        fx.add(primitive_box(depth * 0.8, 0.08, 0.72), "ConsoleBody", loc=(0, y * (length * 0.5 - 0.08), 0.36))
    fx.add(primitive_box(0.06, length * 0.8, 0.5), "ScreenGlow", loc=(-depth * 0.32, 0, 1.06), rot=(0, 0.3, 0))
    fx.add(primitive_box(0.4, 0.42, 0.08), "FabricTeal", loc=(depth * 0.7, 0, 0.46))
    fx.add(primitive_cylinder(0.05, 0.44, 8), "PipingSteel", loc=(depth * 0.7, 0, 0.24))
    return fx


def server_rack(width: float = 0.8, depth: float = 1.0, height: float = 2.2) -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(depth, width, height), "ConsoleBody", loc=(0, 0, height * 0.5))
    rows = int(height / 0.22)
    for i in range(rows):
        z = 0.2 + i * 0.22
        material = "ScreenGlow" if i % 3 else "ScreenAmber"
        fx.add(primitive_box(0.04, width * 0.8, 0.06), material, loc=(depth * 0.5 + 0.01, 0, z))
    fx.add(primitive_box(depth * 0.9, width * 0.9, 0.05), "InteriorTrim", loc=(0, 0, height + 0.03))
    return fx


def storage_rack(length: float = 2.4, depth: float = 0.7, height: float = 2.2, shelves: int = 4) -> Fixture:
    fx = Fixture()
    for z_i in range(shelves + 1):
        z = height * z_i / shelves
        fx.add(primitive_box(depth, length, 0.05), "InteriorTrim", loc=(0, 0, z + 0.025))
    for y in (-1, 1):
        fx.add(primitive_box(depth, 0.06, height), "ConsoleBody", loc=(0, y * length * 0.5, height * 0.5))
    for i in range(int(length / 0.7)):
        for z_i in range(shelves):
            if (i + z_i) % 3 == 2:
                continue
            fx.add(
                primitive_box(depth * 0.8, 0.55, height / shelves * 0.6),
                "FabricTeal" if (i + z_i) % 2 else "DeckPlate",
                loc=(0, -length * 0.5 + 0.45 + i * 0.7, height * z_i / shelves + height / shelves * 0.36),
            )
    return fx


def crate(size: float = 0.9) -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(size, size, size), "DeckPlate", loc=(0, 0, size * 0.5))
    for axis in range(3):
        loc = [0.0, 0.0, size * 0.5]
        rot = [0.0, 0.0, 0.0]
        rot[axis % 2] = math.pi / 2
        fx.add(primitive_box(size * 1.02, 0.06, 0.06), "DeckHazard", loc=(loc[0], loc[1] + size * 0.5, loc[2]))
    fx.add(primitive_box(size * 0.4, size * 0.25, 0.02), "ScreenAmber", loc=(0, -size * 0.51, size * 0.62))
    return fx


# --------------------------------------------------------------------------- #
# Science / medical / habitat furniture
# --------------------------------------------------------------------------- #
def lab_bench(length: float = 3.0, depth: float = 1.0) -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(depth, length, 0.08), "CeramicTile", loc=(0, 0, 0.9))
    fx.add(primitive_box(depth * 0.9, length * 0.95, 0.86), "InteriorWall", loc=(0, 0, 0.45))
    fx.add(primitive_box(0.35, 0.35, 0.3), "ConsoleBody", loc=(0.1, -length * 0.3, 1.1))
    fx.add(primitive_box(0.3, 0.3, 0.05), "ScreenGlow", loc=(0.1, -length * 0.3, 1.27))
    fx.add(primitive_cylinder(0.12, 0.34, 12), "Glass", loc=(0.15, length * 0.22, 1.11))
    fx.add(primitive_cylinder(0.09, 0.26, 12), "MedicalWhite", loc=(-0.2, length * 0.3, 1.07))
    fx.add(primitive_box(0.5, 0.06, 0.42), "InteriorTrim", loc=(0, 0, 1.35))
    return fx


def sample_pod(radius: float = 0.32) -> Fixture:
    fx = Fixture()
    fx.add(primitive_cylinder(radius, radius * 2.2, 14), "TankSkin", loc=(0, 0, radius * 1.1))
    fx.add(primitive_torus(radius * 1.02, 0.035, 16, 6), "PipingSteel", loc=(0, 0, radius * 1.6))
    fx.add(primitive_box(0.04, radius * 1.1, 0.12), "ScreenAmber", loc=(radius, 0, radius * 1.2))
    return fx


def hydroponic_planter(length: float = 3.2, width: float = 1.1, height: float = 1.0) -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(width, length, height), "InteriorTrim", loc=(0, 0, height * 0.5))
    fx.add(primitive_box(width * 0.86, length * 0.94, 0.12), "HydroGreen", loc=(0, 0, height + 0.02))
    for i in range(int(length / 0.5)):
        fx.add(
            primitive_sphere(0.16, 10, 6),
            "HydroGreen",
            loc=(0, -length * 0.44 + 0.3 + i * 0.5, height + 0.2),
        )
    fx.add(primitive_box(width * 1.05, length * 1.02, 0.08), "GrowLight", loc=(0, 0, height + 0.95))
    for y in (-1, 1):
        fx.add(primitive_box(0.08, 0.08, 0.95), "PipingSteel", loc=(y * width * 0.5, -length * 0.48, height + 0.48))
        fx.add(primitive_box(0.08, 0.08, 0.95), "PipingSteel", loc=(y * width * 0.5, length * 0.48, height + 0.48))
    return fx


def medical_bed() -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(0.75, 2.1, 0.12), "MedicalWhite", loc=(0, 0, 0.72))
    fx.add(primitive_cylinder(0.08, 0.7, 10), "PipingSteel", loc=(0, 0, 0.36))
    fx.add(primitive_box(0.9, 1.0, 0.06), "InteriorTrim", loc=(0, 0, 0.04))
    fx.add(primitive_box(0.7, 1.3, 0.08), "FabricTeal", loc=(0, 0.2, 0.82))
    fx.add(primitive_box(0.5, 0.4, 0.1), "MedicalWhite", loc=(0, -0.85, 0.84))
    fx.add(primitive_cylinder(1.05, 1.5, 18, caps=False), "Glass", loc=(0, 0.1, 1.35), rot=(math.pi / 2, 0, 0))
    fx.add(primitive_box(0.5, 0.6, 0.14), "ConsoleBody", loc=(0.75, -0.7, 1.05))
    fx.add(primitive_box(0.04, 0.44, 0.3), "ScreenGlow", loc=(0.75, -0.7, 1.24), rot=(0.5, 0, 0))
    return fx


def med_cabinet() -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(0.5, 1.2, 1.9), "MedicalWhite", loc=(0, 0, 0.95))
    fx.add(primitive_box(0.04, 0.5, 0.5), "ScreenGlow", loc=(0.26, -0.25, 1.35))
    for i in range(3):
        fx.add(primitive_box(0.04, 1.0, 0.04), "InteriorTrim", loc=(0.26, 0, 0.5 + i * 0.45))
    return fx


def bunk(width: float = 0.9, length: float = 2.0) -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(width, length, 0.1), "InteriorTrim", loc=(0, 0, 0.35))
    fx.add(primitive_box(width * 0.92, length * 0.96, 0.14), "FabricBlue", loc=(0, 0, 0.47))
    fx.add(primitive_box(width * 0.6, 0.36, 0.1), "MedicalWhite", loc=(0, -length * 0.35, 0.58))
    fx.add(primitive_box(width * 0.95, 0.08, 0.5), "InteriorWall", loc=(0, -length * 0.5 - 0.04, 0.6))
    fx.add(primitive_box(0.05, 0.3, 0.05), "ScreenAmber", loc=(width * 0.45, -length * 0.4, 0.78))
    fx.add(primitive_box(0.3, 0.4, 0.3), "ConsoleBody", loc=(width * 0.42, length * 0.3, 0.6))
    return fx


def bunk_stack(tiers: int = 2, width: float = 0.9, length: float = 2.0) -> Fixture:
    fx = Fixture()
    for tier in range(tiers):
        fx.extend_at(bunk(width, length), loc=(0, 0, tier * 1.15))
    fx.add(primitive_box(0.08, 0.08, tiers * 1.15 + 0.4), "PipingSteel", loc=(width * 0.55, length * 0.5, (tiers * 1.15) * 0.5))
    return fx


def galley_counter(length: float = 3.0) -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(0.9, length, 0.9), "InteriorWall", loc=(0, 0, 0.45))
    fx.add(primitive_box(0.95, length, 0.06), "CeramicTile", loc=(0, 0, 0.93))
    fx.add(primitive_cylinder(0.18, 0.06, 14), "PipingSteel", loc=(0.1, length * 0.25, 0.97))
    fx.add(primitive_cylinder(0.03, 0.34, 8), "PipingSteel", loc=(0.1, length * 0.25 + 0.18, 1.12))
    fx.add(primitive_box(0.5, 0.6, 0.6), "ConsoleBody", loc=(0.05, -length * 0.28, 1.24))
    fx.add(primitive_box(0.04, 0.4, 0.28), "ScreenAmber", loc=(0.32, -length * 0.28, 1.3))
    return fx


def mess_table(length: float = 2.4, width: float = 1.1) -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(width, length, 0.07), "InteriorTrim", loc=(0, 0, 0.75))
    fx.add(primitive_box(width * 0.3, length * 0.8, 0.7), "ConsoleBody", loc=(0, 0, 0.36))
    for side in (-1, 1):
        for i in range(2):
            y = -length * 0.28 + i * length * 0.56
            fx.add(primitive_box(0.42, 0.42, 0.06), "FabricTeal", loc=(side * (width * 0.5 + 0.32), y, 0.45))
            fx.add(primitive_cylinder(0.05, 0.44, 8), "PipingSteel", loc=(side * (width * 0.5 + 0.32), y, 0.22))
    return fx


def treadmill() -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(0.8, 1.9, 0.12), "RubberBlack", loc=(0, 0, 0.14))
    fx.add(primitive_box(0.9, 2.0, 0.1), "InteriorTrim", loc=(0, 0, 0.06))
    for side in (-1, 1):
        fx.add(primitive_box(0.07, 0.07, 1.3), "PipingSteel", loc=(side * 0.38, -0.8, 0.7))
    fx.add(primitive_box(0.9, 0.1, 0.35), "ConsoleBody", loc=(0, -0.85, 1.4))
    fx.add(primitive_box(0.05, 0.5, 0.24), "ScreenGlow", loc=(0, -0.85, 1.5), rot=(0.4, 0, 0))
    fx.add(primitive_box(1.0, 0.06, 0.06), "DeckHazard", loc=(0, 0.95, 0.22))
    return fx


def airlock_chamber(radius: float = 1.8, length: float = 3.0) -> Fixture:
    """EVA airlock: cylindrical chamber, inner and outer hatches, suit racks."""
    fx = Fixture()
    fx.add(primitive_cylinder(radius, length, 22, caps=False), "InteriorWall", rot=(0, math.pi / 2, 0))
    for i in range(6):
        fx.add(
            primitive_torus(radius + 0.06, 0.09, 22, 8),
            "InteriorTrim",
            loc=(-length * 0.5 + length * (i + 0.5) / 6, 0, 0),
            rot=(0, math.pi / 2, 0),
        )
    fx.extend_at(hatch(radius * 0.62, radius * 1.3), loc=(-length * 0.5, 0, 0), rot=(0, math.pi / 2, 0))
    fx.extend_at(hatch(radius * 0.62, radius * 1.3), loc=(length * 0.5, 0, 0), rot=(0, -math.pi / 2, 0))
    for side in (-1, 1):
        fx.add(primitive_box(0.5, 0.7, 1.7), "FabricBlue", loc=(0, side * (radius - 0.4), 0))
        fx.add(primitive_sphere(0.19, 12, 8), "MedicalWhite", loc=(0, side * (radius - 0.4), 1.0))
    fx.add(primitive_box(0.3, 0.5, 0.06), "ScreenAmber", loc=(length * 0.2, radius - 0.1, 0.9))
    fx.add(primitive_box(length * 0.8, 0.06, 0.06), "LightStrip", loc=(0, 0, radius - 0.12))
    return fx


# --------------------------------------------------------------------------- #
# Engineering furniture
# --------------------------------------------------------------------------- #
def reactor_core(radius: float = 2.4, height: float = 3.6) -> Fixture:
    fx = Fixture()
    fx.add(primitive_cylinder(radius, height, 26), "ReactorShield", loc=(0, 0, height * 0.5))
    fx.add(primitive_torus(radius + 0.16, 0.22, 26, 10), "PipingSteel", loc=(0, 0, height * 0.2))
    fx.add(primitive_torus(radius + 0.16, 0.22, 26, 10), "PipingSteel", loc=(0, 0, height * 0.8))
    fx.add(primitive_cylinder(radius * 0.55, height * 1.06, 20), "ReactorGlow", loc=(0, 0, height * 0.5))
    for i in range(8):
        a = TWO_PI * i / 8
        fx.add(
            primitive_box(0.22, radius * 0.7, height * 0.5),
            "CoilCopper",
            loc=(math.cos(a) * radius * 0.95, math.sin(a) * radius * 0.95, height * 0.5),
            rot=(0, 0, a),
        )
    fx.add(primitive_cone(radius * 1.15, radius * 0.7, 0.7, 26), "ReactorShield", loc=(0, 0, height + 0.3))
    return fx


def turbopump(radius: float = 0.6, length: float = 1.4) -> Fixture:
    fx = Fixture()
    fx.add(primitive_cylinder(radius, length, 18), "EngineMetal", rot=(0, math.pi / 2, 0))
    fx.add(primitive_cylinder(radius * 0.5, radius * 1.1, 16), "PipingSteel", loc=(length * 0.5, 0, 0), rot=(0, math.pi / 2, 0))
    fx.add(primitive_box(radius * 1.6, radius * 1.2, radius * 0.8), "ConsoleBody", loc=(-length * 0.35, 0, -radius * 0.9))
    for i in range(6):
        a = TWO_PI * i / 6
        fx.add(
            primitive_box(length * 0.8, 0.07, 0.07),
            "CoilCopper",
            loc=(0, math.cos(a) * radius * 1.05, math.sin(a) * radius * 1.05),
        )
    return fx


def workbench(length: float = 2.6) -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(0.9, length, 0.1), "DeckPlate", loc=(0, 0, 0.92))
    for y in (-1, 1):
        fx.add(primitive_box(0.85, 0.1, 0.88), "InteriorTrim", loc=(0, y * (length * 0.5 - 0.1), 0.44))
    fx.add(primitive_cylinder(0.16, 0.5, 12), "PipingSteel", loc=(0.1, length * 0.3, 1.2), rot=(0, 0, math.pi / 2))
    fx.add(primitive_box(0.4, 0.3, 0.22), "ConsoleBody", loc=(-0.1, -length * 0.25, 1.08))
    fx.add(primitive_box(0.04, 0.26, 0.16), "ScreenAmber", loc=(-0.1, -length * 0.25, 1.24), rot=(0.6, 0, 0))
    fx.add(primitive_box(1.0, length * 0.9, 0.04), "LightStrip", loc=(0, 0, 1.9))
    return fx


def propellant_tank(radius: float = 1.2, length: float = 2.6) -> Fixture:
    fx = Fixture()
    fx.add(primitive_cylinder(radius, length, 20), "TankSkin", rot=(0, math.pi / 2, 0))
    for side in (-1, 1):
        fx.add(primitive_sphere(radius, 18, 10, theta_length=math.pi / 2), "TankSkin",
                 loc=(side * length * 0.5, 0, 0), rot=(0, side * math.pi / 2, 0))
    for i in range(2):
        fx.add(primitive_torus(radius + 0.05, 0.07, 20, 8), "PipingSteel",
                 loc=(-length * 0.25 + i * length * 0.5, 0, 0), rot=(0, math.pi / 2, 0))
    fx.add(primitive_cylinder(0.09, radius * 1.6, 8), "PipingSteel", loc=(0, 0, radius * 0.9), rot=(math.pi / 2, 0, 0))
    return fx


def pipe_run(points: Sequence[Sequence[float]], radius: float = 0.14, material: str = "PipingSteel") -> Fixture:
    fx = Fixture()
    for i in range(len(points) - 1):
        fx.add(beam_between(points[i], points[i + 1], radius * 2, radius * 2), material)
        fx.add(primitive_sphere(radius * 1.35, 10, 6), material, loc=points[i])
    if len(points) > 1:
        fx.add(primitive_sphere(radius * 1.35, 10, 6), material, loc=points[-1])
    return fx


def ladder(height: float = 3.0, width: float = 0.5) -> Fixture:
    fx = Fixture()
    for side in (-1, 1):
        fx.add(primitive_box(0.07, 0.07, height), "PipingSteel", loc=(0, side * width * 0.5, height * 0.5))
    rungs = max(3, int(height / 0.32))
    for i in range(rungs):
        fx.add(primitive_cylinder(0.03, width, 8), "PipingSteel", loc=(0, 0, 0.25 + i * (height - 0.4) / (rungs - 1)), rot=(math.pi / 2, 0, 0))
    return fx


# --------------------------------------------------------------------------- #
# Exterior hardware
# --------------------------------------------------------------------------- #
def dish(radius: float, depth: float = None, segments: int = 30, rings: int = 8) -> Fixture:
    """Parabolic reflector with back ribs, feed horn and gimbal."""
    depth = radius * 0.32 if depth is None else depth
    fx = Fixture()
    profile = []
    for i in range(rings + 1):
        t = i / rings
        r = radius * t
        z = depth * t * t
        profile.append((r, z))
    vertices, normals, indices = [], [], []
    for r, z in profile:
        ring_base = len(vertices)
        for i in range(segments):
            a = TWO_PI * i / segments
            ca, sa = math.cos(a), math.sin(a)
            vertices.append((r * ca, r * sa, z))
            slope = 2 * depth * (r / radius**2) if radius else 0.0
            n = np.array([-slope * ca, -slope * sa, 1.0])
            n /= np.linalg.norm(n)
            normals.append(tuple(n))
    stride = segments
    for ri in range(len(profile) - 1):
        for i in range(segments):
            j = (i + 1) % segments
            a = ri * stride + i
            a2 = ri * stride + j
            b = (ri + 1) * stride + i
            b2 = (ri + 1) * stride + j
            indices.append((a, b, a2))
            indices.append((a2, b, b2))
    reflector = Mesh(vertices, normals, indices, "reflector").recompute_normals()
    fx.add(reflector, "CeramicTile")
    back = reflector.copy()
    back.normals = -back.normals
    back.indices = back.indices[:, ::-1].copy()
    back.vertices = back.vertices * np.array([1.0, 1.0, 1.0], dtype=np.float32)
    fx.add(back.translate(0, 0, -0.06), "HullMid")
    for i in range(8):
        a = TWO_PI * i / 8
        fx.add(beam_between((0, 0, -0.4), (radius * 0.9 * math.cos(a), radius * 0.9 * math.sin(a), depth * 0.75), 0.14, 0.14), "TrussMetal")
    fx.add(primitive_cylinder(0.12, radius * 0.9, 10), "TrussMetal", loc=(0, 0, depth + radius * 0.42), rot=(math.pi / 2, 0, 0))
    fx.add(primitive_cone(0.28, 0.1, 0.5, 12), "EngineMetal", loc=(0, 0, depth + radius * 0.2))
    fx.add(primitive_torus(radius * 1.02, 0.12, segments, 8), "HullDark", loc=(0, 0, depth))
    return fx


def nav_light(color_material: str = "NavLightWhite", size: float = 0.5) -> Fixture:
    fx = Fixture()
    fx.add(primitive_sphere(size, 10, 6), color_material)
    fx.add(primitive_cylinder(size * 0.5, size * 1.2, 8), "HullDark", loc=(0, 0, -size * 0.8))
    return fx


def antenna_mast(height: float = 8.0) -> Fixture:
    fx = Fixture()
    fx.add(primitive_cylinder(0.22, height, 10), "TrussMetal", loc=(0, 0, height * 0.5))
    fx.add(primitive_cylinder(0.1, height * 0.5, 8), "TrussMetal", loc=(0, 0, height * 1.1))
    fx.add(primitive_box(0.08, 2.2, 0.08), "TrussMetal", loc=(0, 0, height * 0.86))
    fx.add(primitive_box(2.2, 0.08, 0.08), "TrussMetal", loc=(0, 0, height * 0.86))
    fx.add(primitive_sphere(0.28, 10, 6), "NavLightRed", loc=(0, 0, height * 1.36))
    return fx


def thruster_pod(nozzle_radius: float = 1.6, length: float = 4.0) -> Fixture:
    """Reaction-control thruster: housing, bell, propellant feed and glow disc."""
    fx = Fixture()
    fx.add(primitive_box(length * 0.5, nozzle_radius * 1.5, nozzle_radius * 1.5), "EngineMetal", loc=(length * 0.2, 0, 0))
    fx.add(primitive_cone(nozzle_radius * 0.55, nozzle_radius, length * 0.62, 20), "EngineMetal", loc=(-length * 0.28, 0, 0), rot=(0, -math.pi / 2, 0))
    fx.add(primitive_torus(nozzle_radius, 0.09, 20, 8), "CoilCopper", loc=(-length * 0.58, 0, 0), rot=(0, math.pi / 2, 0))
    fx.add(primitive_cylinder(nozzle_radius * 0.86, 0.06, 20), "PlasmaCore", loc=(-length * 0.56, 0, 0), rot=(0, math.pi / 2, 0))
    fx.add(primitive_cylinder(0.22, length * 0.7, 10), "PipingSteel", loc=(length * 0.3, nozzle_radius * 0.7, 0), rot=(0, math.pi / 2, 0))
    return fx


def window_band(length: float, height: float, count: int, inset: float = 0.2) -> Fixture:
    """A row of illuminated viewports (used on the exterior hull)."""
    fx = Fixture()
    if count <= 0:
        return fx
    fx.add(primitive_box(length, inset * 2, height * 1.5), "HullDark")
    step = length / count
    pane_w = step * 0.62
    for i in range(count):
        fx.add(
            primitive_box(pane_w, inset * 0.8, height),
            "WindowGlow",
            loc=(-length * 0.5 + step * (i + 0.5), -inset * 0.6, 0),
        )
    return fx


def radiator_wing(length: float, span: float, hot: bool = True) -> Fixture:
    """Deployable radiator panel: skin, ribs, coolant spine and hinge."""
    fx = Fixture()
    panel = grid_panel(span, length, thickness=0.3, ribs=max(4, int(length / 6)), rib_size=0.4)
    fx.add(panel, "RadiatorHot" if hot else "RadiatorCool")
    for i in range(3):
        fx.add(
            primitive_cylinder(0.28, length, 12),
            "PipingSteel",
            loc=(0, -span * 0.35 + i * span * 0.35, -0.35),
            rot=(0, math.pi / 2, 0),
        )
    fx.add(primitive_box(length * 0.12, 1.2, 1.2), "TrussMetal", loc=(length * 0.5 + length * 0.05, 0, 0))
    fx.add(primitive_cylinder(0.5, 1.6, 12), "EngineMetal", loc=(length * 0.5 + length * 0.05, 0, 0), rot=(math.pi / 2, 0, 0))
    return fx


def shuttle(length: float = 12.0) -> Fixture:
    """Survey shuttle parked in the hangar."""
    fx = Fixture()
    hull = primitive_box(length * 0.62, length * 0.3, length * 0.24)
    hull = merge([hull, primitive_cone(length * 0.1, length * 0.26, length * 0.4, 12).rotate(0, -math.pi / 2, 0).translate(length * 0.5, 0, 0)])
    fx.add(hull, "HullLight")
    fx.add(primitive_box(length * 0.3, length * 0.52, length * 0.05), "HullDark", loc=(-length * 0.1, 0, length * 0.13))
    for side in (-1, 1):
        fx.add(primitive_box(length * 0.28, 0.14, length * 0.16), "HullMid", loc=(-length * 0.05, side * length * 0.26, 0))
        fx.add(primitive_cylinder(0.5, length * 0.16, 12), "EngineMetal", loc=(-length * 0.36, side * length * 0.12, 0), rot=(0, math.pi / 2, 0))
        fx.add(primitive_cylinder(0.42, 0.05, 12), "PlasmaCore", loc=(-length * 0.45, side * length * 0.12, 0), rot=(0, math.pi / 2, 0))
    fx.add(primitive_box(length * 0.12, length * 0.2, 0.06), "Glass", loc=(length * 0.36, 0, length * 0.09))
    fx.add(primitive_box(length * 0.5, length * 0.06, 0.06), "HullAccent", loc=(0, -length * 0.152, length * 0.05))
    fx.add(primitive_box(length * 0.5, length * 0.06, 0.06), "HullAccent", loc=(0, length * 0.152, length * 0.05))
    for side in (-1, 1):
        fx.add(primitive_box(0.5, 0.4, 0.5), "InteriorTrim", loc=(-length * 0.1, side * length * 0.16, -length * 0.14))
    return fx


def survey_drone(size: float = 1.6) -> Fixture:
    fx = Fixture()
    fx.add(primitive_box(size, size * 0.7, size * 0.5), "HullMid")
    for side in (-1, 1):
        fx.add(primitive_box(size * 0.16, size * 1.3, size * 0.1), "TrussMetal", loc=(0, side * size * 0.85, 0))
        fx.add(primitive_cylinder(size * 0.34, 0.06, 14), "EngineMetal", loc=(-size * 0.4, side * size * 0.85, 0), rot=(math.pi / 2, 0, 0))
    fx.add(primitive_sphere(size * 0.2, 12, 8), "Glass", loc=(size * 0.45, 0, size * 0.08))
    fx.add(primitive_box(size * 0.1, size * 0.3, size * 0.06), "ScreenAmber", loc=(size * 0.2, 0, size * 0.28))
    fx.add(primitive_cylinder(size * 0.12, size * 0.5, 10), "TrussMetal", loc=(-size * 0.1, 0, size * 0.4), rot=(0.3, 0, 0))
    return fx


def docking_collar(radius: float = 3.0) -> Fixture:
    fx = Fixture()
    fx.add(primitive_tube(radius + 0.5, radius, 2.4, 24), "HullDark")
    fx.add(primitive_torus(radius + 0.55, 0.22, 24, 10), "TrussMetal", loc=(0, 0, 1.0))
    fx.add(primitive_torus(radius + 0.55, 0.22, 24, 10), "TrussMetal", loc=(0, 0, -1.0))
    for i in range(8):
        a = TWO_PI * i / 8
        fx.add(
            primitive_box(0.5, 0.5, 0.4),
            "EngineMetal",
            loc=(math.cos(a) * (radius + 0.6), math.sin(a) * (radius + 0.6), 0),
            rot=(0, 0, a),
        )
    for i in range(4):
        a = TWO_PI * (i + 0.5) / 4
        fx.add(primitive_sphere(0.28, 10, 6), "NavLightWhite",
                 loc=(math.cos(a) * (radius + 0.7), math.sin(a) * (radius + 0.7), 1.2))
    return fx


def hangar_door(width: float, length: float, split: int = 2) -> Fixture:
    fx = Fixture()
    panel_w = width / split
    for i in range(split):
        y = -width * 0.5 + panel_w * (i + 0.5)
        fx.add(primitive_box(length, panel_w * 0.94, 0.5), "HullDark", loc=(0, y, 0))
        fx.add(primitive_box(length * 0.9, panel_w * 0.2, 0.12), "DeckHazard", loc=(0, y, 0.3))
    fx.add(primitive_box(length + 1.2, 0.6, 0.9), "TrussMetal", loc=(0, -width * 0.5 - 0.3, 0))
    fx.add(primitive_box(length + 1.2, 0.6, 0.9), "TrussMetal", loc=(0, width * 0.5 + 0.3, 0))
    return fx


def truss_section(length: float, width: float, height: float, bays: int, member: float = 0.7) -> Fixture:
    fx = Fixture()
    fx.add(lattice_truss((0, 0, 0), (length, 0, 0), width, height, bays, member), "TrussMetal")
    return fx


def scale_figure(height: float = 1.82) -> Fixture:
    """A simple stylised crew figure used purely as a human-scale reference.

    The figure stands on the local ``z = 0`` plane, faces ``+X`` and is about
    ``height`` metres tall. It is deliberately low-poly so it never dominates
    the triangle budget of the assemblies it is placed into.
    """
    fx = Fixture()
    h = float(height)
    # Vertical proportions (fraction of total height).
    leg_top = h * 0.52
    torso_top = h * 0.80
    head_r = h * 0.062

    # Legs.
    leg_r = h * 0.048
    leg_len = leg_top
    for side in (-1.0, 1.0):
        fx.add(
            primitive_cylinder(leg_r, leg_len, segments=10, caps=True),
            "FabricBlue",
            loc=(0.0, side * h * 0.075, leg_len * 0.5),
        )
    # Hips / pelvis.
    fx.add(
        primitive_box(h * 0.10, h * 0.20, h * 0.10),
        "FabricTeal",
        loc=(0.0, 0.0, leg_top + h * 0.02),
    )
    # Torso.
    torso_len = torso_top - leg_top - h * 0.04
    fx.add(
        primitive_cylinder(h * 0.115, torso_len, segments=12, caps=True),
        "FabricTeal",
        loc=(0.0, 0.0, leg_top + h * 0.04 + torso_len * 0.5),
    )
    # Arms.
    arm_r = h * 0.038
    arm_len = torso_len * 0.92
    for side in (-1.0, 1.0):
        fx.add(
            primitive_cylinder(arm_r, arm_len, segments=8, caps=True),
            "FabricBlue",
            loc=(0.0, side * h * 0.145, leg_top + h * 0.05 + arm_len * 0.5),
        )
    # Neck + head.
    fx.add(
        primitive_cylinder(h * 0.035, h * 0.045, segments=8, caps=True),
        "FabricBlue",
        loc=(0.0, 0.0, torso_top + h * 0.01),
    )
    fx.add(
        primitive_sphere(head_r, segments=14, rings=10),
        "MedicalWhite",
        loc=(h * 0.012, 0.0, torso_top + h * 0.045 + head_r),
    )
    return fx
