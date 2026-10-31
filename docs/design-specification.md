# DSX-01 *ISV Kairos Horizon* — Design Specification

Single source of truth for the vessel's dimensions, deck stack, systems and
material library. Every number here is mirrored by a constant in
`shipspec/constants.py`; the builders, the glTF exporter, the Blender bridge,
the preview renderer and the test suite all read from that module, so the
documentation cannot drift from the models.

## 1. Identity

| Field | Value |
|---|---|
| Name | ISV Kairos Horizon |
| Registry | DSX-01 |
| Class | Kairos-class deep space exploration vessel |
| Build yard | Ceres Orbital Yard — Deep Space Exploration Directorate |
| Crew complement | 84 |
| Mission profile | 12-year autonomous survey of the outer system and interstellar precursor run |

## 2. Coordinate frame

Ship frame is **Z-up**: `+X` bow, `+Y` starboard, `+Z` up, origin at midships on
the centreline. glTF and the web viewer use Y-up; the exporter applies the
conversion `[[1,0,0],[0,0,1],[0,-1,0]]` (new_x = x, new_y = z, new_z = −y).
Blender is Z-up natively and therefore matches the ship frame directly.

## 3. Principal dimensions (metres)

| Quantity | Value | Notes |
|---|---|---|
| Length overall | 492.0 | bow tip +246 to stern/nozzle exit −246 |
| Max beam | 104.0 | across centrifuge ring / radiator wings |
| Max height | 105.0 | across centrifuge ring and dorsal sensor mast |
| Hull beam | 64.0 | habitable block, waterline-equivalent plane |
| Hull height | 28.0 | habitable block vertical extent |
| Hull chamfer | 0.22 | fraction of half-beam cut at the deck edges |
| Habitable block | X 28 … 168 | four-deck pressure volume |
| Bow taper start | X 216 | forward of this the hull narrows to the aperture |
| Spine aft limit | X −150 | lattice truss begins |
| Engine block aft | X −206 | thrust structure |
| Nozzle exit plane | X −246 | magnetic nozzle exit |

## 4. Deck stack

Four decks, each `DECK_HEIGHT = 7.0 m` with `DECK_PLATE_THICKNESS = 0.45 m` and
`INTERIOR_CLEAR_HEIGHT = 2.9 m`. The stack is centred on the hull: the habitable
block runs from `HAB_BLOCK_BOTTOM_Z = −14` to `HAB_BLOCK_TOP_Z = +14`.

| # | Key | Name | System | Accent | Primary compartments |
|---|---|---|---|---|---|
| 1 | deck_01_command | Command & Navigation | SYS_COMMAND | #5ad1ff | Bridge, Navigation & Flight Control, Communications Vault, Captain's Ready Room |
| 2 | deck_02_operations | Operations & Science | SYS_OPERATIONS | #7dffb0 | Science Laboratory, Mission Operations, Sample Vault, Shuttle Hangar |
| 3 | deck_03_habitat | Habitat & Life Support | SYS_HABITAT | #ffd166 | Crew Quarters, Wardroom & Galley, Medical Bay, Hydroponics, EVA Airlock |
| 4 | deck_04_engineering | Engineering & Power | SYS_ENGINEERING | #ff8f5a | Main Engineering, Reactor Control, Machine Shop, Propellant Handling, Stores |

## 5. Systems (isolation groups)

Eleven top-level groups drive system isolation in both the glTF hierarchy and
the web viewer:

`SYS_HULL` Primary Structure · `SYS_COMMAND` · `SYS_OPERATIONS` · `SYS_HABITAT` ·
`SYS_ENGINEERING` · `SYS_SPINE` Spine Truss & Propellant · `SYS_THERMAL`
Thermal Radiators · `SYS_CENTRIFUGE` Centrifuge Gravity Ring ·
`SYS_PROPULSION` · `SYS_SENSORS` Sensors & Communications · `SYS_UTILITY`
Docking, Hangar & Services.

## 6. Major sub-assemblies

| Sub-assembly | Parameters |
|---|---|
| Centrifuge gravity ring | centre X −58, ring radius 46 m, tube radius 5 m, 6 spokes, 1.6 rpm; 48 lit windows + 12 accent bands |
| Thermal radiators | 4 wings, X −140…−100, span 27 m, height 17 m; hot/cold faces; auxiliary louvres |
| Propellant tanks | 5 tanks on the spine: pair A at X −34/+4 (R 9.5), trio B at X −104/−86/−68 (R 8); feed pipe runs |
| Main torch nozzles | 3 (centre R 13 at Y 0; outboard R 11 at Y ±24); 7 coil stages + plasma disc each |
| Maneuvering thrusters | 6 pods distributed fore/aft, dorsal/ventral |
| High-gain antenna | 15 m parabolic dish at X 194, Z 17; 4 secondary dishes + interferometer booms |
| Shuttle hangar | X 104…158, half-width 15 m, ventral two-leaf doors |
| Docking ports | 4 collars: dorsal, ventral, port, starboard |
| Navigation lights | 11 (red/green/white) per collision-regulation placement |

## 7. Performance (quoted)

| Quantity | Value |
|---|---|
| Dry mass | 41 800 t |
| Wet mass | 96 500 t |
| Continuous thrust | 3 450 kN |
| Sustained acceleration | 0.36 g |
| Delta-v | 1 180 km/s |
| Electrical power | 940 MW |
| Cruise speed | 0.012 c |
| Endurance | 12 years |

## 8. Material library

35 PBR metallic-roughness materials (`shipspec/constants.py::MATERIALS`), each
with base colour, metallic, roughness and optional emissive term; `Glass` uses
alpha-blend + double-sided. Emissive families cover window glow, navigation
lights, plasma core, reactor glow, screens, grow lights and light strips. The
Blender bridge maps these onto Principled BSDF nodes; the glTF writer emits
them as `pbrMetallicRoughness` + `emissiveFactor` + `alphaMode`.

## 9. Asset inventory

Seven glTF-binary assets (353 864 triangles, ~11.5 MB total) plus the Blender
master original:

| Asset | Triangles | Content |
|---|---|---|
| dsx-01_full_ship | 133 444 | complete exterior, all 11 systems |
| dsx-02_deck_01_command | 16 984 | deck 1 cutaway + fitted rooms |
| dsx-02_deck_02_operations | 14 508 | deck 2 cutaway + fitted rooms |
| dsx-02_deck_03_habitat | 39 232 | deck 3 cutaway + fitted rooms |
| dsx-02_deck_04_engineering | 21 144 | deck 4 cutaway + fitted rooms |
| dsx-03_interior_compartments | 70 252 | 12 compartments + service corridor + EVA airlock |
| dsx-04_propulsion_system | 58 300 | fusion torch drive study + RCS pod |

See `docs/asset-contract.md` for the node/metadata contract and
`reports/model-validation.json` for measured bounds and counts.
