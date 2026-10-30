"""Scene assembly: turn the procedural builders into named, exportable scenes.

Every asset shares one coordinate frame - the ship frame, where ``+X`` is the
bow, ``+Y`` starboard and ``+Z`` up, with the origin at midships on the
centreline. Isolated studies (a single deck, the interior layout, the drive)
therefore keep their true position inside the vessel, which lets the Three.js
viewer frame, stack and explode them consistently. The glTF writer performs
the Z-up to Y-up conversion on export.

Each scene carries a rich ``extras`` block (asset id, category, systems, deck
metadata, performance figures) that the viewer reads to drive its info panel
and asset switcher, so the models are self-describing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from shipspec import constants as C
from shipspec import decks as decks_mod
from shipspec import hull as hull_mod
from shipspec import interiors as interiors_mod
from shipspec import propulsion as propulsion_mod
from geometry.glb import SceneGraph

GENERATOR = "DSX-01 Kairos Horizon procedural modeller"


# --------------------------------------------------------------------------- #
# Shared metadata
# --------------------------------------------------------------------------- #
def _vessel_block() -> dict[str, Any]:
    return {
        "project": "Deep Space Exploration Ship - 3D Modelling Workbench",
        "vessel": C.VESSEL_NAME,
        "registry": C.VESSEL_REGISTRY,
        "vesselClass": C.VESSEL_CLASS,
        "buildYard": C.BUILD_YARD,
        "crewComplement": C.CREW_COMPLEMENT,
        "missionProfile": C.MISSION_PROFILE,
        "units": "metre",
        "shipFrame": {"forward": "+X", "starboard": "+Y", "up": "+Z", "origin": "midships centreline"},
        "exportFrame": "glTF Y-up (converted from ship Z-up on export)",
        "systems": dict(C.SYSTEMS),
        "dimensions": {
            "lengthOverall": C.LENGTH_OVERALL,
            "maxBeam": C.MAX_BEAM,
            "maxHeight": C.MAX_HEIGHT,
            "hullBeam": C.HULL_BEAM,
            "hullHeight": C.HULL_HEIGHT,
            "habBlockXAft": C.HAB_BLOCK_X_AFT,
            "habBlockXFwd": C.HAB_BLOCK_X_FWD,
        },
    }


def _deck_block(deck: C.DeckSpec) -> dict[str, Any]:
    return {
        "index": deck.index,
        "key": deck.key,
        "name": deck.name,
        "system": deck.system,
        "color": deck.color,
        "zBottom": deck.z_bottom,
        "deckHeight": C.DECK_HEIGHT,
        "interiorClearHeight": C.INTERIOR_CLEAR_HEIGHT,
        "summary": deck.summary,
        "compartments": list(deck.compartments),
    }


# --------------------------------------------------------------------------- #
# Asset builders
# --------------------------------------------------------------------------- #
def build_full_ship() -> SceneGraph:
    builder = hull_mod.build_exterior()
    extras = _vessel_block()
    extras.update(
        {
            "assetId": "dsx-01_full_ship",
            "category": "full-ship",
            "label": f"{C.VESSEL_REGISTRY} {C.VESSEL_NAME} - complete exterior",
            "performance": dict(C.PERFORMANCE),
            "decks": [_deck_block(d) for d in C.DECKS],
        }
    )
    return builder.scene(
        name=f"{C.VESSEL_REGISTRY} {C.VESSEL_NAME}",
        materials=C.MATERIAL_LIST,
        extras=extras,
        group_by=lambda part: part.system,
    )


def build_deck_scene(deck: C.DeckSpec) -> SceneGraph:
    builder = decks_mod.build_deck(deck)
    extras = _vessel_block()
    extras.update(
        {
            "assetId": f"dsx-02_{deck.key}",
            "category": "deck",
            "label": deck.name,
            "deck": _deck_block(deck),
        }
    )
    return builder.scene(
        name=deck.name,
        materials=C.MATERIAL_LIST,
        extras=extras,
        group_by=lambda part: part.system,
    )


def build_interior_scene() -> SceneGraph:
    builder = interiors_mod.build_interiors()
    extras = _vessel_block()
    extras.update(
        {
            "assetId": "dsx-03_interior_compartments",
            "category": "interior",
            "label": "Interior compartment & systems layout",
            "summary": (
                "Walk-through study of the primary crew compartments arranged "
                "along the habitable block, with the service corridor, EVA "
                "airlock and fitted interiors for every room."
            ),
            "compartments": [c.room_id for c in interiors_mod.COMPARTMENTS],
        }
    )
    return builder.scene(
        name="Interior Compartments",
        materials=C.MATERIAL_LIST,
        extras=extras,
        group_by=lambda part: part.system,
    )


def build_propulsion_scene() -> SceneGraph:
    builder = propulsion_mod.build_propulsion()
    extras = _vessel_block()
    extras.update(
        {
            "assetId": "dsx-04_propulsion_system",
            "category": "propulsion",
            "label": "Fusion torch drive & propulsion system",
            "summary": (
                "Detailed single-engine study of the main fusion torch drive: "
                "gimbal mount, injector head, confinement chamber, magnetic "
                "nozzle, turbopumps, thermal loop, control bay and service "
                "platform, plus a reaction-control thruster pod."
            ),
            "performance": dict(C.PERFORMANCE),
        }
    )
    return builder.scene(
        name="Propulsion System",
        materials=C.MATERIAL_LIST,
        extras=extras,
        group_by=lambda part: part.system,
    )


# --------------------------------------------------------------------------- #
# Asset registry (shared by the exporter, tests and viewer manifest)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Asset:
    asset_id: str
    filename: str
    category: str
    label: str
    build: Callable[[], SceneGraph]
    deck_key: str | None = None


ASSETS: tuple[Asset, ...] = (
    Asset(
        asset_id="dsx-01_full_ship",
        filename="dsx-01_full_ship.glb",
        category="full-ship",
        label=f"{C.VESSEL_REGISTRY} {C.VESSEL_NAME} - complete exterior",
        build=build_full_ship,
    ),
    *(
        Asset(
            asset_id=f"dsx-02_{deck.key}",
            filename=f"dsx-02_{deck.key}.glb",
            category="deck",
            label=deck.name,
            build=(lambda d=deck: build_deck_scene(d)),
            deck_key=deck.key,
        )
        for deck in C.DECKS
    ),
    Asset(
        asset_id="dsx-03_interior_compartments",
        filename="dsx-03_interior_compartments.glb",
        category="interior",
        label="Interior compartment & systems layout",
        build=build_interior_scene,
    ),
    Asset(
        asset_id="dsx-04_propulsion_system",
        filename="dsx-04_propulsion_system.glb",
        category="propulsion",
        label="Fusion torch drive & propulsion system",
        build=build_propulsion_scene,
    ),
)

ASSET_BY_ID = {a.asset_id: a for a in ASSETS}
