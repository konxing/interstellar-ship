"""Shared design parameters for the DSX-01 "Kairos Horizon".

This module is the single source of truth: the headless GLB builder, the
software preview renderer, the Blender build script and the validation suite
all read the same numbers, so the different deliverables can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass

from geometry.glb import Material

# --------------------------------------------------------------------------- #
# Vessel identity
# --------------------------------------------------------------------------- #
VESSEL_NAME = "ISV Kairos Horizon"
VESSEL_REGISTRY = "DSX-01"
VESSEL_CLASS = "Kairos-class deep space exploration vessel"
BUILD_YARD = "Ceres Orbital Yard - Deep Space Exploration Directorate"
CREW_COMPLEMENT = 84
MISSION_PROFILE = "12 year autonomous survey of the outer system and interstellar precursor run"

# --------------------------------------------------------------------------- #
# Global dimensions (metres). +X = bow, +Y = starboard, +Z = up.
# --------------------------------------------------------------------------- #
BOW_TIP_X = 246.0
STERN_TIP_X = -246.0
LENGTH_OVERALL = BOW_TIP_X - STERN_TIP_X          # 492 m
HAB_BLOCK_X_AFT = 28.0
HAB_BLOCK_X_FWD = 168.0
BOW_TAPER_X = 216.0
HULL_BEAM = 64.0
HULL_HEIGHT = 28.0
HULL_CHAMFER = 0.22
SPINE_X_AFT = -150.0
ENGINE_BLOCK_X_AFT = -206.0
NOZZLE_EXIT_X = -246.0

MAX_BEAM = 104.0        # across the centrifuge ring / radiator wings
MAX_HEIGHT = 105.0      # across the centrifuge ring and dorsal sensor mast

# --------------------------------------------------------------------------- #
# Deck stack. Four pressure decks, 7 m each, keel of the habitable block at -14 m.
# --------------------------------------------------------------------------- #
DECK_HEIGHT = 7.0
DECK_PLATE_THICKNESS = 0.45
INTERIOR_CLEAR_HEIGHT = 2.9          # usable head-room inside a compartment
HAB_BLOCK_BOTTOM_Z = -HULL_HEIGHT / 2.0   # -14
HAB_BLOCK_TOP_Z = HULL_HEIGHT / 2.0       # +14


@dataclass(frozen=True)
class DeckSpec:
    """One pressure deck of the habitable block."""

    index: int            # 1 = top (command), 4 = bottom (engineering)
    key: str              # machine readable id, used for file/node names
    name: str             # human readable name
    z_bottom: float
    system: str           # viewer grouping / isolation id
    color: str            # viewer accent colour (hex)
    summary: str
    compartments: tuple[str, ...]


def _deck_z(index: int) -> float:
    """Bottom Z of a deck; index 1 is the topmost deck."""
    return HAB_BLOCK_TOP_Z - DECK_HEIGHT * index


DECKS: tuple[DeckSpec, ...] = (
    DeckSpec(
        index=1,
        key="deck_01_command",
        name="Deck 01 - Command & Navigation",
        z_bottom=_deck_z(1),
        system="SYS_COMMAND",
        color="#5ad1ff",
        summary=(
            "Bridge, navigation and flight control, communications suite, "
            "captain's ready room and the emergency command core."
        ),
        compartments=("Bridge", "Navigation & Flight Control", "Communications Vault", "Captain's Ready Room"),
    ),
    DeckSpec(
        index=2,
        key="deck_02_operations",
        name="Deck 02 - Operations & Science",
        z_bottom=_deck_z(2),
        system="SYS_OPERATIONS",
        color="#7dffb0",
        summary=(
            "Science laboratories, sample vault, mission operations centre, "
            "shuttle hangar with ventral doors and the survey drone racks."
        ),
        compartments=("Science Laboratory", "Mission Operations", "Sample Vault", "Shuttle Hangar"),
    ),
    DeckSpec(
        index=3,
        key="deck_03_habitat",
        name="Deck 03 - Habitat & Life Support",
        z_bottom=_deck_z(3),
        system="SYS_HABITAT",
        color="#ffd166",
        summary=(
            "Crew quarters, galley and wardroom, medical bay, hydroponics, "
            "gymnasium, EVA airlock and the main life support plant."
        ),
        compartments=("Crew Quarters", "Wardroom & Galley", "Medical Bay", "Hydroponics", "EVA Airlock"),
    ),
    DeckSpec(
        index=4,
        key="deck_04_engineering",
        name="Deck 04 - Engineering & Power",
        z_bottom=_deck_z(4),
        system="SYS_ENGINEERING",
        color="#ff8f5a",
        summary=(
            "Main engineering control, fusion reactor shielding drum, power "
            "conditioning, workshops, propellant handling and stores."
        ),
        compartments=("Main Engineering", "Reactor Control", "Machine Shop", "Propellant Handling", "Stores"),
    ),
)

DECK_BY_INDEX = {d.index: d for d in DECKS}
DECK_BY_KEY = {d.key: d for d in DECKS}

# --------------------------------------------------------------------------- #
# Major sub-assemblies (viewer isolation groups)
# --------------------------------------------------------------------------- #
SYSTEMS = {
    "SYS_HULL": "Primary Structure",
    "SYS_COMMAND": "Deck 01 - Command & Navigation",
    "SYS_OPERATIONS": "Deck 02 - Operations & Science",
    "SYS_HABITAT": "Deck 03 - Habitat & Life Support",
    "SYS_ENGINEERING": "Deck 04 - Engineering & Power",
    "SYS_SPINE": "Spine Truss & Propellant",
    "SYS_THERMAL": "Thermal Radiators",
    "SYS_CENTRIFUGE": "Centrifuge Gravity Ring",
    "SYS_PROPULSION": "Propulsion",
    "SYS_SENSORS": "Sensors & Communications",
    "SYS_UTILITY": "Docking, Hangar & Services",
}

# --------------------------------------------------------------------------- #
# Sub-assembly dimensions
# --------------------------------------------------------------------------- #
CENTRIFUGE_X = -58.0
CENTRIFUGE_RADIUS = 46.0
CENTRIFUGE_TUBE = 5.0
CENTRIFUGE_SPOKES = 6
CENTRIFUGE_RPM = 1.6                 # ~0.13 g at 46 m - long duration comfort

RADIATOR_X_AFT = -140.0
RADIATOR_X_FWD = -100.0
RADIATOR_SPAN = 27.0
RADIATOR_HEIGHT = 17.0

TANK_A_X = (-34.0, 4.0)              # forward propellant cluster (2 tanks)
TANK_A_RADIUS = 9.5
TANK_B_X = (-104.0, -68.0)           # aft propellant cluster (3 tanks)
TANK_B_RADIUS = 8.0

MAIN_NOZZLES = (                     # (y, z, bell radius)
    (0.0, 2.0, 13.0),
    (-24.0, -6.0, 11.0),
    (24.0, -6.0, 11.0),
)
MANEUVER_PODS = (                    # (x, y, z)
    (-198.0, -27.0, 15.0),
    (-198.0, 27.0, 15.0),
    (-198.0, -27.0, -17.0),
    (-198.0, 27.0, -17.0),
    (196.0, -21.0, -9.0),
    (196.0, 21.0, -9.0),
)

SENSOR_DISH_X = 194.0
SENSOR_DISH_Z = 17.0
SENSOR_DISH_RADIUS = 15.0

HANGAR_X = (104.0, 158.0)
HANGAR_HALF_WIDTH = 15.0

DOCKING_PORTS = (                    # (x, y, z, axis label)
    (78.0, 0.0, HULL_HEIGHT / 2.0 + 0.2, "dorsal"),
    (146.0, 0.0, -(HULL_HEIGHT / 2.0) - 0.2, "ventral"),
    (30.0, -(HULL_BEAM / 2.0) - 0.2, 0.0, "port"),
    (30.0, (HULL_BEAM / 2.0) + 0.2, 0.0, "starboard"),
)

# --------------------------------------------------------------------------- #
# Performance figures quoted by the design document
# --------------------------------------------------------------------------- #
PERFORMANCE = {
    "dry_mass_t": 41_800,
    "wet_mass_t": 96_500,
    "continuous_thrust_kN": 3_450,
    "sustained_acceleration_g": 0.36,
    "delta_v_km_s": 1_180,
    "electrical_power_MW": 940,
    "cruise_speed_c": 0.012,
    "endurance_years": 12,
}

# --------------------------------------------------------------------------- #
# Material library
# --------------------------------------------------------------------------- #
def _materials() -> dict[str, Material]:
    table = [
        Material("HullLight", (0.68, 0.70, 0.73, 1.0), 0.45, 0.52),
        Material("HullMid", (0.50, 0.53, 0.57, 1.0), 0.50, 0.58),
        Material("HullDark", (0.16, 0.18, 0.21, 1.0), 0.55, 0.62),
        Material("HullAccent", (0.86, 0.36, 0.10, 1.0), 0.30, 0.48),
        Material("DeckPlate", (0.34, 0.36, 0.39, 1.0), 0.55, 0.72),
        Material("TrussMetal", (0.28, 0.30, 0.33, 1.0), 0.78, 0.44),
        Material("TankSkin", (0.74, 0.75, 0.71, 1.0), 0.66, 0.36),
        Material("RadiatorHot", (0.46, 0.30, 0.28, 1.0), 0.82, 0.34, emissive=(0.42, 0.08, 0.03)),
        Material("RadiatorCool", (0.64, 0.66, 0.70, 1.0), 0.86, 0.30),
        Material("WindowGlow", (0.04, 0.07, 0.10, 1.0), 0.10, 0.20, emissive=(0.45, 0.85, 1.00)),
        Material("NavLightRed", (0.10, 0.02, 0.02, 1.0), 0.00, 0.30, emissive=(1.00, 0.12, 0.12)),
        Material("NavLightGreen", (0.02, 0.10, 0.04, 1.0), 0.00, 0.30, emissive=(0.15, 1.00, 0.35)),
        Material("NavLightWhite", (0.12, 0.12, 0.12, 1.0), 0.00, 0.30, emissive=(1.00, 1.00, 1.00)),
        Material("PlasmaCore", (0.62, 0.86, 1.00, 1.0), 0.00, 0.20, emissive=(0.38, 0.72, 1.00)),
        Material("EngineMetal", (0.36, 0.38, 0.41, 1.0), 0.90, 0.32),
        Material("CoilCopper", (0.74, 0.46, 0.24, 1.0), 0.95, 0.28),
        Material("Glass", (0.56, 0.76, 0.86, 0.34), 0.10, 0.06, double_sided=True, alpha_mode="BLEND"),
        Material("InteriorFloor", (0.22, 0.24, 0.27, 1.0), 0.10, 0.88),
        Material("InteriorWall", (0.80, 0.81, 0.82, 1.0), 0.05, 0.90),
        Material("InteriorTrim", (0.30, 0.33, 0.36, 1.0), 0.40, 0.60),
        Material("ConsoleBody", (0.20, 0.22, 0.25, 1.0), 0.50, 0.55),
        Material("ScreenGlow", (0.05, 0.08, 0.11, 1.0), 0.00, 0.25, emissive=(0.24, 0.62, 0.88)),
        Material("ScreenAmber", (0.10, 0.07, 0.03, 1.0), 0.00, 0.28, emissive=(0.90, 0.56, 0.16)),
        Material("FabricBlue", (0.24, 0.32, 0.46, 1.0), 0.00, 0.95),
        Material("FabricTeal", (0.18, 0.38, 0.38, 1.0), 0.00, 0.95),
        Material("HydroGreen", (0.26, 0.56, 0.28, 1.0), 0.00, 0.80, emissive=(0.04, 0.16, 0.05)),
        Material("GrowLight", (0.20, 0.08, 0.18, 1.0), 0.00, 0.30, emissive=(0.95, 0.42, 0.85)),
        Material("MedicalWhite", (0.90, 0.92, 0.93, 1.0), 0.12, 0.55),
        Material("ReactorShield", (0.46, 0.47, 0.44, 1.0), 0.80, 0.50),
        Material("ReactorGlow", (0.30, 0.60, 0.80, 1.0), 0.00, 0.25, emissive=(0.30, 0.75, 1.00)),
        Material("PipingSteel", (0.56, 0.58, 0.61, 1.0), 0.92, 0.34),
        Material("RubberBlack", (0.06, 0.06, 0.07, 1.0), 0.00, 0.95),
        Material("DeckHazard", (0.86, 0.66, 0.12, 1.0), 0.20, 0.70),
        Material("LightStrip", (0.30, 0.30, 0.28, 1.0), 0.00, 0.40, emissive=(1.00, 0.97, 0.88)),
        Material("CeramicTile", (0.86, 0.85, 0.80, 1.0), 0.05, 0.45),
    ]
    return {m.name: m for m in table}


MATERIALS: dict[str, Material] = _materials()
MATERIAL_LIST = list(MATERIALS.values())


def hull_half_width(z: float) -> float:
    """Half beam of the habitable block hull at height ``z`` (chamfered hex)."""
    hh = HULL_HEIGHT / 2.0
    hw = HULL_BEAM / 2.0
    chamfer_z = hh * HULL_CHAMFER
    chamfer_y = hw * HULL_CHAMFER
    az = abs(float(z))
    if az >= hh:
        return hw - chamfer_y
    if az <= hh - chamfer_z:
        return hw
    t = (az - (hh - chamfer_z)) / chamfer_z
    return hw - chamfer_y * t


def hull_stations() -> list[tuple[float, float]]:
    """(x, scale) stations of the pressure hull loft from stern bulkhead to bow tip."""
    return [
        (HAB_BLOCK_X_AFT, 1.00),
        (HAB_BLOCK_X_AFT + 18.0, 1.00),
        (96.0, 1.00),
        (HAB_BLOCK_X_FWD, 0.98),
        (188.0, 0.74),
        (BOW_TAPER_X, 0.50),
        (232.0, 0.26),
        (BOW_TIP_X, 0.10),
    ]
