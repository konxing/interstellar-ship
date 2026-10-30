"""Dependency-free 3D geometry kernel for the DSX-01 Kairos Horizon project.

The same mesh data structures are consumed by:
  * ``scripts/build_glb.py``  -> glTF 2.0 binary (.glb) assets
  * ``scripts/render_preview.py`` -> software rasterised preview PNGs
  * ``blender/build_ship.py`` -> native Blender (.blend) scene

Units are metres, Y is starboard, Z is up, +X points towards the bow.
"""

from .mesh import Mesh, primitive_box, primitive_cylinder, primitive_cone
from .mesh import primitive_sphere, primitive_torus, primitive_tube, primitive_prism
from .mesh import primitive_loft, beam_between, merge, transform_mesh
from .glb import write_glb, Material, SceneGraph, GroupNode, MeshNode

__all__ = [
    "Mesh",
    "primitive_box",
    "primitive_cylinder",
    "primitive_cone",
    "primitive_sphere",
    "primitive_torus",
    "primitive_tube",
    "primitive_prism",
    "primitive_loft",
    "beam_between",
    "merge",
    "transform_mesh",
    "write_glb",
    "Material",
    "SceneGraph",
    "GroupNode",
    "MeshNode",
]
