"""Per-deck models: hull band, deck plate, structure and fitted compartments.

Each deck is authored in ship coordinates (so it lines up with the full vessel
model) and re-centred at export time. The hull band uses the translucent
``Glass`` material so the fitted interior stays visible in the viewer.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from geometry.mesh import (
    hex_profile,
    primitive_box,
    primitive_cylinder,
    primitive_loft,
    primitive_torus,
    merge,
)
from shipspec import fixtures as fx
from shipspec.constants import (
    DECK_HEIGHT,
    DECK_PLATE_THICKNESS,
    HAB_BLOCK_X_AFT,
    HAB_BLOCK_X_FWD,
    HULL_BEAM,
    HULL_CHAMFER,
    HULL_HEIGHT,
    INTERIOR_CLEAR_HEIGHT,
    DeckSpec,
    hull_half_width,
)
from shipspec.part import Builder

INNER_X_AFT = HAB_BLOCK_X_AFT + 4.0
INNER_X_FWD = HAB_BLOCK_X_FWD - 4.0


# --------------------------------------------------------------------------- #
# Profile helpers
# --------------------------------------------------------------------------- #
def clip_profile_to_band(
    profile: Sequence[Sequence[float]], z_bottom: float, z_top: float
) -> list[tuple[float, float]]:
    """Sutherland-Hodgman clip of a hull profile against a horizontal band."""

    def clip(poly, inside, intersect):
        result = []
        for i in range(len(poly)):
            a = poly[i]
            b = poly[(i + 1) % len(poly)]
            a_in, b_in = inside(a), inside(b)
            if a_in:
                result.append(a)
            if a_in != b_in:
                result.append(intersect(a, b))
        return result

    def cut_z(a, b, z):
        if abs(b[1] - a[1]) < 1e-9:
            return (a[0], z)
        t = (z - a[1]) / (b[1] - a[1])
        return (a[0] + t * (b[0] - a[0]), z)

    poly = list(profile)
    poly = clip(poly, lambda p: p[1] >= z_bottom, lambda a, b: cut_z(a, b, z_bottom))
    poly = clip(poly, lambda p: p[1] <= z_top, lambda a, b: cut_z(a, b, z_top))
    return poly


def deck_hull_band(deck: DeckSpec, margin: float = 0.35) -> list[tuple[float, float]]:
    profile = hex_profile(HULL_BEAM, HULL_HEIGHT, HULL_CHAMFER)
    return clip_profile_to_band(profile, deck.z_bottom - margin, deck.z_bottom + DECK_HEIGHT + margin)


def deck_interior_width(deck: DeckSpec) -> float:
    z_center = deck.z_bottom + DECK_HEIGHT * 0.5
    return max(12.0, hull_half_width(z_center) * 2.0 - 6.0)


# --------------------------------------------------------------------------- #
# Structural elements
# --------------------------------------------------------------------------- #
def _structure(builder: Builder, deck: DeckSpec) -> None:
    band = deck_hull_band(deck)
    stations = [(x, 1.0, band) for x in (INNER_X_AFT - 4.0, 70.0, 110.0, INNER_X_FWD + 4.0)]
    builder.multi(
        f"DECK{deck.index:02d}_HullBand",
        f"{deck.name} - Hull Band (cutaway)",
        deck.system,
        [(primitive_loft(stations, "band", cap_ends=False), "Glass"),
         (primitive_loft(
             [(x, 1.0, band) for x in (INNER_X_AFT - 4.0, INNER_X_AFT - 3.4)], "ring", cap_ends=False), "HullDark"),
         (primitive_loft(
             [(x, 1.0, band) for x in (INNER_X_FWD + 3.4, INNER_X_FWD + 4.0)], "ring", cap_ends=False), "HullDark")],
        deck=deck.index,
        description=(
            "Translucent cutaway of the pressure hull for this deck. Toggle it in "
            "the viewer to look inside the fitted compartments."
        ),
        tags=("deck", "hull", "cutaway"),
    )

    length = INNER_X_FWD - INNER_X_AFT
    width = deck_interior_width(deck)
    z = deck.z_bottom
    plate = fx.Fixture()
    plate.add(primitive_box(length, width, DECK_PLATE_THICKNESS), "DeckPlate", loc=((INNER_X_AFT + INNER_X_FWD) * 0.5, 0, z - DECK_PLATE_THICKNESS * 0.5))
    # Floor graitings, cable trenches and hazard edging.
    for i in range(int(length / 8)):
        x = INNER_X_AFT + 4.0 + i * 8.0
        plate.add(primitive_box(6.4, width * 0.92, 0.06), "InteriorTrim", loc=(x, 0, z + 0.03))
    for side in (-1, 1):
        plate.add(primitive_box(length, 0.5, 0.08), "DeckHazard", loc=((INNER_X_AFT + INNER_X_FWD) * 0.5, side * (width * 0.5 - 0.4), z + 0.05))
        plate.add(primitive_box(length, 1.0, 0.9), "InteriorTrim", loc=((INNER_X_AFT + INNER_X_FWD) * 0.5, side * (width * 0.5 + 0.6), z - 0.55))
    # Deck beams and ceiling structure.
    beams = fx.Fixture()
    for i in range(int(length / 6) + 1):
        x = INNER_X_AFT + i * 6.0
        if x > INNER_X_FWD:
            break
        beams.add(primitive_box(0.7, width, 1.1), "TrussMetal", loc=(x, 0, z + DECK_HEIGHT - 0.6))
        for side in (-1, 1):
            beams.add(primitive_box(0.5, 0.5, DECK_HEIGHT - 1.0), "TrussMetal", loc=(x, side * (width * 0.5 - 0.3), z + DECK_HEIGHT * 0.5))
        beams.add(primitive_box(0.4, 0.4, 1.4), "PipingSteel", loc=(x + 1.6, width * 0.32, z + DECK_HEIGHT - 1.5))
        beams.add(primitive_box(0.4, 0.4, 1.4), "PipingSteel", loc=(x + 1.6, -width * 0.32, z + DECK_HEIGHT - 1.5))
    beams.add(primitive_box(length, 1.4, 1.4), "TrussMetal", loc=((INNER_X_AFT + INNER_X_FWD) * 0.5, 0, z + DECK_HEIGHT - 0.2))
    beams.add(primitive_box(length, width, 0.35), "DeckPlate", loc=((INNER_X_AFT + INNER_X_FWD) * 0.5, 0, z + DECK_HEIGHT + 0.15))

    builder.multi(
        f"DECK{deck.index:02d}_DeckPlate",
        f"{deck.name} - Deck Plate & Grating",
        deck.system,
        plate.merge_per_material(),
        deck=deck.index,
        description=(
            f"{DECK_PLATE_THICKNESS * 1000:.0f} mm composite deck plate with removable "
            "gratings, cable trenches and hazard edging."
        ),
        tags=("deck", "structure"),
    )
    builder.multi(
        f"DECK{deck.index:02d}_CeilingFrame",
        f"{deck.name} - Ceiling Frame & Services",
        deck.system,
        beams.merge_per_material(),
        deck=deck.index,
        description=(
            "Transverse deck beams, longitudinal girders and the service raceway "
            "carrying power, data and atmosphere ducts above the ceiling."
        ),
        tags=("deck", "structure"),
    )


# --------------------------------------------------------------------------- #
# Compartment layouts (x ranges are ship coordinates)
# --------------------------------------------------------------------------- #
def _rooms(deck: DeckSpec) -> list[dict]:
    """Compartment definitions: id, label, x range and furniture plan."""
    if deck.index == 1:
        return [
            {"id": "Bridge", "label": "Bridge", "x": (128.0, 160.0), "kind": "bridge"},
            {"id": "Navigation", "label": "Navigation & Flight Control", "x": (96.0, 126.0), "kind": "nav"},
            {"id": "CommsVault", "label": "Communications Vault", "x": (66.0, 94.0), "kind": "comms"},
            {"id": "ReadyRoom", "label": "Captain's Ready Room", "x": (INNER_X_AFT, 64.0), "kind": "ready"},
        ]
    if deck.index == 2:
        return [
            {"id": "Hangar", "label": "Shuttle Hangar", "x": (104.0, 160.0), "kind": "hangar"},
            {"id": "MissionOps", "label": "Mission Operations Centre", "x": (72.0, 102.0), "kind": "ops"},
            {"id": "ScienceLab", "label": "Science Laboratory", "x": (INNER_X_AFT, 70.0), "kind": "lab"},
        ]
    if deck.index == 3:
        return [
            {"id": "Quarters", "label": "Crew Quarters", "x": (INNER_X_AFT, 68.0), "kind": "quarters"},
            {"id": "Wardroom", "label": "Wardroom & Galley", "x": (70.0, 98.0), "kind": "wardroom"},
            {"id": "Medbay", "label": "Medical Bay", "x": (100.0, 124.0), "kind": "medbay"},
            {"id": "Hydroponics", "label": "Hydroponics Bay", "x": (126.0, 160.0), "kind": "hydro"},
        ]
    return [
        {"id": "MainEngineering", "label": "Main Engineering", "x": (INNER_X_AFT, 66.0), "kind": "engineering"},
        {"id": "MachineShop", "label": "Machine Shop", "x": (68.0, 98.0), "kind": "shop"},
        {"id": "PropellantHandling", "label": "Propellant Handling", "x": (100.0, 130.0), "kind": "propellant"},
        {"id": "Stores", "label": "Stores & Cryo Bay", "x": (132.0, 160.0), "kind": "stores"},
    ]


def fit_compartment(
    kind: str,
    x0: float,
    x1: float,
    width: float,
    z: float,
    height: float = INTERIOR_CLEAR_HEIGHT,
    windows: bool = True,
) -> fx.Fixture:
    """Fit out one compartment of the given ``kind`` inside an (x0..x1) footprint.

    Shared by the per-deck models and the standalone interior compartment tour
    so furniture layouts can never drift between deliverables.
    """
    length = x1 - x0
    center_x = (x0 + x1) * 0.5

    shell = fx.room_shell(length, width, height, rib_every=4.0)
    fixture = fx.Fixture()
    fixture.extend_at(shell, loc=(center_x, 0, z))

    # Viewports on both sides (engineering spaces get blank bulkheads instead).
    if windows:
        for side in (-1, 1):
            for i in range(max(2, int(length / 7))):
                x = x0 + length * (i + 0.5) / max(2, int(length / 7))
                fixture.add(
                    primitive_box(3.0, 0.3, 1.1),
                    "WindowGlow",
                    loc=(x, side * (width * 0.5 + 0.2), z + height * 0.62),
                )
                fixture.add(
                    primitive_box(3.6, 0.2, 1.6),
                    "InteriorTrim",
                    loc=(x, side * (width * 0.5 + 0.05), z + height * 0.62),
                )

    half_w = width * 0.5 - 1.2

    if kind == "bridge":
        for i, y in enumerate((-9.0, -4.5, 0.0, 4.5, 9.0)):
            fixture.extend_at(fx.console(3.2, 1.1), loc=(center_x + length * 0.28, y, z), rot=(0, -0.35, 0))
            fixture.extend_at(fx.command_chair(), loc=(center_x + length * 0.28 + 1.6, y, z))
        fixture.extend_at(fx.command_chair(), loc=(center_x + length * 0.05, -3.0, z + 0.45))
        fixture.extend_at(fx.command_chair(), loc=(center_x + length * 0.05, 3.0, z + 0.45))
        fixture.extend_at(fx.holo_table(2.4, 1.0), loc=(center_x - length * 0.2, 0, z))
        fixture.add(primitive_box(0.5, width * 0.8, 0.06), "DeckHazard", loc=(center_x - length * 0.34, 0, z + 0.03))
        for i in range(5):
            fixture.add(
                primitive_box(0.16, 4.4, 2.2),
                "ScreenGlow",
                loc=(center_x - length * 0.42, -10.0 + i * 5.0, z + height * 0.55),
                rot=(0, 0.18, 0),
            )
        fixture.extend_at(fx.ladder(height), loc=(center_x + length * 0.42, half_w, z))

    elif kind == "nav":
        for i in range(4):
            fixture.extend_at(fx.workstation(2.6), loc=(center_x - length * 0.25 + i * 6.0, -half_w + 2.0, z), rot=(0, math.pi / 2, 0))
            fixture.extend_at(fx.workstation(2.6), loc=(center_x - length * 0.25 + i * 6.0, half_w - 2.0, z), rot=(0, -math.pi / 2, 0))
        fixture.extend_at(fx.holo_table(1.8, 0.95), loc=(center_x + length * 0.28, 0, z))
        fixture.extend_at(fx.server_rack(), loc=(center_x - length * 0.4, half_w - 0.8, z), rot=(0, math.pi / 2, 0))
        fixture.extend_at(fx.server_rack(), loc=(center_x - length * 0.4 + 1.4, half_w - 0.8, z), rot=(0, math.pi / 2, 0))

    elif kind == "comms":
        for i in range(6):
            fixture.extend_at(fx.server_rack(0.9, 1.2, 2.4), loc=(center_x - length * 0.34 + (i % 3) * 3.4, -half_w + 1.4 + (i // 3) * 5.0, z))
        for i in range(4):
            fixture.extend_at(fx.console(2.2, 0.8, 1.0), loc=(center_x + length * 0.1 + i * 3.0, half_w - 1.6, z), rot=(0, math.pi, 0))
        fixture.add(primitive_cylinder(1.6, height * 0.9, 16), "CoilCopper", loc=(center_x + length * 0.34, 0, z + height * 0.45))
        fixture.add(primitive_torus(1.8, 0.16, 20, 8), "PipingSteel", loc=(center_x + length * 0.34, 0, z + height * 0.8))

    elif kind == "ready":
        fixture.extend_at(fx.mess_table(3.0, 1.3), loc=(center_x - length * 0.1, 0, z))
        for i in range(3):
            fixture.extend_at(fx.workstation(2.2), loc=(center_x - length * 0.3 + i * 5.0, -half_w + 1.6, z), rot=(0, math.pi / 2, 0))
        fixture.extend_at(fx.storage_rack(3.0, 0.7, 2.2), loc=(center_x + length * 0.2, half_w - 0.8, z), rot=(0, math.pi / 2, 0))
        fixture.extend_at(fx.console(2.6, 1.0), loc=(center_x + length * 0.36, -4.0, z), rot=(0, -math.pi / 2, 0))

    elif kind == "hangar":
        # Double-height bay: deck markings, shuttle, drone racks and cranes.
        fixture.add(primitive_box(length * 0.9, width * 0.86, 0.04), "InteriorFloor", loc=(center_x, 0, z + 0.02))
        for i in range(6):
            fixture.add(primitive_box(0.35, width * 0.8, 0.03), "DeckHazard", loc=(x0 + 3.0 + i * (length - 6.0) / 5, 0, z + 0.05))
        fixture.extend_at(fx.shuttle(14.0), loc=(center_x - 4.0, -8.0, z + 1.6), rot=(0, 0.0, 0))
        fixture.extend_at(fx.survey_drone(2.2), loc=(center_x + length * 0.3, 9.0, z + 1.2))
        fixture.extend_at(fx.survey_drone(2.2), loc=(center_x + length * 0.3 + 4.0, 9.0, z + 1.2))
        fixture.extend_at(fx.survey_drone(2.2), loc=(center_x + length * 0.3 + 8.0, 9.0, z + 1.2))
        fixture.add(primitive_box(length * 0.8, 0.8, 0.8), "TrussMetal", loc=(center_x, 0, z + height + 2.2))
        for i in range(3):
            fixture.add(primitive_box(1.6, width * 0.9, 0.6), "TrussMetal", loc=(x0 + 8.0 + i * (length - 16.0) / 2, 0, z + height + 1.6))
            fixture.add(primitive_box(1.0, 1.0, 1.8), "DeckHazard", loc=(x0 + 8.0 + i * (length - 16.0) / 2, 6.0, z + height + 0.6))
        fixture.extend_at(fx.storage_rack(4.0, 0.9, 2.4), loc=(center_x - length * 0.3, half_w - 1.0, z), rot=(0, math.pi / 2, 0))
        fixture.extend_at(fx.console(3.0, 1.0), loc=(center_x + length * 0.34, half_w - 2.0, z), rot=(0, math.pi, 0))
        for i in range(4):
            fixture.add(primitive_box(6.0, 0.4, 0.4), "LightStrip", loc=(x0 + 6.0 + i * (length - 12.0) / 3, 0, z + height + 2.6))

    elif kind == "ops":
        for i in range(3):
            for y in (-8.0, 0.0, 8.0):
                fixture.extend_at(fx.console(2.8, 1.0), loc=(center_x - length * 0.25 + i * 7.0, y, z), rot=(0, -0.2, 0))
        fixture.add(primitive_box(0.2, width * 0.7, 2.6), "ScreenGlow", loc=(center_x + length * 0.42, 0, z + height * 0.5))
        fixture.extend_at(fx.storage_rack(3.4, 0.8, 2.2), loc=(center_x - length * 0.34, half_w - 1.0, z), rot=(0, math.pi / 2, 0))
        fixture.extend_at(fx.mess_table(2.0, 1.0), loc=(center_x + length * 0.2, -half_w + 3.0, z))

    elif kind == "lab":
        for i in range(4):
            fixture.extend_at(fx.lab_bench(4.2), loc=(center_x - length * 0.3 + i * 8.0, -half_w + 2.4, z), rot=(0, math.pi / 2, 0))
            fixture.extend_at(fx.lab_bench(4.2), loc=(center_x - length * 0.3 + i * 8.0, half_w - 2.4, z), rot=(0, -math.pi / 2, 0))
        for i in range(5):
            fixture.extend_at(fx.sample_pod(0.4), loc=(center_x - length * 0.2 + i * 4.0, 0, z))
        fixture.extend_at(fx.server_rack(), loc=(center_x + length * 0.4, half_w - 1.0, z), rot=(0, math.pi, 0))
        fixture.add(primitive_cylinder(2.2, height * 0.85, 18), "Glass", loc=(center_x + length * 0.1, 0, z + height * 0.42))
        fixture.add(primitive_cylinder(2.0, height * 0.2, 18), "InteriorTrim", loc=(center_x + length * 0.1, 0, z + 0.1))
        fixture.add(primitive_cylinder(2.0, height * 0.2, 18), "InteriorTrim", loc=(center_x + length * 0.1, 0, z + height * 0.8))

    elif kind == "quarters":
        for i in range(6):
            y = -half_w + 3.0 + (i % 2) * (width - 6.0)
            x = x0 + 6.0 + (i // 2) * 11.0
            fixture.extend_at(fx.bunk_stack(2), loc=(x, y, z), rot=(0, math.pi / 2 if y < 0 else -math.pi / 2, 0))
            fixture.extend_at(fx.storage_rack(1.8, 0.6, 2.2), loc=(x + 3.4, y * 0.86, z), rot=(0, math.pi / 2 if y < 0 else -math.pi / 2, 0))
        fixture.extend_at(fx.airlock_chamber(2.0, 4.0), loc=(x0 + 6.0, 0, z + 2.0), rot=(0, 0, 0))
        fixture.extend_at(fx.treadmill(), loc=(center_x + length * 0.2, -half_w + 2.0, z))
        fixture.extend_at(fx.treadmill(), loc=(center_x + length * 0.2, -half_w + 4.4, z))
        fixture.extend_at(fx.mess_table(2.2, 1.0), loc=(center_x + length * 0.32, half_w - 3.0, z))

    elif kind == "wardroom":
        fixture.extend_at(fx.galley_counter(length * 0.6), loc=(center_x - length * 0.1, -half_w + 1.4, z), rot=(0, math.pi / 2, 0))
        for i in range(3):
            fixture.extend_at(fx.mess_table(2.6, 1.2), loc=(center_x - length * 0.2 + i * 8.0, 4.0 + (i % 2) * 4.0, z))
        fixture.extend_at(fx.storage_rack(3.0, 0.8, 2.3), loc=(center_x + length * 0.36, -half_w + 1.4, z), rot=(0, math.pi / 2, 0))
        fixture.add(primitive_box(0.15, 4.0, 2.2), "ScreenGlow", loc=(center_x + length * 0.4, half_w - 0.6, z + height * 0.5), rot=(0, -0.3, 0))
        fixture.extend_at(fx.med_cabinet(), loc=(center_x + length * 0.1, half_w - 0.8, z), rot=(0, math.pi, 0))

    elif kind == "medbay":
        for i in range(3):
            fixture.extend_at(fx.medical_bed(), loc=(center_x - length * 0.25 + i * 6.5, -half_w + 3.0, z), rot=(0, math.pi / 2, 0))
        fixture.extend_at(fx.med_cabinet(), loc=(center_x - length * 0.3, half_w - 1.0, z), rot=(0, math.pi, 0))
        fixture.extend_at(fx.med_cabinet(), loc=(center_x - length * 0.3 + 1.6, half_w - 1.0, z), rot=(0, math.pi, 0))
        fixture.extend_at(fx.console(2.4, 0.9), loc=(center_x + length * 0.2, half_w - 1.6, z), rot=(0, math.pi, 0))
        fixture.extend_at(fx.lab_bench(3.0), loc=(center_x + length * 0.34, 0, z), rot=(0, math.pi / 2, 0))
        fixture.add(primitive_cylinder(1.5, height * 0.9, 18), "Glass", loc=(center_x - length * 0.05, 0, z + height * 0.45))

    elif kind == "hydro":
        for i in range(5):
            fixture.extend_at(fx.hydroponic_planter(length * 0.62, 1.6, 1.1), loc=(center_x, -half_w + 2.6 + i * 4.4, z))
        fixture.extend_at(fx.pipe_run([
            (x0 + 2.0, -half_w + 1.0, z + height - 0.4),
            (x1 - 2.0, -half_w + 1.0, z + height - 0.4),
            (x1 - 2.0, half_w - 1.0, z + height - 0.4),
        ], radius=0.2))
        fixture.extend_at(fx.console(2.2, 0.9), loc=(center_x + length * 0.38, half_w - 1.6, z), rot=(0, math.pi, 0))
        fixture.extend_at(fx.storage_rack(2.4, 0.7, 2.2), loc=(x0 + 4.0, half_w - 1.2, z), rot=(0, math.pi / 2, 0))

    elif kind == "engineering":
        fixture.extend_at(fx.reactor_core(3.6, height + 2.4), loc=(center_x - length * 0.1, 0, z))
        for i in range(4):
            fixture.extend_at(fx.turbopump(0.9, 2.2), loc=(center_x - length * 0.3 + i * 4.0, -half_w + 2.0, z + 0.6), rot=(0, math.pi / 2, 0))
        for i in range(3):
            fixture.extend_at(fx.console(3.0, 1.1), loc=(center_x + length * 0.1 + i * 5.0, half_w - 2.0, z), rot=(0, math.pi, 0))
        fixture.extend_at(fx.pipe_run([
            (center_x - length * 0.1, 4.2, z + height + 1.0),
            (center_x + length * 0.3, 4.2, z + height + 1.0),
            (center_x + length * 0.3, half_w - 0.6, z + height - 0.6),
        ], radius=0.35))
        fixture.extend_at(fx.ladder(height + 1.5), loc=(center_x - length * 0.34, half_w - 1.0, z))
        fixture.extend_at(fx.storage_rack(3.6, 0.9, 2.4), loc=(center_x + length * 0.38, -half_w + 1.4, z), rot=(0, -math.pi / 2, 0))

    elif kind == "shop":
        for i in range(3):
            fixture.extend_at(fx.workbench(4.0), loc=(center_x - length * 0.25 + i * 8.0, -half_w + 1.8, z), rot=(0, math.pi / 2, 0))
        fixture.extend_at(fx.storage_rack(4.0, 0.9, 2.4), loc=(center_x, half_w - 1.2, z), rot=(0, math.pi / 2, 0))
        for i in range(4):
            fixture.extend_at(fx.crate(1.0), loc=(center_x - length * 0.3 + i * 3.0, half_w - 4.0, z))
        fixture.extend_at(fx.turbopump(1.1, 2.6), loc=(center_x + length * 0.3, 0, z + 1.0))
        fixture.add(primitive_cylinder(1.4, height * 0.8, 16), "EngineMetal", loc=(center_x - length * 0.1, 4.0, z + height * 0.4))

    elif kind == "propellant":
        for i in range(3):
            fixture.extend_at(fx.propellant_tank(2.0, 6.0), loc=(center_x - length * 0.25 + i * 8.0, -half_w + 4.0, z + 2.2))
        fixture.extend_at(fx.pipe_run([
            (x0 + 2.0, -half_w + 4.0, z + height - 0.3),
            (x1 - 2.0, -half_w + 4.0, z + height - 0.3),
        ], radius=0.3))
        for i in range(4):
            fixture.extend_at(fx.turbopump(0.7, 1.6), loc=(center_x - length * 0.3 + i * 6.0, half_w - 2.4, z + 0.5), rot=(0, math.pi / 2, 0))
        fixture.extend_at(fx.console(3.0, 1.0), loc=(center_x + length * 0.3, half_w - 1.8, z), rot=(0, math.pi, 0))
        fixture.add(primitive_box(length * 0.7, 0.6, 0.06), "DeckHazard", loc=(center_x, 0, z + 0.04))

    elif kind == "stores":
        for i in range(5):
            fixture.extend_at(fx.storage_rack(5.0, 1.0, 2.5, shelves=5), loc=(center_x - length * 0.3 + (i % 3) * 9.0, -half_w + 2.0 + (i // 3) * 9.0, z), rot=(0, math.pi / 2, 0))
        for i in range(6):
            fixture.extend_at(fx.crate(1.1), loc=(center_x - length * 0.2 + (i % 3) * 4.5, half_w - 3.0 - (i // 3) * 3.0, z))
        fixture.add(primitive_cylinder(1.9, height * 0.92, 20), "Glass", loc=(center_x + length * 0.32, -half_w + 3.0, z + height * 0.46))
        fixture.add(primitive_cylinder(1.9, 0.2, 20), "MedicalWhite", loc=(center_x + length * 0.32, -half_w + 3.0, z + 0.1))
        fixture.extend_at(fx.console(2.0, 0.8), loc=(center_x + length * 0.32, half_w - 1.6, z), rot=(0, math.pi, 0))

    return fixture


def _fit_room(deck: DeckSpec, room: dict) -> fx.Fixture:
    """Compartment fit-out using this deck's envelope."""
    x0, x1 = room["x"]
    return fit_compartment(
        room["kind"],
        x0,
        x1,
        width=deck_interior_width(deck) - 2.4,
        z=deck.z_bottom + DECK_PLATE_THICKNESS,
        windows=deck.index != 4,
    )


def build_deck(deck: DeckSpec) -> Builder:
    """Build the complete model of one pressure deck."""
    builder = Builder(deck.key)
    _structure(builder, deck)
    for room in _rooms(deck):
        builder.multi(
            f"DECK{deck.index:02d}_Room_{room['id']}",
            room["label"],
            deck.system,
            _fit_room(deck, room).merge_per_material(),
            deck=deck.index,
            description=f"{room['label']} - {deck.name}.",
            tags=("deck", "interior", room["kind"]),
        )
    return builder
