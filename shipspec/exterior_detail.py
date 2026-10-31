"""Surface detail layered onto the exterior hull.

The pressure hull loft is deliberately smooth - it is the structural envelope.
Everything that makes the ship read as a worked industrial vehicle is added
here: segmented armour belts, deterministic greebles hugging the skin, framed
viewport bands, an articulated bridge canopy, centrifuge cabin pods and the
open lattice of the engine bay.
"""

from __future__ import annotations

import math
import random
from typing import Sequence

import numpy as np

from geometry.mesh import (
    beam_between,
    grid_panel,
    merge,
    primitive_box,
    primitive_cone,
    primitive_cylinder,
    primitive_sphere,
    primitive_torus,
    primitive_tube,
)
from shipspec import fixtures as fx
from shipspec.constants import (
    BOW_TIP_X,
    CENTRIFUGE_RADIUS,
    CENTRIFUGE_TUBE,
    CENTRIFUGE_X,
    ENGINE_BLOCK_X_AFT,
    HAB_BLOCK_X_AFT,
    HAB_BLOCK_X_FWD,
    HULL_BEAM,
    HULL_HEIGHT,
    MAIN_NOZZLES,
    NOZZLE_EXIT_X,
    SPINE_X_AFT,
    hull_half_width,
    hull_stations,
)

TWO_PI = math.pi * 2.0
HALF_BEAM = HULL_BEAM * 0.5
HALF_HEIGHT = HULL_HEIGHT * 0.5


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _bow_scale(x: float) -> float:
    stations = hull_stations()
    for (x0, s0), (x1, s1) in zip(stations, stations[1:]):
        if x0 <= x <= x1:
            return s0 + (s1 - s0) * ((x - x0) / max(x1 - x0, 1e-6))
    return stations[-1][1]


# --------------------------------------------------------------------------- #
# Armour belt
# --------------------------------------------------------------------------- #
def armour_belt() -> fx.Fixture:
    """Segmented armour plating along both flanks plus a dorsal spine plate."""
    f = fx.Fixture()
    x0, x1 = HAB_BLOCK_X_AFT + 4.0, HAB_BLOCK_X_FWD - 4.0
    seg, gap = 7.6, 0.6
    count = int((x1 - x0) // (seg + gap))
    for side in (-1, 1):
        for z_lo, z_hi, plate in ((4.4, 10.2, "HullDark"), (-10.2, -4.4, "HullMid")):
            zc = (z_lo + z_hi) * 0.5
            height = z_hi - z_lo
            for i in range(count):
                x = x0 + seg * 0.5 + i * (seg + gap)
                f.add(primitive_box(seg, 0.8, height), plate, loc=(x, side * (HALF_BEAM + 0.4), zc))
                for z_edge in (z_lo + 0.35, z_hi - 0.35):
                    f.add(primitive_box(seg, 0.42, 0.36), "HullAccent",
                          loc=(x, side * (HALF_BEAM + 0.76), z_edge))
                for dx in (-seg * 0.36, seg * 0.36):
                    f.add(primitive_box(0.5, 0.24, 0.5), "TrussMetal",
                          loc=(x + dx, side * (HALF_BEAM + 0.9), zc))
                if i % 3 == 1:
                    f.add(primitive_box(1.6, 0.26, height * 0.46), "DeckHazard",
                          loc=(x, side * (HALF_BEAM + 0.84), zc))
    # Dorsal spine plate: lower, wider segments between the dorsal conduits.
    for i in range(18):
        x = x0 + 3.6 + i * 7.1
        f.add(primitive_box(6.4, 0.5, 1.6), "HullDark", loc=(x, 0, HALF_HEIGHT + 0.3))
        f.add(primitive_box(0.36, 0.24, 1.9), "HullAccent", loc=(x + 3.4, 0, HALF_HEIGHT + 0.45))
    return f


# --------------------------------------------------------------------------- #
# Hull panel seams and surface greebles
# --------------------------------------------------------------------------- #
def _flank_cluster(rng: random.Random) -> fx.Fixture:
    """One small piece of surface hardware, local +Y pointing outboard."""
    f = fx.Fixture()
    kind = rng.randrange(8)
    if kind == 0:  # vent grille
        f.add(primitive_box(2.6, 0.28, 1.7), "HullDark", loc=(0, 0.14, 0))
        for k in range(5):
            f.add(primitive_box(2.3, 0.16, 0.16), "HullMid", loc=(0, 0.32, -0.56 + k * 0.28))
        f.add(primitive_box(2.7, 0.1, 0.12), "TrussMetal", loc=(0, 0.34, 0.86))
    elif kind == 1:  # junction box with conduits
        f.add(primitive_box(1.3, 0.6, 1.0), "HullMid", loc=(0, 0.3, 0))
        for z in (-0.3, 0.3):
            f.add(primitive_cylinder(0.11, 2.6, 10), "PipingSteel", loc=(0, 0.62, z), rot=(0, math.pi / 2, 0))
        f.add(primitive_box(1.5, 0.18, 0.25), "HullDark", loc=(0, 0.66, 0.62))
    elif kind == 2:  # pipe run
        for z in (-0.42, 0.0, 0.42):
            f.add(primitive_cylinder(0.14, 3.4, 12), "PipingSteel", loc=(0, 0.46, z), rot=(0, math.pi / 2, 0))
        for x in (-1.1, 1.1):
            f.add(primitive_box(0.32, 0.32, 1.5), "TrussMetal", loc=(x, 0.42, 0))
    elif kind == 3:  # patch panel
        f.add(primitive_box(2.4, 0.22, 1.5), "HullMid", loc=(0, 0.11, 0))
        for sx in (-1, 1):
            for sz in (-1, 1):
                f.add(primitive_box(0.22, 0.2, 0.22), "TrussMetal", loc=(sx * 1.0, 0.2, sz * 0.6))
    elif kind == 4:  # inspection hatch
        f.add(primitive_cylinder(0.62, 0.34, 14), "HullDark", loc=(0, 0.26, 0), rot=(math.pi / 2, 0, 0))
        f.add(primitive_torus(0.7, 0.09, 14, 6), "TrussMetal", loc=(0, 0.34, 0), rot=(math.pi / 2, 0, 0))
        for k in range(4):
            a = TWO_PI * k / 4 + math.pi / 4
            f.add(primitive_box(0.2, 0.2, 0.36), "EngineMetal",
                  loc=(math.cos(a) * 0.62, 0.4, math.sin(a) * 0.62), rot=(0, 0, a))
    elif kind == 5:  # sensor pod
        f.add(primitive_cylinder(0.16, 0.9, 10), "TrussMetal", loc=(0, 0.45, 0), rot=(math.pi / 2, 0, 0))
        f.add(primitive_sphere(0.26, 10, 6), "WindowGlow", loc=(0, 0.98, 0))
        f.add(primitive_torus(0.4, 0.06, 10, 5), "PipingSteel", loc=(0, 0.24, 0), rot=(math.pi / 2, 0, 0))
    elif kind == 6:  # radiator stub
        panel = grid_panel(2.2, 2.8, 0.16, 4, 0.18)
        f.add(panel, "RadiatorCool", loc=(0, 1.0, 0), rot=(math.pi / 2, 0, 0))
        f.add(primitive_box(0.5, 0.5, 1.8), "TrussMetal", loc=(0, 0.25, 0))
    else:  # cargo pod / service module
        f.add(primitive_cylinder(0.85, 3.0, 14), "HullLight", loc=(0, 1.35, 0), rot=(0, math.pi / 2, 0))
        for x in (-0.9, 0.9):
            f.add(primitive_torus(0.9, 0.09, 14, 6), "TrussMetal", loc=(x, 1.35, 0), rot=(0, math.pi / 2, 0))
        f.add(primitive_box(0.14, 0.5, 1.4), "DeckHazard", loc=(0, 0.85, 0))
    return f


def _scaled(cluster: fx.Fixture, factor: float) -> fx.Fixture:
    out = fx.Fixture()
    for mesh, material in cluster:
        out.append((mesh.copy().scale(factor), material))
    return out


def _dorsal_cluster(rng: random.Random) -> fx.Fixture:
    """Surface hardware on a crown or keel face, local +Z pointing outboard."""
    f = fx.Fixture()
    kind = rng.randrange(6)
    if kind == 0:  # grating panel
        f.add(grid_panel(3.4, 2.2, 0.14, 4, 0.14), "TrussMetal", loc=(0, 0, 0.07))
        f.add(primitive_box(3.6, 0.16, 0.16), "HullAccent", loc=(0, 1.15, 0.18))
    elif kind == 1:  # access hatch
        f.add(primitive_cylinder(0.8, 0.36, 16), "HullDark", loc=(0, 0, 0.2))
        f.add(primitive_torus(0.88, 0.1, 16, 6), "TrussMetal", loc=(0, 0, 0.36))
        f.add(primitive_box(0.4, 0.4, 0.22), "DeckHazard", loc=(0, 0.7, 0.3))
    elif kind == 2:  # antenna base
        f.add(primitive_cylinder(0.5, 0.42, 12), "HullMid", loc=(0, 0, 0.2))
        f.add(primitive_cylinder(0.1, 2.4, 8), "TrussMetal", loc=(0, 0, 1.5))
        for k in range(3):
            a = TWO_PI * k / 3
            f.add(beam_between((0, 0, 2.6), (math.cos(a) * 0.6, math.sin(a) * 0.6, 1.7), 0.06, 0.06), "PipingSteel")
        f.add(primitive_sphere(0.16, 8, 5), "NavLightWhite", loc=(0, 0, 2.7))
    elif kind == 3:  # cable run
        for y in (-0.32, 0.32):
            f.add(primitive_cylinder(0.13, 3.6, 10), "PipingSteel", loc=(0, y, 0.36), rot=(0, math.pi / 2, 0))
        for x in (-1.2, 0.0, 1.2):
            f.add(primitive_box(0.3, 1.1, 0.3), "TrussMetal", loc=(x, 0, 0.24))
    elif kind == 4:  # rescue beacon
        f.add(primitive_cylinder(0.34, 0.5, 10), "HullDark", loc=(0, 0, 0.25))
        f.add(primitive_sphere(0.3, 10, 6), "NavLightWhite", loc=(0, 0, 0.62))
        f.add(primitive_torus(0.4, 0.06, 10, 5), "PipingSteel", loc=(0, 0, 0.42))
    else:  # equipment locker
        f.add(primitive_box(2.0, 1.1, 0.7), "HullMid", loc=(0, 0, 0.35))
        f.add(primitive_box(1.8, 0.9, 0.1), "HullDark", loc=(0, 0, 0.74))
        f.add(primitive_box(0.12, 0.8, 0.12), "DeckHazard", loc=(0, 0.0, 0.8))
    return f


def surface_greebles() -> fx.Fixture:
    """Deterministic industrial clutter that follows the hull skin."""
    rng = random.Random(20261031)
    f = fx.Fixture()

    # Flank hardware, both sides, clear of the deck bands and chamfers.
    for side in (-1, 1):
        x = HAB_BLOCK_X_AFT + 6.0
        while x < HAB_BLOCK_X_FWD - 6.0:
            z = rng.uniform(-9.4, 9.4)
            cluster = _flank_cluster(rng)
            f.extend_at(cluster, loc=(x, side * (hull_half_width(z) + 0.02), z),
                        rot=(0, 0, 0 if side > 0 else math.pi))
            x += rng.uniform(6.0, 9.5)

    # Crown and keel hardware.
    for count, z, flip in ((18, HALF_HEIGHT + 0.02, 0.0), (14, -HALF_HEIGHT - 0.02, math.pi)):
        for _ in range(count):
            x = rng.uniform(HAB_BLOCK_X_AFT + 8.0, HAB_BLOCK_X_FWD - 8.0)
            y = rng.uniform(-20.0, 20.0)
            f.extend_at(_dorsal_cluster(rng), loc=(x, y, z), rot=(flip, 0, rng.choice((-1, 1)) * 0.0))

    # Bow taper hardware: smaller boxes scaled to the contracting section.
    for side in (-1, 1):
        for _ in range(12):
            x = rng.uniform(174.0, 238.0)
            s = _bow_scale(x)
            z = rng.uniform(-HALF_HEIGHT * s * 0.6, HALF_HEIGHT * s * 0.6)
            cluster = _scaled(_flank_cluster(rng), 0.62)
            f.extend_at(cluster, loc=(x, side * (HALF_BEAM * s + 0.02), z),
                        rot=(0, 0, 0 if side > 0 else math.pi))

    # Panel seams: recessed strips dividing the flanks into plating tiles.
    for side in (-1, 1):
        for x in np.arange(HAB_BLOCK_X_AFT + 6.0, HAB_BLOCK_X_FWD - 5.0, 6.0):
            for z in (-8.0, 0.0, 8.0):
                f.add(primitive_box(0.3, 0.16, 3.4), "HullDark",
                      loc=(float(x), side * (HALF_BEAM + 0.06), z))
        # Longitudinal cable ducts running most of the flank.
        for z in (-3.2, 3.2):
            f.add(primitive_cylinder(0.2, HAB_BLOCK_X_FWD - HAB_BLOCK_X_AFT - 12.0, 12),
                  "PipingSteel", loc=((HAB_BLOCK_X_AFT + HAB_BLOCK_X_FWD) * 0.5,
                                      side * (HALF_BEAM + 0.28), z), rot=(0, math.pi / 2, 0))
            for x in np.arange(HAB_BLOCK_X_AFT + 10.0, HAB_BLOCK_X_FWD - 8.0, 11.0):
                f.add(primitive_box(0.34, 0.36, 0.6), "TrussMetal",
                      loc=(float(x), side * (HALF_BEAM + 0.28), z))
    return f


# --------------------------------------------------------------------------- #
# Exposed structural frames
# --------------------------------------------------------------------------- #
def frame_rings() -> fx.Fixture:
    """Exterior frame bands every 7 m, standing just proud of the plating."""
    f = fx.Fixture()
    hw, hh = HALF_BEAM, HALF_HEIGHT
    cy, cz = hw * 0.22, hh * 0.22
    profile = [(hw, -hh + cz), (hw, hh - cz), (hw - cy, hh), (-hw + cy, hh),
               (-hw, hh - cz), (-hw, -hh + cz), (-hw + cy, -hh), (hw - cy, -hh)]
    for x in np.arange(HAB_BLOCK_X_AFT + 4.0, HAB_BLOCK_X_FWD - 2.0, 7.0):
        for i, (y0, z0) in enumerate(profile):
            y1, z1 = profile[(i + 1) % 8]
            f.add(beam_between((float(x), y0 * 1.008, z0 * 1.008),
                               (float(x), y1 * 1.008, z1 * 1.008), 0.34, 0.34), "TrussMetal")
        for gy, gz in profile:
            f.add(primitive_box(0.9, 0.5, 0.5), "HullDark",
                  loc=(float(x), gy * 1.012, gz * 1.012), rot=(math.atan2(gz, gy) - math.pi / 2, 0, 0))
    return f


# --------------------------------------------------------------------------- #
# Framed viewport bands
# --------------------------------------------------------------------------- #
def framed_window_band(length: float, height: float, count: int) -> fx.Fixture:
    """Viewport band with recessed frames, sills and mullions (local Y outward)."""
    f = fx.Fixture()
    step = length / count
    pane_w = step * 0.64
    f.add(primitive_box(length, 0.5, height * 1.75), "HullDark", loc=(0, -0.05, 0))
    for i in range(count):
        x = -length * 0.5 + step * (i + 0.5)
        f.add(primitive_box(pane_w + 0.34, 0.22, height + 0.34), "HullMid", loc=(x, 0.12, 0))
        f.add(primitive_box(pane_w, 0.16, height), "WindowGlow", loc=(x, 0.28, 0))
        f.add(primitive_box(pane_w + 0.5, 0.3, 0.16), "TrussMetal", loc=(x, 0.2, -height * 0.5 - 0.22))
        f.add(primitive_box(pane_w + 0.5, 0.24, 0.12), "TrussMetal", loc=(x, 0.2, height * 0.5 + 0.2))
    for i in range(count + 1):
        x = -length * 0.5 + step * i
        f.add(primitive_box(0.18, 0.5, height * 1.5), "TrussMetal", loc=(x, 0.2, 0))
    return f


# --------------------------------------------------------------------------- #
# Bridge canopy
# --------------------------------------------------------------------------- #
def bridge_canopy() -> fx.Fixture:
    """Armoured bridge blister: framed glazing, visor roof, masts and catwalk."""
    f = fx.Fixture()
    x = HAB_BLOCK_X_FWD - 12.0
    # Base sits on the hull crown (z = 14) so the glazing reads above the deck line.
    z = 13.6
    f.add(primitive_box(21.0, 31.0, 1.1), "HullDark", loc=(x, 0, z))
    f.add(primitive_box(19.0, 29.0, 0.7), "HullMid", loc=(x + 0.4, 0, z + 0.75))
    # Nine framed panes across the front arc.
    for i in range(9):
        y = -12.4 + i * 3.1
        f.add(primitive_box(0.7, 2.5, 2.7), "HullMid", loc=(x + 9.9, y, z + 2.0))
        f.add(primitive_box(0.3, 2.1, 2.2), "WindowGlow", loc=(x + 10.25, y, z + 2.1))
        f.add(primitive_box(1.6, 0.35, 2.6), "TrussMetal", loc=(x + 9.4, y + 1.55, z + 2.0))
    f.add(primitive_box(1.0, 30.0, 0.5), "TrussMetal", loc=(x + 10.0, 0, z + 3.55))
    f.add(primitive_box(1.4, 30.0, 0.6), "HullMid", loc=(x + 10.6, 0, z + 0.85))
    # Visor roof and side cheeks.
    f.add(primitive_box(22.0, 32.0, 0.5), "HullLight", loc=(x, 0, z + 3.9))
    f.add(primitive_box(4.0, 32.0, 1.0), "HullDark", loc=(x + 9.0, 0, z + 4.2), rot=(0, -0.18, 0))
    for side in (-1, 1):
        f.add(primitive_box(20.0, 0.8, 2.4), "HullMid", loc=(x, side * 15.6, z + 1.6))
        f.add(primitive_box(3.2, 2.6, 2.0), "HullDark", loc=(x - 8.4, side * 14.6, z + 1.0))
    # Roof sensor cluster and comms masts.
    f.add(primitive_cylinder(2.0, 1.6, 16), "TrussMetal", loc=(x - 2.0, 0, z + 4.9))
    f.add(primitive_torus(2.3, 0.22, 18, 6), "EngineMetal", loc=(x - 2.0, 0, z + 4.8))
    f.add(primitive_sphere(0.5, 10, 6), "WindowGlow", loc=(x - 2.0, 0, z + 5.6))
    f.extend_at(fx.antenna_mast(4.5), loc=(x - 5.0, 12.0, z + 4.2))
    f.extend_at(fx.antenna_mast(3.2), loc=(x - 5.0, -12.0, z + 4.2))
    # Rear service walkway with handrails.
    f.add(primitive_box(2.2, 30.0, 0.18), "DeckPlate", loc=(x - 10.6, 0, z + 0.6))
    for side in (-1, 1):
        f.add(primitive_box(0.14, 30.0, 0.14), "DeckHazard", loc=(x - 10.6, side * 14.8, z + 1.5))
        for i in range(8):
            f.add(primitive_box(0.14, 0.14, 0.9), "DeckHazard", loc=(x - 10.6, -13.5 + i * 3.8, z + 1.1))
    return f


# --------------------------------------------------------------------------- #
# Centrifuge cabins and rim hardware
# --------------------------------------------------------------------------- #
def centrifuge_ring_detail() -> fx.Fixture:
    """48 cabin pods, rim handrails, escape ports and hazard lighting."""
    f = fx.Fixture()
    ring_radius = CENTRIFUGE_RADIUS + CENTRIFUGE_TUBE * 0.78
    for i in range(48):
        a = TWO_PI * i / 48
        cy, cz = math.cos(a), math.sin(a)
        f.add(primitive_box(7.0, 3.6, 4.9), "HullLight",
              loc=(CENTRIFUGE_X, cy * ring_radius, cz * ring_radius), rot=(a, 0, 0))
        f.add(primitive_box(6.2, 0.3, 3.9), "HullMid",
              loc=(CENTRIFUGE_X, cy * (ring_radius + 1.7), cz * (ring_radius + 1.7)), rot=(a, 0, 0))
        f.add(primitive_box(4.2, 0.14, 1.5), "WindowGlow",
              loc=(CENTRIFUGE_X, cy * (ring_radius + 1.93), cz * (ring_radius + 1.93)), rot=(a, 0, 0))
        for dx in (-2.6, 2.6):
            f.add(primitive_box(0.5, 0.4, 4.3), "HullDark",
                  loc=(CENTRIFUGE_X + dx, cy * (ring_radius + 1.6), cz * (ring_radius + 1.6)), rot=(a, 0, 0))
        if i % 2 == 0:
            f.add(primitive_box(0.4, 0.3, 0.8), "LightStrip",
                  loc=(CENTRIFUGE_X, cy * (ring_radius + 2.05), cz * (ring_radius + 2.05)), rot=(a, 0, 0))
    # Rim handrails stay inside the 105 m overall envelope.
    for radius in (ring_radius + 2.1, ring_radius + 2.4):
        f.add(primitive_torus(radius, 0.12, 64, 6), "DeckHazard",
              loc=(CENTRIFUGE_X, 0, 0), rot=(0, math.pi / 2, 0))
        for i in range(24):
            a = TWO_PI * i / 24
            f.add(primitive_box(0.18, 0.18, 0.9), "DeckHazard",
                  loc=(CENTRIFUGE_X, math.cos(a) * radius, math.sin(a) * radius), rot=(a, 0, 0))
    # Four rim escape ports.
    for i in range(4):
        a = TWO_PI * i / 4 + math.pi / 4
        port_radius = ring_radius + 2.05
        f.extend_at(fx.docking_collar(1.5),
                    loc=(CENTRIFUGE_X, math.cos(a) * port_radius, math.sin(a) * port_radius),
                    rot=(a - math.pi / 2, 0, 0))
    return f


def centrifuge_spoke_detail() -> fx.Fixture:
    """Elevator cars and service conduits running along the six spokes."""
    f = fx.Fixture()
    inner = 6.0
    outer = CENTRIFUGE_RADIUS - CENTRIFUGE_TUBE * 0.5
    for i in range(6):
        a = TWO_PI * i / 6
        cy, cz = math.cos(a), math.sin(a)
        for t in (0.34, 0.68):
            r = inner + (outer - inner) * t
            f.add(primitive_box(3.0, 2.4, 2.6), "HullMid",
                  loc=(CENTRIFUGE_X, cy * r, cz * r), rot=(a, 0, 0))
            f.add(primitive_box(2.4, 0.14, 1.2), "WindowGlow",
                  loc=(CENTRIFUGE_X, cy * (r + 1.25), cz * (r + 1.25)), rot=(a, 0, 0))
            f.add(primitive_box(0.2, 0.2, 2.0), "DeckHazard",
                  loc=(CENTRIFUGE_X - 1.65, cy * r, cz * r), rot=(a, 0, 0))
        for offset in (-1.6, 1.6):
            f.add(primitive_cylinder(0.16, outer - inner, 10), "PipingSteel",
                  loc=(CENTRIFUGE_X + offset, cy * (inner + outer) * 0.5, cz * (inner + outer) * 0.5),
                  rot=(0, math.pi / 2, 0))
    f.add(primitive_torus(6.6, 0.3, 28, 8), "EngineMetal", loc=(CENTRIFUGE_X, 0, 0), rot=(0, math.pi / 2, 0))
    return f


# --------------------------------------------------------------------------- #
# Bow nose detail
# --------------------------------------------------------------------------- #
def bow_nose_detail() -> fx.Fixture:
    """Frames, chines and sensor pallet along the tapered bow."""
    f = fx.Fixture()
    stations = [174.0, 186.0, 198.0, 210.0, 220.0, 228.0, 236.0, 242.0]
    profile = [(HALF_BEAM, -HALF_HEIGHT + HALF_HEIGHT * 0.22),
               (HALF_BEAM, HALF_HEIGHT - HALF_HEIGHT * 0.22),
               (HALF_BEAM - HALF_BEAM * 0.22, HALF_HEIGHT),
               (-HALF_BEAM + HALF_BEAM * 0.22, HALF_HEIGHT),
               (-HALF_BEAM, HALF_HEIGHT - HALF_HEIGHT * 0.22),
               (-HALF_BEAM, -HALF_HEIGHT + HALF_HEIGHT * 0.22),
               (-HALF_BEAM + HALF_BEAM * 0.22, -HALF_HEIGHT),
               (HALF_BEAM - HALF_BEAM * 0.22, -HALF_HEIGHT)]

    def ring(x: float):
        s = _bow_scale(x)
        return [(x, y * s * 1.015, z * s * 1.015) for y, z in profile]

    rings = [ring(x) for x in stations]
    for pts in rings:
        for i in range(8):
            f.add(beam_between(pts[i], pts[(i + 1) % 8], 0.3, 0.3), "TrussMetal")
    for i in range(len(rings) - 1):
        for corner in (0, 2, 4, 6):
            f.add(beam_between(rings[i][corner], rings[i + 1][corner], 0.42, 0.42), "HullDark")
    # Nose cap stack and aperture ring.
    f.add(primitive_cylinder(2.9, 1.6, 20), "HullDark", loc=(BOW_TIP_X - 0.8, 0, 0), rot=(0, math.pi / 2, 0))
    f.add(primitive_torus(3.0, 0.28, 20, 8), "EngineMetal", loc=(BOW_TIP_X - 1.4, 0, 0), rot=(0, math.pi / 2, 0))
    f.add(primitive_cone(1.2, 0.35, 1.0, 16), "HullMid", loc=(BOW_TIP_X - 0.1, 0, 0), rot=(0, math.pi / 2, 0))
    for i in range(6):
        a = TWO_PI * i / 6
        f.add(primitive_sphere(0.4, 10, 6), "WindowGlow",
              loc=(BOW_TIP_X - 2.0, math.cos(a) * 2.2, math.sin(a) * 2.2))
    # Forward sensor pallet and small dishes.
    for side in (-1, 1):
        f.add(primitive_box(6.0, 2.2, 1.2), "HullMid",
              loc=(238.0, side * 4.4, -1.2))
        f.extend_at(fx.dish(2.0, segments=16, rings=5),
                    loc=(236.0, side * 4.6, -2.6), rot=(-0.35, side * 0.2, 0))
        f.extend_at(fx.thruster_pod(0.55, 1.3),
                    loc=(226.0, side * 7.4, 1.2), rot=(0, math.pi if side > 0 else 0, 0))
    for row in (-3, 1):
        for i in range(4):
            f.add(primitive_box(1.5, 0.3, 0.5), "WindowGlow", loc=(226.0, -4.5 + i * 3.0, row))
            f.add(primitive_box(1.8, 0.42, 0.16), "TrussMetal", loc=(226.0, -4.5 + i * 3.0, row - 0.36))
    return f


# --------------------------------------------------------------------------- #
# Main nozzle stiffening
# --------------------------------------------------------------------------- #
def nozzle_stiffeners() -> fx.Fixture:
    """Stiffener rings, stringers and actuator lugs around the three bells."""
    f = fx.Fixture()
    for y, z, bell_radius in MAIN_NOZZLES:
        x_throat = ENGINE_BLOCK_X_AFT
        x_exit = NOZZLE_EXIT_X
        length = x_throat - x_exit
        for k in range(1, 5):
            t = k / 5.0
            radius = bell_radius * (0.42 + 0.58 * t)
            f.add(primitive_torus(radius, 0.26, 32, 8), "EngineMetal",
                  loc=(x_throat - t * length, y, z), rot=(0, math.pi / 2, 0))
        for i in range(10):
            a = TWO_PI * i / 10
            f.add(beam_between(
                (x_throat + 0.6, y + math.cos(a) * bell_radius * 0.5, z + math.sin(a) * bell_radius * 0.5),
                (x_exit + 5.0, y + math.cos(a) * bell_radius * 0.93, z + math.sin(a) * bell_radius * 0.93),
                0.32, 0.32,
            ), "TrussMetal")
        for i in range(4):
            a = TWO_PI * i / 4 + math.pi / 4
            f.add(primitive_box(2.4, 0.8, 1.0), "HullDark",
                  loc=(x_throat - 4.0, y + math.cos(a) * bell_radius * 0.58, z + math.sin(a) * bell_radius * 0.58),
                  rot=(a, 0, 0))
    return f


# --------------------------------------------------------------------------- #
# Engine bay open lattice
# --------------------------------------------------------------------------- #
def engine_bay_frame() -> fx.Fixture:
    """Open thrust frame: longerons, ring frames, X-bracing and gimbal rings.

    Deliberately hollow: the space between and around the nozzle bells stays
    clear so the engine bay can be seen through from astern.
    """
    f = fx.Fixture()
    x_front = SPINE_X_AFT - 2.0
    x_back = ENGINE_BLOCK_X_AFT
    # The cradle wraps outside the outboard nozzle axes (y = +/-24) so no member
    # ever crosses a bell throat; the bay interior stays visually open.
    half_y, z_top, z_bot = 25.6, 14.4, -18.6

    for y in (-half_y, half_y):
        for z in (z_top, z_bot):
            f.add(primitive_box(x_front - x_back, 1.1, 1.1), "TrussMetal",
                  loc=((x_front + x_back) * 0.5, y, z))

    xs = np.linspace(x_front, x_back, 8)
    for k, x in enumerate(xs):
        for (ay, az), (by, bz) in (((-half_y, z_top), (half_y, z_top)),
                                   ((-half_y, z_bot), (half_y, z_bot)),
                                   ((-half_y, z_top), (-half_y, z_bot)),
                                   ((half_y, z_top), (half_y, z_bot))):
            f.add(beam_between((float(x), ay, az), (float(x), by, bz), 0.8, 0.8), "TrussMetal")
        if k < len(xs) - 1:
            x2 = float(xs[k + 1])
            for y in (-half_y, half_y):
                f.add(beam_between((float(x), y, z_top), (x2, y, z_bot), 0.45, 0.45), "TrussMetal")
                f.add(beam_between((float(x), y, z_bot), (x2, y, z_top), 0.45, 0.45), "TrussMetal")

    # Cross-bracing between the nozzle bays keeps the frame honest.
    for x in (-166.0, -182.0):
        for z in (z_top, z_bot):
            f.add(beam_between((x, -half_y, z), (x + 8.0, half_y, z), 0.4, 0.4), "TrussMetal")
            f.add(beam_between((x, half_y, z), (x + 8.0, -half_y, z), 0.4, 0.4), "TrussMetal")

    # Gimbal rings and their radial actuators, one per drive.
    for y, z, bell_radius in MAIN_NOZZLES:
        ring_radius = bell_radius * 1.28
        f.add(primitive_torus(ring_radius, 0.45, 30, 8), "EngineMetal",
              loc=(x_back + 1.2, y, z), rot=(0, math.pi / 2, 0))
        f.add(primitive_torus(ring_radius, 0.2, 30, 6), "CoilCopper",
              loc=(x_back + 3.4, y, z), rot=(0, math.pi / 2, 0))
        for i in range(6):
            a = TWO_PI * i / 6
            py, pz = y + math.cos(a) * ring_radius, z + math.sin(a) * ring_radius
            f.add(beam_between((x_back + 1.2, py, pz),
                               (x_back + 7.0, y * 0.5 + math.cos(a) * (half_y - 3.0),
                                z * 0.5 + math.sin(a) * 6.0), 0.65, 0.65), "TrussMetal")
            if i % 2 == 0:
                f.add(primitive_cylinder(0.32, 3.4, 10), "HullDark",
                      loc=(x_back + 4.2, py, pz), rot=(0, math.pi / 2, 0))
    # Stern maintenance walkway, well clear of the exhaust axis.
    f.add(primitive_box(6.0, 20.0, 0.2), "DeckPlate", loc=(x_back - 2.0, 0, z_bot - 2.4))
    for side in (-1, 1):
        f.add(primitive_box(6.0, 0.14, 0.14), "DeckHazard", loc=(x_back - 2.0, side * 9.8, z_bot - 1.4))
    return f
