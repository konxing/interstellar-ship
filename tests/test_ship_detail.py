"""Geometry-detail invariants for the refined full ship and drive study.

These tests encode what "detailed enough" means in measurable terms: the hull
must carry surface hardware instead of a bare loft, the engine bay must stay
an open lattice you can see through between the nozzles, the centrifuge ring
must read as a cabin band, and the propulsion study's gimbal yoke must not
plug the drive axis with a solid slab.
"""

from __future__ import annotations

import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from shipspec import constants as C  # noqa: E402
from shipspec import hull as hull_mod  # noqa: E402
from shipspec import propulsion as propulsion_mod  # noqa: E402
from shipspec.part import Builder  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _ship() -> Builder:
    return hull_mod.build_exterior()


def _drive() -> Builder:
    return propulsion_mod.build_propulsion()


def _part(builder: Builder, name: str):
    for part in builder.parts:
        if part.name == name:
            return part
    raise AssertionError(f"part '{name}' missing; have {[p.name for p in builder.parts]}")


def _system_triangles(builder: Builder, system: str) -> int:
    return sum(p.triangle_count for p in builder.parts if p.system == system)


def _ray_hits(part, origin, direction, tmin: float = 0.0, tmax: float = 1e9) -> bool:
    """Vectorised Moller-Trumbore test of one ray against every part primitive."""
    origin = np.asarray(origin, dtype=np.float64)
    direction = np.asarray(direction, dtype=np.float64)
    for mesh, _material in part.primitives:
        if mesh.is_empty():
            continue
        tri = mesh.vertices.astype(np.float64)[mesh.indices]
        e1 = tri[:, 1] - tri[:, 0]
        e2 = tri[:, 2] - tri[:, 0]
        pvec = np.cross(direction, e2)
        det = np.einsum("ij,ij->i", e1, pvec)
        valid = np.abs(det) > 1e-9
        inv = np.zeros_like(det)
        inv[valid] = 1.0 / det[valid]
        tvec = origin - tri[:, 0]
        u = np.einsum("ij,ij->i", tvec, pvec) * inv
        qvec = np.cross(tvec, e1)
        v = np.einsum("j,ij->i", direction, qvec) * inv
        t = np.einsum("ij,ij->i", e2, qvec) * inv
        hit = (
            valid
            & (u >= -1e-6) & (u <= 1.0 + 1e-6)
            & (v >= -1e-6) & (u + v <= 1.0 + 1e-6)
            & (t > tmin) & (t < tmax)
        )
        if bool(np.any(hit)):
            return True
    return False


def _blocked_fraction(part, axes_start: float, grid_y, grid_z, direction=(-1.0, 0.0, 0.0)) -> float:
    blocked = 0
    probes = 0
    for y in grid_y:
        for z in grid_z:
            probes += 1
            if _ray_hits(part, (axes_start, y, z), direction, tmin=1.0, tmax=80.0):
                blocked += 1
    return blocked / probes


# --------------------------------------------------------------------------- #
# Whole-ship detail budget
# --------------------------------------------------------------------------- #
def test_full_ship_carries_a_meaningful_detail_budget():
    builder = _ship()
    total = sum(p.triangle_count for p in builder.parts)
    assert total >= 120_000, f"full ship only {total} triangles; surface detail missing"
    assert total <= 450_000, f"full ship {total} triangles; over budget for a 7-asset delivery"


def test_hull_system_is_more_than_a_bare_loft():
    builder = _ship()
    hull_tris = _system_triangles(builder, "SYS_HULL")
    assert hull_tris >= 30_000, f"SYS_HULL carries only {hull_tris} triangles"


def test_hull_surface_greebles_hug_the_pressure_skin():
    part = _part(_ship(), "HULL_SurfaceGreebles")
    assert part.triangle_count >= 8_000, "greeble layer is too sparse to read at ship scale"
    lo, hi = part.bounds()
    assert lo[0] >= C.HAB_BLOCK_X_AFT - 1.0, "greebles hang off the stern end"
    assert hi[0] <= C.BOW_TIP_X + 1.0, "greebles hang past the bow tip"
    assert abs(lo[1]) <= C.HULL_BEAM * 0.5 + 6.0 and abs(hi[1]) <= C.HULL_BEAM * 0.5 + 6.0
    assert abs(lo[2]) <= C.HULL_HEIGHT * 0.5 + 6.0 and abs(hi[2]) <= C.HULL_HEIGHT * 0.5 + 6.0

    # Every vertex that sits alongside the habitable block must ride on the
    # outer skin: either on a flank (|y| at the local half beam) or on the
    # crown/keel (|z| at the half height), allowing for hardware thickness.
    half_height = C.HULL_HEIGHT * 0.5
    violations = 0
    checked = 0
    for mesh, _material in part.primitives:
        for x, y, z in mesh.vertices.astype(np.float64):
            if not (C.HAB_BLOCK_X_AFT + 1.0 <= x <= C.HAB_BLOCK_X_FWD - 1.0):
                continue
            checked += 1
            radial = max(
                abs(y) / max(C.hull_half_width(z), 1e-6),
                abs(z) / half_height,
            )
            if radial < 0.90:
                violations += 1
    assert checked > 2_000, "no greeble vertices fall alongside the habitable block"
    assert violations / checked <= 0.02, f"{violations}/{checked} greebles float inside the hull"


def test_armour_belt_wraps_the_flanks():
    part = _part(_ship(), "HULL_ArmourBelt")
    assert part.triangle_count >= 3_000
    lo, hi = part.bounds()
    assert hi[0] - lo[0] >= (C.HAB_BLOCK_X_FWD - C.HAB_BLOCK_X_AFT) * 0.55, "belt is not a belt"


def test_bow_and_bridge_are_articulated():
    builder = _ship()
    bow = _part(builder, "HULL_BowSection")
    bridge = _part(builder, "DECK01_BridgeBlister")
    assert bow.triangle_count >= 2_500, f"bow only {bow.triangle_count} triangles"
    assert bridge.triangle_count >= 1_200, f"bridge blister only {bridge.triangle_count} triangles"


def test_thermal_and_centrifuge_detail():
    builder = _ship()
    thermal = _system_triangles(builder, "SYS_THERMAL")
    centrifuge = _system_triangles(builder, "SYS_CENTRIFUGE")
    assert thermal >= 3_000, f"thermal system only {thermal} triangles"
    assert centrifuge >= 12_000, f"centrifuge ring only {centrifuge} triangles"


# --------------------------------------------------------------------------- #
# Engine bay must be an open frame, not a solid slab
# --------------------------------------------------------------------------- #
def test_engine_bay_is_an_open_lattice():
    part = _part(_ship(), "PROP_ThrustStructure")
    assert part.triangle_count >= 2_200, f"thrust frame only {part.triangle_count} triangles"

    # Look straight through the engine bay from behind: most sight lines
    # between the nozzle bells must pass through the lattice.
    grid_y = np.linspace(-24.0, 24.0, 17)
    grid_z = np.linspace(-16.0, 14.0, 11)
    blocked = _blocked_fraction(part, C.SPINE_X_AFT, grid_y, grid_z)
    assert blocked <= 0.35, f"{blocked:.0%} of engine-bay sight lines are blocked by solid structure"


def test_nozzle_exhaust_paths_are_clear():
    part = _part(_ship(), "PROP_ThrustStructure")
    for y, z, bell_radius in C.MAIN_NOZZLES:
        # A ray just inside the bell exit must run out of the ship unimpeded.
        assert not _ray_hits(part, (C.NOZZLE_EXIT_X - 2.0, y, z), (-1.0, 0.0, 0.0), tmax=200.0)
        # The throat end must open into the chamber, not into a bulkhead.
        assert not _ray_hits(part, (C.NOZZLE_EXIT_X + 4.0, y, z), (1.0, 0.0, 0.0), tmax=200.0)


# --------------------------------------------------------------------------- #
# Propulsion study: gimbal yoke keeps the drive axis open
# --------------------------------------------------------------------------- #
def test_drive_gimbal_yoke_keeps_the_axis_clear():
    part = _part(_drive(), "PROP_Drive_GimbalMount")
    assert part.triangle_count >= 3_000, f"gimbal only {part.triangle_count} triangles"
    assert not _ray_hits(part, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)), "gimbal plugs the drive axis"

    # The yoke must still surround the axis: rays at the ring radius hit it.
    hits = 0
    for i in range(8):
        a = 2.0 * np.pi * i / 8.0
        if _ray_hits(part, (0.0, np.cos(a) * 8.6, np.sin(a) * 8.6), (1.0, 0.0, 0.0)):
            hits += 1
    assert hits >= 6, f"gimbal ring only answers {hits}/8 radial rays"


def test_propulsion_study_budget():
    builder = _drive()
    total = sum(p.triangle_count for p in builder.parts)
    assert total >= 45_000, f"propulsion study only {total} triangles"
