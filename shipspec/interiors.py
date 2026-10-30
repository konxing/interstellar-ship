"""Standalone interior compartment tour model (1:1 human scale).

Ten representative compartments laid out in a row and linked by a service
corridor, so the viewer can walk the ship's interior without loading the
492 m exterior model. Furniture layouts are shared with the per-deck models
through :func:`shipspec.decks.fit_compartment`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from geometry.mesh import primitive_box, primitive_cylinder, primitive_torus
from shipspec import fixtures as fx
from shipspec.constants import DECK_BY_INDEX, INTERIOR_CLEAR_HEIGHT
from shipspec.decks import fit_compartment
from shipspec.part import Builder

GAP = 7.0
CORRIDOR_OFFSET = 4.0
CORRIDOR_WIDTH = 3.0
CORRIDOR_HEIGHT = 2.5


@dataclass(frozen=True)
class Compartment:
    room_id: str
    label: str
    kind: str
    length: float
    width: float
    height: float
    deck: int
    description: str
    windows: bool = True


COMPARTMENTS: tuple[Compartment, ...] = (
    Compartment(
        "Bridge", "Bridge & Command Centre", "bridge", 24.0, 17.0, 3.4, 1,
        "Primary flight deck: five helm/console positions, two command chairs, "
        "tactical holo-table and the aft mission display wall.",
    ),
    Compartment(
        "Navigation", "Navigation & Flight Control", "nav", 20.0, 13.0, INTERIOR_CLEAR_HEIGHT, 1,
        "Eight navigation workstations, the star-chart holo-table and redundant "
        "flight computers on shock-isolated racks.",
    ),
    Compartment(
        "CommsVault", "Communications Vault", "comms", 18.0, 12.0, INTERIOR_CLEAR_HEIGHT, 1,
        "Laser/RF transceiver racks, the 40 kW transmitter coil and the "
        "encrypted data core.",
    ),
    Compartment(
        "ScienceLab", "Science Laboratory", "lab", 26.0, 13.0, INTERIOR_CLEAR_HEIGHT, 2,
        "Wet and dry benches, sample containment glove-box, spectroscopy rack "
        "and the geology analysis bay.",
    ),
    Compartment(
        "MissionOps", "Mission Operations Centre", "ops", 20.0, 15.0, INTERIOR_CLEAR_HEIGHT, 2,
        "Nine operator positions, surface operations wall display and the "
        "survey drone control bench.",
    ),
    Compartment(
        "Hangar", "Shuttle Hangar", "hangar", 40.0, 26.0, 9.0, 2,
        "Double-height bay for two survey shuttles, overhead crane rail, "
        "drone charging racks and ventral doors.",
    ),
    Compartment(
        "Quarters", "Crew Quarters", "quarters", 24.0, 13.0, INTERIOR_CLEAR_HEIGHT, 3,
        "Twelve berths in two tiers, personal storage, exercise equipment and "
        "the inboard EVA airlock.",
    ),
    Compartment(
        "Wardroom", "Wardroom & Galley", "wardroom", 18.0, 13.0, INTERIOR_CLEAR_HEIGHT, 3,
        "Galley counter with food printer, three mess tables, wardroom display "
        "and the medical cabinet station.",
    ),
    Compartment(
        "Medbay", "Medical Bay", "medbay", 18.0, 13.0, INTERIOR_CLEAR_HEIGHT, 3,
        "Three auto-doc berths, diagnostic cabinet, isolation pod and the "
        "sickbay console.",
    ),
    Compartment(
        "Hydroponics", "Hydroponics Bay", "hydro", 26.0, 13.0, INTERIOR_CLEAR_HEIGHT, 3,
        "Five growth racks under magenta LED arrays, nutrient loop piping and "
        "the atmosphere scrubber interface.",
    ),
    Compartment(
        "MainEngineering", "Main Engineering", "engineering", 26.0, 17.0, 5.2, 4,
        "Reactor control drum, four turbopumps, drive console row and the "
        "overhead coolant raceway.",
        windows=False,
    ),
    Compartment(
        "MachineShop", "Machine Shop & Stores", "shop", 22.0, 13.0, INTERIOR_CLEAR_HEIGHT, 4,
        "Three work benches, spare-parts racks, containerised stores and the "
        "heavy maintenance hoist.",
        windows=False,
    ),
)


def build_interiors() -> Builder:
    """Build the interior compartment tour."""
    builder = Builder("interior compartments")
    cursor = 0.0
    spans: list[tuple[float, float, Compartment]] = []

    for room in COMPARTMENTS:
        x0 = cursor
        x1 = cursor + room.length
        spans.append((x0, x1, room))
        cursor = x1 + GAP

    total_length = cursor - GAP
    corridor_y = -max(room.width for room in COMPARTMENTS) * 0.5 - CORRIDOR_OFFSET - CORRIDOR_WIDTH * 0.5

    # Service corridor linking every compartment.
    corridor = fx.Fixture()
    corridor.add(
        primitive_box(total_length, CORRIDOR_WIDTH, 0.2),
        "DeckPlate",
        loc=(total_length * 0.5, corridor_y, -0.1),
    )
    corridor.add(
        primitive_box(total_length, CORRIDOR_WIDTH, 0.16),
        "InteriorWall",
        loc=(total_length * 0.5, corridor_y, CORRIDOR_HEIGHT),
    )
    for side in (-1, 1):
        corridor.add(
            primitive_box(total_length, 0.16, CORRIDOR_HEIGHT),
            "InteriorWall",
            loc=(total_length * 0.5, corridor_y + side * CORRIDOR_WIDTH * 0.5, CORRIDOR_HEIGHT * 0.5),
        )
        corridor.add(
            primitive_box(total_length, 0.06, 0.24),
            "LightStrip",
            loc=(total_length * 0.5, corridor_y + side * CORRIDOR_WIDTH * 0.42, CORRIDOR_HEIGHT - 0.1),
        )
    bays = max(6, int(total_length / 8))
    for i in range(bays + 1):
        x = total_length * i / bays
        corridor.add(primitive_box(0.2, CORRIDOR_WIDTH, CORRIDOR_HEIGHT), "InteriorTrim",
                     loc=(x, corridor_y, CORRIDOR_HEIGHT * 0.5))
        corridor.add(primitive_box(0.14, CORRIDOR_WIDTH * 0.9, 0.14), "PipingSteel",
                     loc=(x + 0.6, corridor_y, CORRIDOR_HEIGHT - 0.35))
    for x0, x1, room in spans:
        spur_x = (x0 + x1) * 0.5
        spur_length = abs(corridor_y) - room.width * 0.5
        spur_y = (corridor_y - room.width * 0.5) * 0.5
        corridor.add(primitive_box(CORRIDOR_WIDTH, spur_length, 0.2), "DeckPlate",
                     loc=(spur_x, spur_y, -0.1))
        corridor.add(primitive_box(CORRIDOR_WIDTH, spur_length, 0.16), "InteriorWall",
                     loc=(spur_x, spur_y, CORRIDOR_HEIGHT))
        for side in (-1, 1):
            corridor.add(primitive_box(0.16, spur_length, CORRIDOR_HEIGHT), "InteriorWall",
                         loc=(spur_x + side * CORRIDOR_WIDTH * 0.5, spur_y, CORRIDOR_HEIGHT * 0.5))
        corridor.extend_at(fx.door(1.3, 2.2), loc=(spur_x, -room.width * 0.5 - 0.2, 0.0), rot=(0, math.pi / 2, 0))
        corridor.add(primitive_box(0.4, 0.4, 0.06), "ScreenAmber",
                     loc=(spur_x + 1.2, -room.width * 0.5 - 0.35, 1.4))
    builder.multi(
        "INT_ServiceCorridor",
        "Service Corridor & Access Spurs",
        "SYS_HABITAT",
        corridor.merge_per_material(),
        description=(
            f"{total_length:.0f} m pressurised service corridor with access spurs, "
            "cable raceways and compartment status panels."
        ),
        tags=("interior", "corridor"),
    )

    for x0, x1, room in spans:
        deck = DECK_BY_INDEX[room.deck]
        fixture = fit_compartment(
            room.kind, x0, x1, room.width, 0.0, room.height, windows=room.windows
        )
        builder.multi(
            f"INT_{room.room_id}",
            room.label,
            deck.system,
            fixture.merge_per_material(),
            deck=room.deck,
            description=room.description,
            tags=("interior", room.kind, deck.key),
        )

    # Dedicated EVA airlock module (cylindrical, not a rectangular room).
    airlock_x = total_length + GAP
    airlock = fx.Fixture()
    airlock.add(primitive_box(14.0, 10.0, 0.2), "DeckPlate", loc=(airlock_x + 7.0, 0, -0.1))
    airlock.add(primitive_box(14.0, 10.0, 0.16), "InteriorWall", loc=(airlock_x + 7.0, 0, 3.0))
    for side in (-1, 1):
        airlock.add(primitive_box(14.0, 0.18, 3.0), "InteriorWall", loc=(airlock_x + 7.0, side * 5.0, 1.5))
    airlock.extend_at(fx.airlock_chamber(2.2, 6.0), loc=(airlock_x + 7.0, 0, 2.2))
    airlock.add(primitive_cylinder(2.4, 0.3, 20), "DeckHazard", loc=(airlock_x + 2.6, 0, 0.05))
    airlock.add(primitive_box(0.6, 3.0, 0.06), "ScreenAmber", loc=(airlock_x + 12.0, -4.8, 1.6))
    airlock.extend_at(fx.storage_rack(3.0, 0.8, 2.4), loc=(airlock_x + 12.2, 3.6, 0.0), rot=(0, math.pi / 2, 0))
    for i in range(4):
        airlock.add(primitive_torus(2.6, 0.14, 20, 8), "InteriorTrim",
                    loc=(airlock_x + 4.0 + i * 2.0, 0, 2.2), rot=(0, math.pi / 2, 0))
    builder.multi(
        "INT_EVAAirlock",
        "EVA Airlock & Suit Room",
        "SYS_HABITAT",
        airlock.merge_per_material(),
        deck=3,
        description=(
            "Two-chamber EVA airlock with six suit hard-points, suit purge "
            "controls and the dust mitigation shower."
        ),
        tags=("interior", "airlock", "eva"),
    )

    return builder

