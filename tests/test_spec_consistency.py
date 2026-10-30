"""Invariants of the design specification and builder/spec coherence."""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from shipspec import constants as C  # noqa: E402
from shipspec import decks as decks_mod  # noqa: E402
from shipspec import hull as hull_mod  # noqa: E402
from shipspec import interiors as interiors_mod  # noqa: E402
from shipspec import propulsion as propulsion_mod  # noqa: E402


def _all_builders():
    yield "exterior", hull_mod.build_exterior()
    for deck in C.DECKS:
        yield deck.key, decks_mod.build_deck(deck)
    yield "interiors", interiors_mod.build_interiors()
    yield "propulsion", propulsion_mod.build_propulsion()


def test_deck_stack_is_contiguous_and_inside_hull():
    bottoms = [d.z_bottom for d in C.DECKS]
    assert bottoms == sorted(bottoms, reverse=True) or bottoms == sorted(bottoms)
    for i in range(len(C.DECKS) - 1):
        gap = abs(C.DECKS[i].z_bottom - C.DECKS[i + 1].z_bottom)
        assert abs(gap - C.DECK_HEIGHT) < 1e-6, (C.DECKS[i].key, gap)
    top = max(d.z_bottom for d in C.DECKS) + C.DECK_HEIGHT
    bottom = min(d.z_bottom for d in C.DECKS)
    assert top <= C.HULL_HEIGHT / 2 + 1e-6, top
    assert bottom >= -C.HULL_HEIGHT / 2 - 1e-6, bottom


def test_deck_indices_and_keys_unique():
    indices = [d.index for d in C.DECKS]
    keys = [d.key for d in C.DECKS]
    assert len(set(indices)) == len(indices) == 4
    assert len(set(keys)) == len(keys) == 4
    assert set(C.DECK_BY_INDEX) == set(indices)
    assert set(C.DECK_BY_KEY) == set(keys)


def test_every_deck_system_is_known():
    for deck in C.DECKS:
        assert deck.system in C.SYSTEMS, deck.system


def test_builders_only_use_known_materials():
    for label, builder in _all_builders():
        for part in builder.parts:
            for mat in part.material_names:
                assert mat in C.MATERIALS, f"{label}/{part.name} uses unknown material {mat}"


def test_builders_only_use_known_systems():
    for label, builder in _all_builders():
        for part in builder.parts:
            assert part.system in C.SYSTEMS, f"{label}/{part.name} uses unknown system {part.system}"


def test_builders_produce_nonempty_parts():
    for label, builder in _all_builders():
        assert builder.parts, label
        for part in builder.parts:
            assert not part.is_empty(), f"{label}/{part.name} is empty"
            assert part.triangle_count > 0


def test_part_extras_wellformed():
    for label, builder in _all_builders():
        for part in builder.parts:
            extras = part.extras()
            assert extras["partId"] == part.name
            assert extras["label"]
            assert extras["system"] in C.SYSTEMS
            assert isinstance(extras["materials"], list) and extras["materials"]


def test_hull_half_width_monotonic_and_bounded():
    zs = [0.0, C.HULL_HEIGHT * 0.25, C.HULL_HEIGHT * 0.49]
    widths = [C.hull_half_width(z) for z in zs]
    assert widths[0] >= widths[1] >= widths[2] > 0
    assert widths[0] <= C.HULL_BEAM / 2 + 1e-6


def test_performance_figures_positive():
    for key, value in C.PERFORMANCE.items():
        assert value > 0, key


def test_material_library_complete():
    assert len(C.MATERIALS) >= 30
    assert set(C.MATERIALS) == {m.name for m in C.MATERIAL_LIST}
    for mat in C.MATERIAL_LIST:
        assert len(mat.base_color) == 4
        assert 0.0 <= mat.metallic <= 1.0
        assert 0.0 <= mat.roughness <= 1.0
