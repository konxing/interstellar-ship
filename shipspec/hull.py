"""Exterior hull, spine, thermal, centrifuge, propulsion and sensor assemblies.

``build_exterior()`` returns a :class:`~shipspec.part.Builder` holding every
component of the complete ship, tagged with the system/deck it belongs to so
the exporter can produce the full-vessel GLB, per-deck GLBs or isolated systems.
"""

from __future__ import annotations

import math

import numpy as np

from geometry.mesh import (
    beam_between,
    hex_profile,
    merge,
    primitive_box,
    primitive_cone,
    primitive_cylinder,
    primitive_loft,
    primitive_sphere,
    primitive_torus,
    primitive_tube,
)
from shipspec import exterior_detail as xd
from shipspec import fixtures as fx
from shipspec.constants import (
    BOW_TAPER_X,
    BOW_TIP_X,
    CENTRIFUGE_RADIUS,
    CENTRIFUGE_SPOKES,
    CENTRIFUGE_TUBE,
    CENTRIFUGE_X,
    DECKS,
    DECK_HEIGHT,
    DOCKING_PORTS,
    ENGINE_BLOCK_X_AFT,
    HAB_BLOCK_X_AFT,
    HAB_BLOCK_X_FWD,
    HANGAR_HALF_WIDTH,
    HANGAR_X,
    HULL_BEAM,
    HULL_CHAMFER,
    HULL_HEIGHT,
    MAIN_NOZZLES,
    MANEUVER_PODS,
    NOZZLE_EXIT_X,
    RADIATOR_HEIGHT,
    RADIATOR_SPAN,
    RADIATOR_X_AFT,
    RADIATOR_X_FWD,
    SENSOR_DISH_RADIUS,
    SENSOR_DISH_X,
    SENSOR_DISH_Z,
    SPINE_X_AFT,
    TANK_A_RADIUS,
    TANK_A_X,
    TANK_B_RADIUS,
    TANK_B_X,
    hull_half_width,
    hull_stations,
)
from shipspec.part import Builder

TWO_PI = math.pi * 2.0
HULL_PROFILE = hex_profile(HULL_BEAM, HULL_HEIGHT, HULL_CHAMFER)


# --------------------------------------------------------------------------- #
# Primary structure
# --------------------------------------------------------------------------- #
def _pressure_hull(builder: Builder) -> None:
    """Habitable block, bow taper and stern core of the pressure hull."""
    hab_stations = [
        (x, s, HULL_PROFILE)
        for x, s in hull_stations()
        if HAB_BLOCK_X_AFT - 0.5 <= x <= HAB_BLOCK_X_FWD + 0.5
    ]
    builder.multi(
        "HULL_PressureShell_HabBlock",
        "Pressure Hull - Habitable Block",
        "SYS_HULL",
        [(primitive_loft(hab_stations, "hab"), "HullLight")],
        description=(
            "Four-deck pressurised habitable block, 140 m long, chamfered hexagonal "
            "cross-section 64 m x 28 m. Whipple shield and meteoroid bumper forward."
        ),
        tags=("structure", "pressure"),
    )

    bow_stations = [
        (x, s, HULL_PROFILE)
        for x, s in hull_stations()
        if x >= HAB_BLOCK_X_FWD - 0.5
    ]
    builder.multi(
        "HULL_BowSection",
        "Bow Section & Sensor Nose",
        "SYS_HULL",
        [
            (primitive_loft(bow_stations, "bow"), "HullMid"),
            (_bow_aperture(), "WindowGlow"),
            *xd.bow_nose_detail().merge_per_material(),
        ],
        description=(
            "Tapered bow housing the long baseline sensor suite, astronavigation "
            "package and the Whipple shield stand-off structure."
        ),
        tags=("structure", "sensors"),
    )

    stern_profile = hex_profile(50.0, 30.0, 0.18)
    stern_stations = [
        (SPINE_X_AFT, 0.92, stern_profile),
        (SPINE_X_AFT - 18.0, 1.0, stern_profile),
        (ENGINE_BLOCK_X_AFT + 18.0, 1.0, stern_profile),
        (ENGINE_BLOCK_X_AFT, 0.96, stern_profile),
    ]
    builder.multi(
        "HULL_EngineeringCore",
        "Engineering Core & Reactor Shielding",
        "SYS_ENGINEERING",
        [
            (primitive_loft(stern_stations, "stern"), "HullDark"),
            (_engine_core_ribs(), "TrussMetal"),
        ],
        deck=4,
        description=(
            "Armoured engineering core: reactor shielding drum, power conditioning "
            "and the thrust structure that carries the main drive."
        ),
        tags=("structure", "propulsion"),
    )

    builder.multi(
        "HULL_WhippleShield",
        "Whipple Meteoroid Shield",
        "SYS_HULL",
        [(_whipple_shield(), "HullDark")],
        description=(
            "Stand-off bumper shield ahead of the habitable block, spaced 3 m from "
            "the pressure hull to break up hypervelocity particles."
        ),
        tags=("structure", "protection"),
    )

    builder.multi(
        "HULL_DeckStrakes",
        "Hull Plating Strakes & Deck Lines",
        "SYS_HULL",
        [(_hull_plating(), "HullMid"), (_livery(), "HullAccent")],
        description=(
            "External hull plating seams marking each pressure deck, plus the "
            "directorate livery stripe and registry markings."
        ),
        tags=("structure", "detail"),
    )

    builder.multi(
        "HULL_ArmourBelt",
        "Segmented Armour Belt",
        "SYS_HULL",
        xd.armour_belt().merge_per_material(),
        description=(
            "Segmented ceramic-composite armour over both flanks and the dorsal "
            "spine, with bolted plate edges, hazard markings and offset seams."
        ),
        tags=("structure", "detail", "protection"),
    )

    builder.multi(
        "HULL_SurfaceGreebles",
        "Hull Surface Systems & Greebles",
        "SYS_HULL",
        xd.surface_greebles().merge_per_material(),
        description=(
            "Vents, junction boxes, cable ducts, inspection hatches, sensor pods "
            "and cargo pods fitted tight to the outer skin."
        ),
        tags=("structure", "detail", "utility"),
    )

    builder.multi(
        "HULL_FrameRings",
        "Transverse Frame Rings",
        "SYS_HULL",
        xd.frame_rings().merge_per_material(),
        description=(
            "Exposed transverse frames every 7 m: eight-member belt beams standing "
            "proud of the plating with bolted corner gussets."
        ),
        tags=("structure", "detail"),
    )

    builder.multi(
        "HULL_DorsalSpineConduit",
        "Dorsal Spine Conduit",
        "SYS_HULL",
        [(_dorsal_conduit(), "TrussMetal")],
        description=(
            "External cable and coolant raceway running the length of the "
            "habitable block, with maintenance crawlers every 20 m."
        ),
        tags=("structure", "utility"),
    )


def _bow_aperture():
    """Illuminated sensor aperture ring at the nose."""
    parts = []
    x = BOW_TIP_X - 6.0
    ring = primitive_torus(3.4, 0.35, 20, 8).rotate(0, math.pi / 2, 0).translate(x, 0, 0)
    parts.append(ring)
    for i in range(6):
        a = TWO_PI * i / 6
        parts.append(
            primitive_sphere(0.55, 10, 6).translate(x + 1.0, math.cos(a) * 2.2, math.sin(a) * 2.2)
        )
    return merge(parts, "bow_aperture")


def _engine_core_ribs():
    parts = []
    for x in np.linspace(SPINE_X_AFT - 4.0, ENGINE_BLOCK_X_AFT + 6.0, 7):
        parts.append(
            primitive_torus(17.5, 0.55, 26, 8)
            .scale(1.0, 1.42, 1.0)
            .translate(float(x), 0, 0)
        )
    return merge(parts, "core_ribs")


def _whipple_shield():
    """Thin stand-off shield ahead of the habitable block."""
    profile = hex_profile(HULL_BEAM + 5.0, HULL_HEIGHT + 5.0, HULL_CHAMFER)
    stations = [(HAB_BLOCK_X_FWD + 2.0, 1.0, profile), (HAB_BLOCK_X_FWD + 14.0, 0.86, profile)]
    shield = primitive_loft(stations, "shield", cap_ends=False)
    posts = []
    for x in (HAB_BLOCK_X_FWD + 3.0, HAB_BLOCK_X_FWD + 9.0, HAB_BLOCK_X_FWD + 13.0):
        for i in range(8):
            a = TWO_PI * i / 8
            y = math.cos(a) * (HULL_BEAM * 0.5 + 1.2)
            z = math.sin(a) * (HULL_HEIGHT * 0.5 + 1.2)
            posts.append(beam_between((x, y * 0.98, z * 0.98), (x, y, z), 0.4, 0.4))
    return merge([shield, *posts], "whipple")


def _hull_plating():
    """Deck separator bands, panel seams and hull furniture."""
    parts = []
    for deck in DECKS:
        z = deck.z_bottom
        half = hull_half_width(z)
        for side in (-1, 1):
            parts.append(
                primitive_box(HAB_BLOCK_X_FWD - HAB_BLOCK_X_AFT + 6.0, 0.9, 0.9)
                .translate((HAB_BLOCK_X_AFT + HAB_BLOCK_X_FWD) * 0.5 - 1.0, side * (half - 0.2), z)
            )
    for x in np.arange(HAB_BLOCK_X_AFT + 8.0, HAB_BLOCK_X_FWD, 14.0):
        for side in (-1, 1):
            parts.append(
                primitive_box(0.7, 0.7, HULL_HEIGHT * 0.86).translate(float(x), side * (HULL_BEAM * 0.5 - 0.25), 0)
            )
    # Ventral keel beam and dorsal spine rail.
    parts.append(primitive_box(HAB_BLOCK_X_FWD - HAB_BLOCK_X_AFT, 4.0, 1.6).translate(
        (HAB_BLOCK_X_AFT + HAB_BLOCK_X_FWD) * 0.5, 0, -HULL_HEIGHT * 0.5 - 0.7))
    parts.append(primitive_box(HAB_BLOCK_X_FWD - HAB_BLOCK_X_AFT, 2.4, 1.2).translate(
        (HAB_BLOCK_X_AFT + HAB_BLOCK_X_FWD) * 0.5, 0, HULL_HEIGHT * 0.5 + 0.5))
    # Life support intakes and hull mounted equipment lockers.
    for x in (56.0, 96.0, 136.0):
        for side in (-1, 1):
            parts.append(primitive_box(9.0, 2.6, 4.0).translate(x, side * (HULL_BEAM * 0.5 + 1.0), -9.0))
    return merge(parts, "plating")


def _livery():
    """Accent stripes and the registry band."""
    parts = []
    mid_x = (HAB_BLOCK_X_AFT + HAB_BLOCK_X_FWD) * 0.5
    length = HAB_BLOCK_X_FWD - HAB_BLOCK_X_AFT
    for side in (-1, 1):
        parts.append(
            primitive_box(length * 0.9, 0.4, 1.8).translate(mid_x, side * (HULL_BEAM * 0.5 + 0.25), 4.0)
        )
    parts.append(primitive_box(length * 0.42, 0.4, 3.2).translate(mid_x - 18.0, HULL_BEAM * 0.5 + 0.25, -2.0))
    parts.append(primitive_box(length * 0.42, 0.4, 3.2).translate(mid_x - 18.0, -(HULL_BEAM * 0.5 + 0.25), -2.0))
    return merge(parts, "livery")


def _dorsal_conduit():
    parts = []
    for offset in (-3.4, 3.4):
        parts.append(
            primitive_box(HAB_BLOCK_X_FWD - HAB_BLOCK_X_AFT - 8.0, 1.4, 1.4)
            .translate((HAB_BLOCK_X_AFT + HAB_BLOCK_X_FWD) * 0.5, offset, HULL_HEIGHT * 0.5 + 1.4)
        )
    for x in np.arange(HAB_BLOCK_X_AFT + 10.0, HAB_BLOCK_X_FWD - 6.0, 20.0):
        parts.append(primitive_box(2.4, 9.0, 1.0).translate(float(x), 0, HULL_HEIGHT * 0.5 + 1.0))
    return merge(parts, "dorsal_conduit")


# --------------------------------------------------------------------------- #
# Deck exteriors (window bands, blisters, deck specific hardware)
# --------------------------------------------------------------------------- #
def _deck_exteriors(builder: Builder) -> None:
    for deck in DECKS:
        z_center = deck.z_bottom + DECK_HEIGHT * 0.5
        half = hull_half_width(z_center)
        windows = []
        for side in (-1, 1):
            band = xd.framed_window_band(length=112.0, height=1.2, count=26)
            rot = (0, 0, 0) if side > 0 else (0, 0, math.pi)
            for mesh, material in band:
                placed = mesh.copy().rotate(*rot).translate(96.0, side * (half + 0.02), z_center)
                windows.append((placed, material))
        builder.multi(
            f"DECK{deck.index:02d}_ViewportBand",
            f"{deck.name} - Viewport Band",
            deck.system,
            windows,
            deck=deck.index,
            description=(
                "Illuminated viewport band and radiation shutters for "
                f"{deck.name.lower()}."
            ),
            tags=("deck", "exterior"),
        )

    # Deck 01: bridge blister with wrap-around glazing.
    builder.multi(
        "DECK01_BridgeBlister",
        "Bridge Observation Blister",
        "SYS_COMMAND",
        _bridge_blister(),
        deck=1,
        description=(
            "Armoured observation blister above the bridge with 220 degree "
            "glazing, electrochromic shutters and the manual helm position."
        ),
        tags=("deck", "command"),
    )

    # Deck 02: ventral hangar doors and frame.
    builder.multi(
        "DECK02_HangarDoors",
        "Shuttle Hangar Ventral Doors",
        "SYS_OPERATIONS",
        _hangar_doors(),
        deck=2,
        description=(
            "Two-leaf ventral hangar doors, 54 m x 30 m clear opening, with "
            "hydraulic rams and a magnetic capture rail for shuttle recovery."
        ),
        tags=("deck", "hangar"),
    )

    # Deck 03: life support plant and hydroponics glow panels.
    builder.multi(
        "DECK03_LifeSupportPlant",
        "Life Support & Hydroponics Plant",
        "SYS_HABITAT",
        _life_support_plant(),
        deck=3,
        description=(
            "External life support heat exchangers, CO2 scrubber intakes and the "
            "illuminated hydroponics growth racks visible through the hull glazing."
        ),
        tags=("deck", "life-support"),
    )

    # Deck 04: reactor shielding bulge and radiator louvres.
    builder.multi(
        "DECK04_ReactorShielding",
        "Reactor Shielding & Louvres",
        "SYS_ENGINEERING",
        _reactor_shielding(),
        deck=4,
        description=(
            "Borated composite shielding drum around the fusion core with "
            "emergency dump louvres and maintenance access ports."
        ),
        tags=("deck", "propulsion"),
    )


def _bridge_blister():
    return xd.bridge_canopy().merge_per_material()


def _hangar_doors():
    fixture = fx.Fixture()
    z = DECKS[1].z_bottom + 0.4
    x = (HANGAR_X[0] + HANGAR_X[1]) * 0.5
    length = HANGAR_X[1] - HANGAR_X[0]
    fixture.extend_at(
        fx.hangar_door(width=HANGAR_HALF_WIDTH * 2.0, length=length, split=2),
        loc=(x, 0, z - 0.6),
    )
    fixture.add(primitive_box(length + 6.0, HANGAR_HALF_WIDTH * 2.4, 1.0), "HullDark", loc=(x, 0, z + 0.4))
    for i in range(4):
        fixture.add(
            primitive_sphere(0.7, 10, 6),
            "NavLightWhite",
            loc=(HANGAR_X[0] - 2.0 + i * (length + 4.0) / 3, HANGAR_HALF_WIDTH + 2.0, z - 1.4),
        )
    return fixture.merge_per_material()


def _life_support_plant():
    fixture = fx.Fixture()
    z = DECKS[2].z_bottom + DECK_HEIGHT * 0.5
    for x in (58.0, 84.0, 110.0):
        for side in (-1, 1):
            fixture.add(primitive_box(14.0, 4.0, 4.6), "HullMid", loc=(x, side * (HULL_BEAM * 0.5 + 1.8), z - 1.0))
            fixture.add(primitive_cylinder(1.3, 12.0, 12), "PipingSteel",
                        loc=(x, side * (HULL_BEAM * 0.5 + 3.9), z - 1.0), rot=(0, 0, math.pi / 2))
    # Hydroponics growth windows glow green.
    for i in range(7):
        fixture.add(primitive_box(6.0, 0.5, 2.0), "HydroGreen", loc=(52.0 + i * 15.0, HULL_BEAM * 0.5 + 0.3, z + 1.6))
    for x in (66.0, 118.0):
        fixture.extend_at(fx.antenna_mast(5.0), loc=(x, -HULL_BEAM * 0.5 - 1.0, z - 3.0), rot=(0, 0, -math.pi / 2))
    return fixture.merge_per_material()


def _reactor_shielding():
    fixture = fx.Fixture()
    z = DECKS[3].z_bottom + DECK_HEIGHT * 0.5
    fixture.add(primitive_cylinder(9.0, 26.0, 24), "ReactorShield", loc=(HAB_BLOCK_X_AFT + 22.0, 0, z), rot=(0, math.pi / 2, 0))
    fixture.add(primitive_cylinder(6.4, 27.0, 20), "ReactorGlow", loc=(HAB_BLOCK_X_AFT + 22.0, 0, z), rot=(0, math.pi / 2, 0))
    for i in range(5):
        fixture.add(primitive_torus(9.2, 0.5, 24, 8), "TrussMetal",
                    loc=(HAB_BLOCK_X_AFT + 12.0 + i * 5.0, 0, z), rot=(0, math.pi / 2, 0))
    for x in (HAB_BLOCK_X_AFT + 10.0, HAB_BLOCK_X_AFT + 34.0):
        for side in (-1, 1):
            fixture.add(primitive_box(8.0, 3.0, 5.0), "HullDark", loc=(x, side * 10.0, z - 5.0))
            fixture.add(primitive_box(7.0, 2.4, 0.4), "RadiatorHot", loc=(x, side * 10.0, z - 7.6))
    return fixture.merge_per_material()


# --------------------------------------------------------------------------- #
# Spine truss, propellant and thermal systems
# --------------------------------------------------------------------------- #
def _spine(builder: Builder) -> None:
    fixture = fx.Fixture()
    length = HAB_BLOCK_X_AFT - SPINE_X_AFT
    top = fx.truss_section(length, 12.0, 10.0, 22, member=0.9)
    fixture.extend_at(top, loc=(SPINE_X_AFT, 0, 7.0))
    bottom = fx.truss_section(length, 12.0, 10.0, 22, member=0.9)
    fixture.extend_at(bottom, loc=(SPINE_X_AFT, 0, -17.0))
    for x in np.linspace(SPINE_X_AFT, HAB_BLOCK_X_AFT, 12):
        fixture.add(beam_between((float(x), 0, 7.0), (float(x), 0, -17.0), 1.1, 1.1), "TrussMetal")
        for side in (-1, 1):
            fixture.add(beam_between((float(x), side * 6.0, 7.0), (float(x), side * 6.0, -17.0), 0.8, 0.8), "TrussMetal")
    builder.multi(
        "SPINE_MainTruss",
        "Main Spine Truss",
        "SYS_SPINE",
        fixture.merge_per_material(),
        description=(
            "178 m Warren lattice spine carrying propellant, radiators, the "
            "centrifuge bearing and the main thrust load path into the hull."
        ),
        tags=("structure", "spine"),
    )

    tanks = fx.Fixture()
    x0, x1 = TANK_A_X
    length_a = x1 - x0
    for side in (-1, 1):
        tanks.extend_at(fx.propellant_tank(TANK_A_RADIUS, length_a), loc=((x0 + x1) * 0.5, side * 13.0, -5.0))
        tanks.add(primitive_box(length_a * 0.9, 2.0, 2.0), "TrussMetal", loc=((x0 + x1) * 0.5, side * 13.0, -5.0 - TANK_A_RADIUS - 1.0))
    x0, x1 = TANK_B_X
    length_b = x1 - x0
    for y in (-19.0, 0.0, 19.0):
        tanks.extend_at(fx.propellant_tank(TANK_B_RADIUS, length_b), loc=((x0 + x1) * 0.5, y, 9.0))
        tanks.add(primitive_box(length_b * 0.9, 2.0, 2.0), "TrussMetal", loc=((x0 + x1) * 0.5, y, 9.0 + TANK_B_RADIUS + 1.0))
    # Feed lines running aft to the engine block.
    tanks.extend_at(
        fx.pipe_run([(TANK_A_X[0], -13.0, -5.0), (TANK_B_X[1] - 4.0, -13.0, -5.0), (SPINE_X_AFT - 4.0, -8.0, -2.0)], radius=0.55),
    )
    tanks.extend_at(
        fx.pipe_run([(TANK_A_X[0], 13.0, -5.0), (TANK_B_X[1] - 4.0, 13.0, -5.0), (SPINE_X_AFT - 4.0, 8.0, -2.0)], radius=0.55),
    )
    tanks.extend_at(
        fx.pipe_run([(TANK_B_X[0], 0.0, 9.0), (SPINE_X_AFT - 6.0, 0.0, 4.0)], radius=0.75),
    )
    builder.multi(
        "SPINE_PropellantTanks",
        "Propellant Tank Clusters",
        "SYS_SPINE",
        tanks.merge_per_material(),
        description=(
            "Five cryogenic tanks: two forward 9.5 m spheres for deuterium/helium-3 "
            "and three aft 8 m tanks for reaction mass, with insulated feed lines."
        ),
        tags=("spine", "propellant"),
    )


def _thermal(builder: Builder) -> None:
    wings = fx.Fixture()
    length = RADIATOR_X_FWD - RADIATOR_X_AFT
    x_center = (RADIATOR_X_AFT + RADIATOR_X_FWD) * 0.5
    for side in (-1, 1):
        for level, hot in ((14.0, True), (-14.0, False)):
            wing = fx.radiator_wing(length, RADIATOR_SPAN, hot=hot)
            rot = (0, 0, side * 0.42 if level > 0 else -side * 0.42)
            wings.extend_at(
                wing,
                loc=(x_center, side * (8.0 + RADIATOR_SPAN * 0.5 * 0.0), level),
                rot=rot,
            )
            # Frame spars, transverse ribs, tip caps and root manifold.
            detail = fx.Fixture()
            for y in (-RADIATOR_SPAN * 0.3, 0.0, RADIATOR_SPAN * 0.3):
                detail.add(primitive_box(length * 0.92, 0.3, 0.22), "TrussMetal", loc=(0, y, 0.32))
            for k in range(7):
                x = -length * 0.44 + k * (length * 0.88 / 6)
                detail.add(primitive_box(0.28, RADIATOR_SPAN * 0.96, 0.3), "EngineMetal", loc=(x, 0, 0.35))
            for x in (-length * 0.5, length * 0.5):
                detail.add(primitive_box(0.9, RADIATOR_SPAN + 1.2, 0.55), "EngineMetal", loc=(x, 0, 0.05))
            detail.add(primitive_cylinder(0.5, RADIATOR_SPAN * 0.9, 14), "PipingSteel",
                       loc=(-length * 0.5 - 0.6, 0, -0.2), rot=(math.pi / 2, 0, 0))
            detail.add(primitive_torus(1.1, 0.22, 18, 8), "EngineMetal",
                       loc=(-length * 0.5 - 0.2, 0, 0), rot=(0, math.pi / 2, 0))
            for k in range(6):
                detail.add(primitive_box(0.34, 0.34, 0.6), "TrussMetal",
                           loc=(-length * 0.4 + k * length * 0.16, 0, 0.4))
            wings.extend_at(detail, loc=(x_center, side * (8.0 + RADIATOR_SPAN * 0.5 * 0.0), level), rot=rot)
            wings.add(
                beam_between((x_center - length * 0.5, side * 6.0, level * 0.5), (x_center - length * 0.5, side * 8.0, level), 1.2, 1.2),
                "TrussMetal",
            )
    builder.multi(
        "THERMAL_RadiatorWings",
        "Primary Radiator Wings",
        "SYS_THERMAL",
        wings.merge_per_material(),
        description=(
            "Four deployable droplet-free radiator wings, 40 m x 27 m each, "
            "rejecting 940 MW of waste heat. Forward pair runs hot (reactor "
            "loop), aft pair runs cool (electronics and habitat loop)."
        ),
        tags=("thermal", "spine"),
    )

    louvres = fx.Fixture()
    for i in range(9):
        louvres.add(
            primitive_box(3.4, RADIATOR_SPAN * 0.86, 0.3),
            "RadiatorCool",
            loc=(RADIATOR_X_AFT + 2.0 + i * 4.2, 0, 22.0),
            rot=(0.5, 0, 0),
        )
    builder.multi(
        "THERMAL_AuxiliaryLouvres",
        "Auxiliary Louvre Radiators",
        "SYS_THERMAL",
        louvres.merge_per_material(),
        description="Secondary louvre radiators for burst heat rejection during manoeuvres.",
        tags=("thermal",),
    )


def _centrifuge(builder: Builder) -> None:
    ring = fx.Fixture()
    ring.add(
        primitive_torus(CENTRIFUGE_RADIUS, CENTRIFUGE_TUBE, 60, 18),
        "HullLight",
        loc=(CENTRIFUGE_X, 0, 0),
        rot=(0, math.pi / 2, 0),
    )
    # Interior deck ring + window band on the outer surface.
    ring.add(
        primitive_torus(CENTRIFUGE_RADIUS, CENTRIFUGE_TUBE * 0.45, 60, 10),
        "InteriorTrim",
        loc=(CENTRIFUGE_X, 0, 0),
        rot=(0, math.pi / 2, 0),
    )
    for i in range(48):
        a = TWO_PI * i / 48
        ring.add(
            primitive_box(1.6, 1.6, 0.5),
            "WindowGlow",
            loc=(
                CENTRIFUGE_X,
                math.cos(a) * (CENTRIFUGE_RADIUS + CENTRIFUGE_TUBE * 0.92),
                math.sin(a) * (CENTRIFUGE_RADIUS + CENTRIFUGE_TUBE * 0.92),
            ),
            rot=(a, 0, 0),
        )
    for i in range(12):
        a = TWO_PI * i / 12
        ring.add(
            primitive_box(2.2, CENTRIFUGE_TUBE * 2.05, 0.5),
            "HullAccent",
            loc=(
                CENTRIFUGE_X,
                math.cos(a) * (CENTRIFUGE_RADIUS),
                math.sin(a) * (CENTRIFUGE_RADIUS),
            ),
            rot=(a, 0, 0),
        )
    ring.extend_at(xd.centrifuge_ring_detail())
    builder.multi(
        "CENTRIFUGE_HabitatRing",
        "Centrifuge Habitat Ring R-1",
        "SYS_CENTRIFUGE",
        ring.merge_per_material(),
        description=(
            f"46 m radius rotating habitat ring at {1.6:.1f} rpm providing ~0.13 g "
            "for long duration crew health, with 48 illuminated cabins."
        ),
        tags=("habitat", "rotating"),
    )

    spokes = fx.Fixture()
    for i in range(CENTRIFUGE_SPOKES):
        a = TWO_PI * i / CENTRIFUGE_SPOKES
        outer = (
            CENTRIFUGE_X,
            math.cos(a) * (CENTRIFUGE_RADIUS - CENTRIFUGE_TUBE * 0.5),
            math.sin(a) * (CENTRIFUGE_RADIUS - CENTRIFUGE_TUBE * 0.5),
        )
        inner = (CENTRIFUGE_X, math.cos(a) * 4.0, math.sin(a) * 4.0)
        spokes.add(beam_between(inner, outer, 2.4, 2.4), "TrussMetal")
        spokes.add(beam_between(
            (CENTRIFUGE_X - 3.0, math.cos(a) * 4.0, math.sin(a) * 4.0),
            (CENTRIFUGE_X - 3.0, outer[1], outer[2]), 1.0, 1.0), "TrussMetal")
    spokes.add(primitive_cylinder(5.2, 10.0, 20), "HullMid", loc=(CENTRIFUGE_X, 0, 0), rot=(0, math.pi / 2, 0))
    spokes.add(primitive_torus(5.4, 0.5, 22, 8), "EngineMetal", loc=(CENTRIFUGE_X - 4.0, 0, 0), rot=(0, math.pi / 2, 0))
    spokes.add(primitive_torus(5.4, 0.5, 22, 8), "EngineMetal", loc=(CENTRIFUGE_X + 4.0, 0, 0), rot=(0, math.pi / 2, 0))
    spokes.extend_at(xd.centrifuge_spoke_detail())
    builder.multi(
        "CENTRIFUGE_SpokesAndHub",
        "Ring Spokes & Bearing Hub",
        "SYS_CENTRIFUGE",
        spokes.merge_per_material(),
        description=(
            "Six pressurised spokes with elevator cars and the superconducting "
            "magnetic bearing that decouples the ring from the spine."
        ),
        tags=("habitat", "rotating"),
    )


# --------------------------------------------------------------------------- #
# Propulsion
# --------------------------------------------------------------------------- #
def _propulsion(builder: Builder) -> None:
    nozzles = fx.Fixture()
    for index, (y, z, bell_radius) in enumerate(MAIN_NOZZLES, start=1):
        x_bell_start = ENGINE_BLOCK_X_AFT
        x_exit = NOZZLE_EXIT_X
        length = x_bell_start - x_exit
        nozzles.add(
            primitive_cone(bell_radius * 0.42, bell_radius, length, 30),
            "EngineMetal",
            loc=((x_bell_start + x_exit) * 0.5, y, z),
            rot=(0, -math.pi / 2, 0),
        )
        nozzles.add(
            primitive_tube(bell_radius, bell_radius - 0.6, 1.6, 30),
            "HullDark",
            loc=(x_exit + 0.8, y, z),
            rot=(0, math.pi / 2, 0),
        )
        nozzles.add(
            primitive_cylinder(bell_radius * 0.9, 0.25, 30),
            "PlasmaCore",
            loc=(x_exit + 1.4, y, z),
            rot=(0, math.pi / 2, 0),
        )
        # Magnetic nozzle coil stack.
        for c in range(7):
            t = c / 6
            radius = bell_radius * (0.46 + 0.54 * t)
            nozzles.add(
                primitive_torus(radius, 0.42, 26, 8),
                "CoilCopper",
                loc=(x_exit + 2.0 + t * (length - 6.0), y, z),
                rot=(0, math.pi / 2, 0),
            )
        nozzles.add(
            primitive_cylinder(bell_radius * 0.5, length * 0.55, 22),
            "HullDark",
            loc=(x_bell_start + length * 0.16, y, z),
            rot=(0, math.pi / 2, 0),
        )
        nozzles.add(
            primitive_torus(bell_radius * 0.62, 0.5, 22, 8),
            "TrussMetal",
            loc=(x_bell_start + 1.0, y, z),
            rot=(0, math.pi / 2, 0),
        )
    nozzles.extend_at(xd.nozzle_stiffeners())
    builder.multi(
        "PROP_MainTorchNozzles",
        "Main Fusion Torch Nozzles (x3)",
        "SYS_PROPULSION",
        nozzles.merge_per_material(),
        description=(
            "Three 3.45 MN fusion torch drives with 7-stage superconducting "
            "magnetic nozzles, gimbal mounted +/- 6 degrees for thrust vectoring."
        ),
        tags=("propulsion", "engine"),
    )

    thrust_frame = xd.engine_bay_frame()
    builder.multi(
        "PROP_ThrustStructure",
        "Thrust Structure & Gimbal Mounts",
        "SYS_PROPULSION",
        thrust_frame.merge_per_material(),
        description=(
            "Primary thrust structure transferring 3.45 MN of continuous thrust "
            "into the spine, with three gimbal rings and 18 tension struts."
        ),
        tags=("propulsion", "structure"),
    )

    pods = fx.Fixture()
    for i, (x, y, z) in enumerate(MANEUVER_PODS, start=1):
        yaw = math.pi if x > 0 else 0.0
        pods.extend_at(fx.thruster_pod(1.7, 4.6), loc=(x, y, z), rot=(0, yaw + (math.pi / 2 if x < 0 else -math.pi / 2), 0))
        pods.add(primitive_box(3.4, 3.4, 3.4), "HullDark", loc=(x + (2.0 if x < 0 else -2.0), y * 0.86, z))
    builder.multi(
        "PROP_ManeuveringThrusters",
        "Maneuvering Thruster Pods (x6)",
        "SYS_PROPULSION",
        pods.merge_per_material(),
        description=(
            "Six RCS pods (four stern, two bow) for attitude control, docking "
            "and station keeping, each with redundant injectors."
        ),
        tags=("propulsion", "rcs"),
    )

    heat = fx.Fixture()
    for x in (-160.0, -172.0, -184.0):
        heat.add(primitive_cylinder(3.2, 16.0, 16), "PipingSteel", loc=(x, 18.0, 8.0), rot=(0, 0, math.pi / 2))
        heat.add(primitive_cylinder(3.2, 16.0, 16), "PipingSteel", loc=(x, -18.0, 8.0), rot=(0, 0, math.pi / 2))
        heat.add(primitive_box(4.0, 24.0, 12.0), "HullMid", loc=(x, 0, -12.0))
    heat.extend_at(fx.pipe_run([(-150.0, 18.0, 8.0), (-190.0, 18.0, 8.0), (-200.0, 10.0, 4.0)], radius=0.5))
    heat.extend_at(fx.pipe_run([(-150.0, -18.0, 8.0), (-190.0, -18.0, 8.0), (-200.0, -10.0, 4.0)], radius=0.5))
    builder.multi(
        "PROP_HeatExchangers",
        "Engine Heat Exchangers & Plumbing",
        "SYS_PROPULSION",
        heat.merge_per_material(),
        description=(
            "Lithium heat pipes and ammonia exchangers moving drive waste heat "
            "to the aft radiator loop, with emergency dump valves."
        ),
        tags=("propulsion", "thermal"),
    )


# --------------------------------------------------------------------------- #
# Sensors, docking and services
# --------------------------------------------------------------------------- #
def _sensors(builder: Builder) -> None:
    main = fx.Fixture()
    main.extend_at(
        fx.dish(SENSOR_DISH_RADIUS, segments=34, rings=10),
        loc=(SENSOR_DISH_X, 0, SENSOR_DISH_Z + 6.0),
        rot=(-0.42, 0, 0),
    )
    main.add(primitive_cylinder(2.6, 9.0, 14), "TrussMetal", loc=(SENSOR_DISH_X, 0, SENSOR_DISH_Z + 1.0))
    main.add(primitive_box(6.0, 8.0, 3.0), "HullDark", loc=(SENSOR_DISH_X, 0, SENSOR_DISH_Z - 4.0))
    main.add(primitive_torus(3.0, 0.4, 18, 8), "EngineMetal", loc=(SENSOR_DISH_X, 0, SENSOR_DISH_Z - 3.0), rot=(math.pi / 2, 0, 0))
    builder.multi(
        "SENSORS_MainHighGainAntenna",
        "Main High-Gain Antenna (15 m)",
        "SYS_SENSORS",
        main.merge_per_material(),
        description=(
            "15 m parabolic high-gain antenna on a two-axis gimbal, providing "
            "the primary laser/RF link back to the inner system."
        ),
        tags=("sensors", "comms"),
    )

    arrays = fx.Fixture()
    for side in (-1, 1):
        arrays.extend_at(
            fx.dish(5.4, segments=22, rings=7),
            loc=(158.0, side * 22.0, 8.0),
            rot=(0, side * 0.5, 0),
        )
        arrays.extend_at(
            fx.dish(4.2, segments=20, rings=6),
            loc=(SENSOR_DISH_X - 8.0, side * 16.0, -14.0),
            rot=(0, side * -0.6, 0),
        )
    # Long baseline interferometer booms.
    for side in (-1, 1):
        arrays.add(
            beam_between((120.0, side * 8.0, -12.0), (120.0, side * 34.0, -12.0), 1.0, 1.0),
            "TrussMetal",
        )
        for i in range(5):
            arrays.add(
                primitive_box(1.6, 1.6, 1.6),
                "HullMid",
                loc=(120.0, side * (12.0 + i * 5.5), -12.0),
            )
            arrays.add(primitive_sphere(0.5, 10, 6), "WindowGlow", loc=(120.0, side * (12.0 + i * 5.5), -11.0))
    arrays.extend_at(fx.antenna_mast(11.0), loc=(176.0, 0, 12.0))
    arrays.extend_at(fx.antenna_mast(7.0), loc=(60.0, -HULL_BEAM * 0.5, -12.0), rot=(0, 0, math.pi))
    builder.multi(
        "SENSORS_ArraysAndBooms",
        "Sensor Arrays & Interferometer Booms",
        "SYS_SENSORS",
        arrays.merge_per_material(),
        description=(
            "Four auxiliary dishes, a 68 m long baseline optical interferometer "
            "and the astronavigation mast for pulsar-referenced positioning."
        ),
        tags=("sensors", "comms"),
    )


def _utility(builder: Builder) -> None:
    docking = fx.Fixture()
    for i, (x, y, z, label) in enumerate(DOCKING_PORTS, start=1):
        rot = {
            "dorsal": (0, 0, 0),
            "ventral": (math.pi, 0, 0),
            "port": (0, math.pi / 2, 0),
            "starboard": (0, -math.pi / 2, 0),
        }[label]
        docking.extend_at(fx.docking_collar(3.4 if label in ("dorsal", "ventral") else 2.6), loc=(x, y, z), rot=rot)
    builder.multi(
        "UTIL_DockingCollars",
        "Docking Collars (x4)",
        "SYS_UTILITY",
        docking.merge_per_material(),
        description=(
            "Two axial and two lateral universal docking collars for tenders, "
            "surface landers and station transfer."
        ),
        tags=("utility", "docking"),
    )

    lights = fx.Fixture()
    light_positions = [
        ("NavLightRed", (96.0, -(HULL_BEAM * 0.5 + 1.4), 0.0)),
        ("NavLightGreen", (96.0, (HULL_BEAM * 0.5 + 1.4), 0.0)),
        ("NavLightWhite", (BOW_TIP_X - 2.0, 0.0, 3.0)),
        ("NavLightWhite", (ENGINE_BLOCK_X_AFT + 4.0, 0.0, 16.0)),
        ("NavLightWhite", (CENTRIFUGE_X, 0.0, CENTRIFUGE_RADIUS + CENTRIFUGE_TUBE + 1.0)),
        ("NavLightWhite", (RADIATOR_X_AFT + 2.0, 34.0, 14.0)),
        ("NavLightWhite", (RADIATOR_X_AFT + 2.0, -34.0, 14.0)),
        ("NavLightRed", (RADIATOR_X_AFT + 2.0, 34.0, -14.0)),
        ("NavLightRed", (RADIATOR_X_AFT + 2.0, -34.0, -14.0)),
        ("NavLightGreen", (HAB_BLOCK_X_FWD + 6.0, 12.0, -12.0)),
        ("NavLightGreen", (HAB_BLOCK_X_FWD + 6.0, -12.0, -12.0)),
    ]
    for material, loc in light_positions:
        lights.extend_at(fx.nav_light(material, 0.85), loc=loc)
    builder.multi(
        "UTIL_NavigationLights",
        "Navigation & Strobe Lights",
        "SYS_UTILITY",
        lights.merge_per_material(),
        description=(
            "Port red, starboard green and white anti-collision strobes at the "
            "bow, stern, ring apex and radiator tips."
        ),
        tags=("utility", "lighting"),
    )

    services = fx.Fixture()
    # External EVA hand-rails, airlock hatches and maintenance crawlers.
    for x in (52.0, 88.0, 124.0, 156.0):
        for side in (-1, 1):
            services.add(
                primitive_box(12.0, 0.35, 0.35),
                "DeckHazard",
                loc=(x, side * (HULL_BEAM * 0.5 + 0.5), -6.0),
            )
    for x, y, z in ((70.0, -(HULL_BEAM * 0.5 + 0.4), -4.0), (140.0, (HULL_BEAM * 0.5 + 0.4), -4.0)):
        services.extend_at(fx.hatch(1.3, 2.4), loc=(x, y, z), rot=(0, math.pi / 2 if y > 0 else -math.pi / 2, 0))
    services.add(primitive_box(6.0, 6.0, 4.0), "HullMid", loc=(HAB_BLOCK_X_AFT - 3.0, 0, -12.0))
    services.add(primitive_box(30.0, 3.0, 3.0), "TrussMetal", loc=(10.0, 0, -18.0))
    builder.multi(
        "UTIL_EVAServices",
        "EVA Services & Maintenance Access",
        "SYS_UTILITY",
        services.merge_per_material(),
        description=(
            "External hand-rails, two EVA airlocks, tether points and the "
            "ventral maintenance crawler rail."
        ),
        tags=("utility", "eva"),
    )


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def build_exterior() -> Builder:
    """Build every exterior component of the complete vessel."""
    builder = Builder("DSX-01 exterior")
    _pressure_hull(builder)
    _deck_exteriors(builder)
    _spine(builder)
    _thermal(builder)
    _centrifuge(builder)
    _propulsion(builder)
    _sensors(builder)
    _utility(builder)
    return builder
