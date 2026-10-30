"""Detailed fusion torch drive assembly (single engine, 1:1 scale).

The full-ship model carries a simplified three-engine cluster; this module
breaks one drive down into its serviceable sub-assemblies so the engineering
deck documentation and the viewer's propulsion study have something to look at.
The drive axis runs along -X, matching the vessel's stern orientation.
"""

from __future__ import annotations

import math

import numpy as np

from geometry.mesh import (
    beam_between,
    merge,
    primitive_box,
    primitive_cone,
    primitive_cylinder,
    primitive_sphere,
    primitive_torus,
    primitive_tube,
)
from shipspec import fixtures as fx

TWO_PI = math.pi * 2.0

# Drive station map (local +X = forward towards the ship, -X = exhaust).
GIMBAL_X = 18.0
INJECTOR_X = 10.0
CHAMBER_X_AFT = -2.0
CHAMBER_X_FWD = 10.0
NOZZLE_X_AFT = -22.0
NOZZLE_THROAT_RADIUS = 2.6
NOZZLE_EXIT_RADIUS = 13.0
COIL_COUNT = 9


def _gimbal_mount() -> fx.Fixture:
    fixture = fx.Fixture()
    fixture.add(primitive_box(6.0, 22.0, 22.0), "TrussMetal", loc=(GIMBAL_X + 2.0, 0, 0))
    fixture.add(primitive_torus(9.0, 1.0, 30, 10), "EngineMetal", loc=(GIMBAL_X, 0, 0), rot=(0, math.pi / 2, 0))
    fixture.add(primitive_torus(7.4, 0.7, 28, 8), "TrussMetal", loc=(GIMBAL_X - 2.4, 0, 0), rot=(0, math.pi / 2, 0))
    for i in range(4):
        a = TWO_PI * i / 4 + math.pi / 4
        fixture.add(
            primitive_cylinder(0.9, 5.0, 14),
            "EngineMetal",
            loc=(GIMBAL_X - 1.0, math.cos(a) * 8.2, math.sin(a) * 8.2),
            rot=(0, math.pi / 2, 0),
        )
        fixture.add(
            beam_between(
                (GIMBAL_X + 4.0, math.cos(a) * 10.0, math.sin(a) * 10.0),
                (GIMBAL_X - 3.0, math.cos(a) * 6.6, math.sin(a) * 6.6),
                1.0, 1.0,
            ),
            "TrussMetal",
        )
    fixture.add(primitive_box(2.0, 16.0, 3.0), "HullDark", loc=(GIMBAL_X + 4.0, 0, 9.0))
    fixture.add(primitive_box(2.0, 16.0, 3.0), "HullDark", loc=(GIMBAL_X + 4.0, 0, -9.0))
    for i in range(6):
        fixture.add(primitive_sphere(0.55, 10, 6), "PipingSteel",
                    loc=(GIMBAL_X - 2.0, math.cos(TWO_PI * i / 6) * 7.4, math.sin(TWO_PI * i / 6) * 7.4))
    return fixture


def _injector_assembly() -> fx.Fixture:
    fixture = fx.Fixture()
    fixture.add(primitive_cylinder(3.4, 2.4, 26), "EngineMetal", loc=(INJECTOR_X - 1.2, 0, 0), rot=(0, math.pi / 2, 0))
    fixture.add(primitive_cylinder(3.0, 0.5, 26), "CoilCopper", loc=(INJECTOR_X - 2.6, 0, 0), rot=(0, math.pi / 2, 0))
    # 60 coaxial injector elements on a hex pattern.
    rings = [(0.0, 1), (1.0, 6), (1.8, 12), (2.5, 18)]
    for radius, count in rings:
        for i in range(count):
            a = TWO_PI * i / count if count > 1 else 0.0
            fixture.add(
                primitive_cylinder(0.16, 1.1, 8),
                "PipingSteel",
                loc=(INJECTOR_X - 3.0, math.cos(a) * radius, math.sin(a) * radius),
                rot=(0, math.pi / 2, 0),
            )
    fixture.add(primitive_cylinder(1.5, 3.0, 18), "ReactorGlow", loc=(INJECTOR_X - 3.4, 0, 0), rot=(0, math.pi / 2, 0))
    fixture.add(primitive_torus(3.5, 0.3, 26, 8), "TrussMetal", loc=(INJECTOR_X - 0.2, 0, 0), rot=(0, math.pi / 2, 0))
    # Deuterium / helium-3 manifold ring.
    fixture.add(primitive_torus(4.4, 0.42, 28, 10), "PipingSteel", loc=(INJECTOR_X + 0.6, 0, 0), rot=(0, math.pi / 2, 0))
    for i in range(6):
        a = TWO_PI * i / 6
        fixture.add(
            primitive_cylinder(0.3, 2.2, 10),
            "PipingSteel",
            loc=(INJECTOR_X + 0.6, math.cos(a) * 3.6, math.sin(a) * 3.6),
            rot=(0, math.pi / 2, 0),
        )
    return fixture


def _fusion_chamber() -> fx.Fixture:
    fixture = fx.Fixture()
    length = CHAMBER_X_FWD - CHAMBER_X_AFT
    center_x = (CHAMBER_X_FWD + CHAMBER_X_AFT) * 0.5
    fixture.add(primitive_cylinder(3.6, length, 28), "ReactorShield", loc=(center_x, 0, 0), rot=(0, math.pi / 2, 0))
    # Cooling jacket ribs.
    for i in range(14):
        x = CHAMBER_X_AFT + 0.6 + i * (length - 1.2) / 13
        fixture.add(primitive_torus(3.75, 0.22, 26, 8), "PipingSteel", loc=(x, 0, 0), rot=(0, math.pi / 2, 0))
    # Confinement coil stack.
    for i in range(6):
        x = CHAMBER_X_AFT + 1.2 + i * (length - 2.4) / 5
        fixture.add(primitive_torus(4.3, 0.45, 28, 10), "CoilCopper", loc=(x, 0, 0), rot=(0, math.pi / 2, 0))
        for j in range(4):
            a = TWO_PI * j / 4
            fixture.add(
                primitive_box(0.5, 0.9, 0.9),
                "EngineMetal",
                loc=(x, math.cos(a) * 4.6, math.sin(a) * 4.6),
                rot=(a, 0, 0),
            )
    # Visible plasma core.
    fixture.add(primitive_cylinder(1.9, length * 0.94, 20), "PlasmaCore", loc=(center_x, 0, 0), rot=(0, math.pi / 2, 0))
    fixture.add(primitive_sphere(2.1, 18, 12), "PlasmaCore", loc=(CHAMBER_X_AFT + 1.0, 0, 0))
    # Shielding drums fore and aft.
    fixture.add(primitive_cone(4.6, 3.6, 2.4, 26), "ReactorShield", loc=(CHAMBER_X_FWD + 1.2, 0, 0), rot=(0, -math.pi / 2, 0))
    fixture.add(primitive_cone(3.6, 3.0, 1.8, 26), "HullDark", loc=(CHAMBER_X_AFT - 0.9, 0, 0), rot=(0, math.pi / 2, 0))
    return fixture


def _magnetic_nozzle() -> fx.Fixture:
    fixture = fx.Fixture()
    length = CHAMBER_X_AFT - NOZZLE_X_AFT
    for i in range(COIL_COUNT):
        t = i / (COIL_COUNT - 1)
        radius = NOZZLE_THROAT_RADIUS + (NOZZLE_EXIT_RADIUS - NOZZLE_THROAT_RADIUS) * (t ** 1.45)
        x = CHAMBER_X_AFT - 1.0 - t * (length - 2.0)
        fixture.add(primitive_torus(radius, 0.55 - 0.18 * t, 30, 10), "CoilCopper", loc=(x, 0, 0), rot=(0, math.pi / 2, 0))
        fixture.add(primitive_torus(radius + 0.5, 0.16, 30, 6), "EngineMetal", loc=(x, 0, 0), rot=(0, math.pi / 2, 0))
        for j in range(6):
            a = TWO_PI * j / 6
            fixture.add(
                primitive_box(0.7, 0.7, 0.9),
                "TrussMetal",
                loc=(x, math.cos(a) * (radius + 0.6), math.sin(a) * (radius + 0.6)),
                rot=(a, 0, 0),
            )
    # Nozzle skin (open bell) between the coils.
    bell = primitive_cone(NOZZLE_THROAT_RADIUS + 0.4, NOZZLE_EXIT_RADIUS + 0.4, length, 32)
    bell.rotate(0, -math.pi / 2, 0).translate(CHAMBER_X_AFT - 1.0 - length * 0.5, 0, 0)
    fixture.add(bell, "HullDark")
    # Cryostat and superconducting feed.
    fixture.add(primitive_tube(1.0, 0.7, length * 0.9, 14), "PipingSteel",
                loc=(CHAMBER_X_AFT - length * 0.45, NOZZLE_EXIT_RADIUS * 0.55, 0), rot=(0, math.pi / 2, 0))
    fixture.add(primitive_tube(1.0, 0.7, length * 0.9, 14), "PipingSteel",
                loc=(CHAMBER_X_AFT - length * 0.45, -NOZZLE_EXIT_RADIUS * 0.55, 0), rot=(0, math.pi / 2, 0))
    # Exhaust plasma disc and struts.
    fixture.add(primitive_cylinder(NOZZLE_EXIT_RADIUS * 0.92, 0.3, 32), "PlasmaCore", loc=(NOZZLE_X_AFT + 0.4, 0, 0), rot=(0, math.pi / 2, 0))
    fixture.add(primitive_torus(NOZZLE_EXIT_RADIUS, 0.7, 32, 10), "EngineMetal", loc=(NOZZLE_X_AFT + 0.2, 0, 0), rot=(0, math.pi / 2, 0))
    for i in range(8):
        a = TWO_PI * i / 8
        fixture.add(
            beam_between(
                (CHAMBER_X_AFT - 2.0, math.cos(a) * 3.4, math.sin(a) * 3.4),
                (NOZZLE_X_AFT + 1.0, math.cos(a) * (NOZZLE_EXIT_RADIUS - 0.6), math.sin(a) * (NOZZLE_EXIT_RADIUS - 0.6)),
                0.5, 0.5,
            ),
            "TrussMetal",
        )
    return fixture


def _turbopumps() -> fx.Fixture:
    fixture = fx.Fixture()
    for side in (-1, 1):
        fixture.extend_at(fx.turbopump(1.3, 3.4), loc=(INJECTOR_X - 4.0, side * 6.2, 2.4), rot=(0, math.pi / 2, 0))
        fixture.extend_at(fx.turbopump(1.0, 2.6), loc=(INJECTOR_X - 4.0, side * 6.2, -2.6), rot=(0, math.pi / 2, 0))
        fixture.extend_at(fx.pipe_run([
            (INJECTOR_X - 6.0, side * 6.2, 2.4),
            (GIMBAL_X + 2.0, side * 7.0, 2.4),
            (GIMBAL_X + 5.0, side * 7.0, 0.0),
        ], radius=0.36))
        fixture.extend_at(fx.pipe_run([
            (INJECTOR_X - 5.4, side * 6.2, -2.6),
            (INJECTOR_X - 1.0, side * 4.6, -1.0),
        ], radius=0.28))
    fixture.add(primitive_box(4.0, 12.0, 4.0), "HullMid", loc=(GIMBAL_X + 5.0, 0, 0))
    return fixture


def _thermal_system() -> fx.Fixture:
    fixture = fx.Fixture()
    for i in range(12):
        x = CHAMBER_X_AFT + 0.8 + i * (CHAMBER_X_FWD - CHAMBER_X_AFT - 1.6) / 11
        for side in (-1, 1):
            fixture.add(
                primitive_box(0.3, 4.6, 2.2),
                "RadiatorHot",
                loc=(x, side * 5.4, 0),
                rot=(side * 0.25, 0, 0),
            )
    fixture.extend_at(fx.pipe_run([
        (CHAMBER_X_AFT + 1.0, 5.0, 3.0),
        (CHAMBER_X_FWD - 1.0, 5.0, 3.0),
        (CHAMBER_X_FWD - 1.0, 5.0, -3.0),
        (CHAMBER_X_AFT + 1.0, 5.0, -3.0),
    ], radius=0.28))
    fixture.extend_at(fx.pipe_run([
        (CHAMBER_X_AFT + 1.0, -5.0, 3.0),
        (CHAMBER_X_FWD - 1.0, -5.0, 3.0),
    ], radius=0.28))
    fixture.add(primitive_cylinder(1.2, 8.0, 14), "PipingSteel", loc=(CHAMBER_X_AFT - 6.0, 0, 6.0), rot=(0, math.pi / 2, 0))
    return fixture


def _control_bay() -> fx.Fixture:
    fixture = fx.Fixture()
    fixture.add(primitive_box(5.0, 6.0, 4.0), "ConsoleBody", loc=(GIMBAL_X + 1.0, -8.0, -6.0))
    for i in range(4):
        fixture.add(primitive_box(0.1, 1.2, 0.7), "ScreenGlow", loc=(GIMBAL_X - 1.6, -8.8 + i * 0.6, -5.6 + i * 0.4))
    fixture.extend_at(fx.console(2.4, 0.9), loc=(GIMBAL_X - 2.0, -8.0, -8.2), rot=(0, -math.pi / 2, 0))
    fixture.extend_at(fx.pipe_run([
        (GIMBAL_X - 1.5, -8.0, -4.0),
        (INJECTOR_X - 2.0, -5.0, -2.0),
        (INJECTOR_X - 2.6, -3.4, 0.0),
    ], radius=0.2))
    fixture.extend_at(fx.server_rack(0.8, 1.0, 2.2), loc=(GIMBAL_X + 1.0, 8.0, -7.0))
    return fixture


def _service_platform() -> fx.Fixture:
    """Walkway, hand-rails and ladder giving the drive a human scale reference."""
    fixture = fx.Fixture()
    platform_y = 7.0
    fixture.add(primitive_box(CHAMBER_X_FWD - NOZZLE_X_AFT + 6.0, 2.4, 0.2), "DeckPlate",
                loc=((CHAMBER_X_FWD + NOZZLE_X_AFT) * 0.5, platform_y, -4.4))
    for i in range(10):
        x = NOZZLE_X_AFT + 2.0 + i * 3.4
        fixture.add(primitive_box(0.2, 2.4, 0.6), "TrussMetal", loc=(x, platform_y, -4.7))
    for i in range(11):
        x = NOZZLE_X_AFT + 2.0 + i * 3.4
        fixture.add(primitive_box(0.12, 0.12, 1.2), "DeckHazard", loc=(x, platform_y + 1.1, -3.8))
    fixture.add(primitive_box(CHAMBER_X_FWD - NOZZLE_X_AFT + 6.0, 0.12, 0.12), "DeckHazard",
                loc=((CHAMBER_X_FWD + NOZZLE_X_AFT) * 0.5, platform_y + 1.1, -3.8))
    fixture.add(primitive_box(CHAMBER_X_FWD - NOZZLE_X_AFT + 6.0, 0.12, 0.12), "DeckHazard",
                loc=((CHAMBER_X_FWD + NOZZLE_X_AFT) * 0.5, platform_y + 1.7, -3.8))
    fixture.extend_at(fx.ladder(4.4), loc=(NOZZLE_X_AFT + 3.0, platform_y + 0.6, -8.6))
    fixture.extend_at(fx.light_strip(6.0), loc=(CHAMBER_X_AFT - 4.0, platform_y, -3.3))
    fixture.extend_at(fx.scale_figure(), loc=(CHAMBER_X_AFT - 3.0, platform_y, -4.3), rot=(0, math.pi / 2, 0))
    return fixture


def _rcs_pod() -> fx.Fixture:
    """Single manoeuvring thruster pod at full detail."""
    fixture = fx.Fixture()
    fixture.add(primitive_box(6.0, 4.4, 4.4), "EngineMetal", loc=(2.0, 0, 0))
    fixture.add(primitive_box(5.4, 3.8, 3.8), "HullDark", loc=(2.4, 0, 0))
    fixture.add(primitive_cone(1.2, 2.4, 4.4, 22), "EngineMetal", loc=(-2.4, 0, 0), rot=(0, -math.pi / 2, 0))
    fixture.add(primitive_torus(2.4, 0.18, 22, 8), "CoilCopper", loc=(-4.4, 0, 0), rot=(0, math.pi / 2, 0))
    fixture.add(primitive_cylinder(2.2, 0.16, 22), "PlasmaCore", loc=(-4.5, 0, 0), rot=(0, math.pi / 2, 0))
    for i in range(3):
        fixture.add(primitive_torus(1.5 + i * 0.1, 0.12, 18, 6), "PipingSteel",
                    loc=(-1.0 - i * 1.0, 0, 0), rot=(0, math.pi / 2, 0))
    fixture.extend_at(fx.turbopump(0.5, 1.2), loc=(3.4, 1.6, -1.6))
    fixture.extend_at(fx.turbopump(0.5, 1.2), loc=(3.4, -1.6, -1.6))
    fixture.extend_at(fx.pipe_run([(4.6, 1.6, -1.6), (5.6, 1.6, 0.0), (5.6, 0.0, 0.0)], radius=0.16))
    fixture.add(primitive_box(1.2, 1.2, 0.8), "ConsoleBody", loc=(4.0, 0, 2.4))
    fixture.add(primitive_box(0.08, 0.8, 0.4), "ScreenAmber", loc=(3.35, 0, 2.4))
    fixture.add(primitive_box(6.4, 0.4, 0.4), "DeckHazard", loc=(2.0, 0, 2.4))
    return fixture


def build_propulsion() -> "object":
    """Return the propulsion study builder."""
    from shipspec.part import Builder

    builder = Builder("propulsion system")
    assemblies = (
        ("PROP_Drive_GimbalMount", "Gimbal Mount & Thrust Yoke", _gimbal_mount(),
         "Two-axis gimbal carrying +/- 6 degrees of thrust vectoring, with four "
         "electro-hydrostatic actuators and a failsafe lock-out ring."),
        ("PROP_Drive_InjectorAssembly", "Injector Assembly & Fuel Manifold", _injector_assembly(),
         "37-element coaxial injector head feeding the D/He-3 manifold at 42 MPa, "
         "with a pilot plasma torch for restart."),
        ("PROP_Drive_FusionChamber", "Fusion Chamber & Confinement Coils", _fusion_chamber(),
         "12 m magnetically confined fusion chamber, six superconducting coil "
         "pairs, borated composite shielding and lithium cooling jacket."),
        ("PROP_Drive_MagneticNozzle", "Magnetic Nozzle & Exhaust Bell", _magnetic_nozzle(),
         f"{COIL_COUNT}-stage magnetic nozzle expanding the plasma from a "
         f"{NOZZLE_THROAT_RADIUS:.1f} m throat to a {NOZZLE_EXIT_RADIUS:.0f} m exit, "
         "cryostat-cooled to 20 K."),
        ("PROP_Drive_Turbopumps", "Turbopumps & Propellant Feed", _turbopumps(),
         "Four turbopumps (two main, two pilot) drawing from the aft tank cluster, "
         "with insulated feed lines and burst discs."),
        ("PROP_Drive_ThermalSystem", "Thermal Management Fins", _thermal_system(),
         "Twelve lithium heat-pipe fin pairs dumping drive waste heat into the "
         "aft radiator loop."),
        ("PROP_Drive_ControlBay", "Drive Control & Electronics Bay", _control_bay(),
         "Redundant drive controllers, ignition sequencer, sensor harness and "
         "the local maintenance console."),
        ("PROP_Drive_ServicePlatform", "Service Platform & Scale Figure", _service_platform(),
         "Maintenance walkway with hand-rails, ladder and a 1.8 m reference "
         "figure for scale."),
        ("PROP_RCS_Pod", "Maneuvering Thruster Pod (detail)", _rcs_pod(),
         "Single reaction-control pod: 60 kN thrust, twin turbopumps, "
         "regeneratively cooled bell and hazard-marked service panel."),
    )
    for name, label, fixture, description in assemblies:
        system = "SYS_PROPULSION"
        builder.multi(name, label, system, fixture.merge_per_material(),
                      deck=4, description=description, tags=("propulsion", "detail"))
    return builder
