"""Design specification and procedural builders for the DSX-01 Kairos Horizon.

The package is deliberately free of third-party dependencies beyond NumPy so
the same source of truth feeds the glTF exporter, the Blender bridge, the
software preview renderer and the validation suite without drifting.

Public entry points
-------------------
``assembly.build_full_ship``      -> complete vessel scene graph
``assembly.build_deck``           -> one isolated deck-level model
``assembly.build_interior``       -> interior compartment study
``assembly.build_propulsion``     -> fusion torch drive study
``constants``                     -> frozen dimensions, decks, materials
"""

from __future__ import annotations

from shipspec import assembly, constants, decks, fixtures, hull, interiors, part, propulsion

__all__ = [
    "assembly",
    "constants",
    "decks",
    "fixtures",
    "hull",
    "interiors",
    "part",
    "propulsion",
]
