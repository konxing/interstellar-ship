"""Mesh data structure and procedural primitive builders.

Everything here is pure Python + NumPy so it runs identically inside the CI
sandbox, on a developer laptop and (through the Blender bridge) inside
Blender's bundled Python interpreter.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np

TWO_PI = math.pi * 2.0


# --------------------------------------------------------------------------- #
# Core mesh container
# --------------------------------------------------------------------------- #
class Mesh:
    """Indexed triangle mesh with per-vertex normals."""

    __slots__ = ("vertices", "normals", "indices", "name")

    def __init__(
        self,
        vertices: Sequence[Sequence[float]] | np.ndarray | None = None,
        normals: Sequence[Sequence[float]] | np.ndarray | None = None,
        indices: Sequence[Sequence[int]] | np.ndarray | None = None,
        name: str = "",
    ) -> None:
        self.name = name
        self.vertices = _as_float_array(vertices)
        self.indices = _as_int_array(indices)
        if normals is None:
            self.normals = np.zeros_like(self.vertices)
            self.recompute_normals()
        else:
            self.normals = _as_float_array(normals)

    # -- introspection ---------------------------------------------------- #
    @property
    def triangle_count(self) -> int:
        return int(self.indices.shape[0])

    @property
    def vertex_count(self) -> int:
        return int(self.vertices.shape[0])

    def is_empty(self) -> bool:
        return self.vertex_count == 0

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        if self.is_empty():
            z = np.zeros(3, dtype=np.float32)
            return z, z.copy()
        return self.vertices.min(axis=0), self.vertices.max(axis=0)

    def center(self) -> np.ndarray:
        lo, hi = self.bounds()
        return (lo + hi) * 0.5

    # -- mutation --------------------------------------------------------- #
    def transform(self, matrix: np.ndarray) -> "Mesh":
        matrix = np.asarray(matrix, dtype=np.float64)
        if self.is_empty():
            return self
        rot = matrix[:3, :3]
        trans = matrix[:3, 3]
        self.vertices = (self.vertices.astype(np.float64) @ rot.T + trans).astype(np.float32)
        if np.allclose(rot @ rot.T, np.eye(3), atol=1e-6):
            normal_matrix = rot
        else:
            normal_matrix = np.linalg.inv(rot).T
        norms = self.normals.astype(np.float64) @ normal_matrix.T
        lengths = np.linalg.norm(norms, axis=1, keepdims=True)
        lengths[lengths == 0] = 1.0
        self.normals = (norms / lengths).astype(np.float32)
        return self

    def translate(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> "Mesh":
        if not self.is_empty():
            self.vertices = self.vertices + np.array([x, y, z], dtype=np.float32)
        return self

    def scale(self, sx: float, sy: float | None = None, sz: float | None = None) -> "Mesh":
        sy = sx if sy is None else sy
        sz = sx if sz is None else sz
        return self.transform(np.diag([sx, sy, sz, 1.0]))

    def rotate(self, rx: float = 0.0, ry: float = 0.0, rz: float = 0.0, order: str = "XYZ") -> "Mesh":
        return self.transform(euler_matrix(rx, ry, rz, order))

    def mirror(self, axis: str = "y") -> "Mesh":
        idx = {"x": 0, "y": 1, "z": 2}[axis]
        scale = np.ones(3)
        scale[idx] = -1.0
        self.transform(np.diag([scale[0], scale[1], scale[2], 1.0]))
        # Mirroring flips winding order.
        self.indices = self.indices[:, ::-1].copy()
        return self

    def recompute_normals(self) -> "Mesh":
        """Flat (facet) normals expanded per vertex - safe default."""
        normals = np.zeros_like(self.vertices)
        if self.indices.shape[0] == 0:
            return self
        v = self.vertices.astype(np.float64)
        tri = v[self.indices]
        face_n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        lengths = np.linalg.norm(face_n, axis=1, keepdims=True)
        lengths[lengths == 0] = 1.0
        face_n /= lengths
        for corner in range(3):
            np.add.at(normals, self.indices[:, corner], face_n)
        nlen = np.linalg.norm(normals, axis=1, keepdims=True)
        nlen[nlen == 0] = 1.0
        self.normals = (normals / nlen).astype(np.float32)
        return self

    def copy(self) -> "Mesh":
        return Mesh(self.vertices.copy(), self.normals.copy(), self.indices.copy(), self.name)


def _as_float_array(data) -> np.ndarray:
    if data is None:
        return np.zeros((0, 3), dtype=np.float32)
    arr = np.asarray(data, dtype=np.float32)
    return arr.reshape(-1, 3)


def _as_int_array(data) -> np.ndarray:
    if data is None:
        return np.zeros((0, 3), dtype=np.uint32)
    arr = np.asarray(data, dtype=np.uint32)
    return arr.reshape(-1, 3)


# --------------------------------------------------------------------------- #
# Transform helpers
# --------------------------------------------------------------------------- #
def translation_matrix(x: float, y: float, z: float) -> np.ndarray:
    m = np.eye(4, dtype=np.float64)
    m[0, 3], m[1, 3], m[2, 3] = x, y, z
    return m


def scale_matrix(sx: float, sy: float, sz: float) -> np.ndarray:
    return np.diag([sx, sy, sz, 1.0]).astype(np.float64)


def euler_matrix(rx: float = 0.0, ry: float = 0.0, rz: float = 0.0, order: str = "XYZ") -> np.ndarray:
    """Rotation matrix from euler angles in radians (intrinsic, given order)."""
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    rot_x = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=np.float64)
    rot_y = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float64)
    rot_z = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], dtype=np.float64)
    table = {"X": rot_x, "Y": rot_y, "Z": rot_z}
    result = np.eye(3, dtype=np.float64)
    for axis in order:
        result = result @ table[axis]
    m = np.eye(4, dtype=np.float64)
    m[:3, :3] = result
    return m


def compose_matrix(
    location: Sequence[float] = (0.0, 0.0, 0.0),
    rotation: Sequence[float] = (0.0, 0.0, 0.0),
    scale: Sequence[float] = (1.0, 1.0, 1.0),
    order: str = "XYZ",
) -> np.ndarray:
    return (
        translation_matrix(*location)
        @ euler_matrix(*rotation, order=order)
        @ scale_matrix(*scale)
    )


def transform_mesh(mesh: Mesh, **kwargs) -> Mesh:
    """Return a transformed copy of ``mesh`` (see :func:`compose_matrix`)."""
    return mesh.copy().transform(compose_matrix(**kwargs))


def look_at_matrix(origin: Sequence[float], target: Sequence[float], up: Sequence[float] = (0, 0, 1)) -> np.ndarray:
    """Orientation matrix whose +Z axis points from ``origin`` to ``target``."""
    o = np.asarray(origin, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    z_axis = t - o
    norm = np.linalg.norm(z_axis)
    if norm < 1e-9:
        return translation_matrix(*o)
    z_axis /= norm
    up = np.asarray(up, dtype=np.float64)
    x_axis = np.cross(up, z_axis)
    if np.linalg.norm(x_axis) < 1e-6:
        x_axis = np.cross(np.array([0.0, 1.0, 0.0]), z_axis)
    x_axis /= np.linalg.norm(x_axis)
    y_axis = np.cross(z_axis, x_axis)
    m = np.eye(4, dtype=np.float64)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x_axis, y_axis, z_axis, o
    return m


def merge(meshes: Iterable[Mesh], name: str = "") -> Mesh:
    """Concatenate meshes into one (index buffers are offset)."""
    meshes = [m for m in meshes if not m.is_empty()]
    if not meshes:
        return Mesh(name=name)
    vertices = np.concatenate([m.vertices for m in meshes], axis=0)
    normals = np.concatenate([m.normals for m in meshes], axis=0)
    index_blocks = []
    offset = 0
    for m in meshes:
        index_blocks.append(m.indices.astype(np.uint32) + offset)
        offset += m.vertex_count
    indices = np.concatenate(index_blocks, axis=0)
    return Mesh(vertices, normals, indices, name=name)


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #
def primitive_box(sx: float, sy: float, sz: float, name: str = "box") -> Mesh:
    """Axis aligned box centred on the origin."""
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
    corners = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
    ]
    faces = [
        (0, 3, 2, 1, (0, 0, -1)),  # -Z
        (4, 5, 6, 7, (0, 0, 1)),   # +Z
        (0, 1, 5, 4, (0, -1, 0)),  # -Y
        (3, 7, 6, 2, (0, 1, 0)),   # +Y
        (0, 4, 7, 3, (-1, 0, 0)),  # -X
        (1, 2, 6, 5, (1, 0, 0)),   # +X
    ]
    vertices, normals, indices = [], [], []
    for a, b, c, d, n in faces:
        base = len(vertices)
        for i in (a, b, c, d):
            vertices.append(corners[i])
            normals.append(n)
        indices.extend([(base, base + 1, base + 2), (base, base + 2, base + 3)])
    return Mesh(vertices, normals, indices, name)


def primitive_cylinder(
    radius: float,
    height: float,
    segments: int = 24,
    caps: bool = True,
    name: str = "cylinder",
    radius_top: float | None = None,
) -> Mesh:
    """Cylinder centred on the origin, axis along +Z."""
    segments = max(3, int(segments))
    r_bottom = radius
    r_top = radius if radius_top is None else radius_top
    half = height * 0.5
    vertices, normals, indices = [], [], []

    def ring(r: float, z: float):
        base = len(vertices)
        for i in range(segments):
            a = TWO_PI * i / segments
            vertices.append((r * math.cos(a), r * math.sin(a), z))
        return base

    if caps and r_bottom > 0:
        base_center = len(vertices)
        vertices.append((0.0, 0.0, -half))
        normals.append((0.0, 0.0, -1.0))
        bottom = ring(r_bottom, -half)
        for i in range(segments):
            normals.append((0.0, 0.0, -1.0))
        for i in range(segments):
            nxt = (i + 1) % segments
            indices.append((base_center, bottom + nxt, bottom + i))

    if caps and r_top > 0:
        base_center = len(vertices)
        vertices.append((0.0, 0.0, half))
        normals.append((0.0, 0.0, 1.0))
        top = ring(r_top, half)
        for i in range(segments):
            normals.append((0.0, 0.0, 1.0))
        for i in range(segments):
            nxt = (i + 1) % segments
            indices.append((base_center, top + i, top + nxt))

    bottom = ring(r_bottom, -half)
    top = ring(r_top, half)
    slope = (r_bottom - r_top) / height if height else 0.0
    for i in range(segments):
        a = TWO_PI * i / segments
        n = np.array([math.cos(a), math.sin(a), slope], dtype=np.float64)
        n /= np.linalg.norm(n) or 1.0
        normals.extend([tuple(n)] * 2)
    for i in range(segments):
        nxt = (i + 1) % segments
        indices.append((bottom + i, bottom + nxt, top + nxt))
        indices.append((bottom + i, top + nxt, top + i))
    return Mesh(vertices, normals, indices, name)


def primitive_cone(
    radius_bottom: float,
    radius_top: float,
    height: float,
    segments: int = 24,
    name: str = "cone",
) -> Mesh:
    return primitive_cylinder(
        radius_bottom, height, segments, caps=True, name=name, radius_top=radius_top
    )


def primitive_sphere(
    radius: float,
    segments: int = 24,
    rings: int = 14,
    name: str = "sphere",
    theta_start: float = 0.0,
    theta_length: float = math.pi,
) -> Mesh:
    segments = max(3, int(segments))
    rings = max(2, int(rings))
    vertices, normals, indices = [], [], []
    for r in range(rings + 1):
        theta = theta_start + theta_length * r / rings
        for s in range(segments + 1):
            phi = TWO_PI * s / segments
            nx = math.sin(theta) * math.cos(phi)
            ny = math.sin(theta) * math.sin(phi)
            nz = math.cos(theta)
            vertices.append((radius * nx, radius * ny, radius * nz))
            normals.append((nx, ny, nz))
    stride = segments + 1
    for r in range(rings):
        for s in range(segments):
            a = r * stride + s
            b = a + stride
            if r != 0 or theta_start != 0.0:
                indices.append((a, b, a + 1))
            if r != rings - 1 or theta_start + theta_length != math.pi:
                indices.append((a + 1, b, b + 1))
    return Mesh(vertices, normals, indices, name)


def primitive_torus(
    major_radius: float,
    minor_radius: float,
    major_segments: int = 40,
    minor_segments: int = 14,
    name: str = "torus",
    arc: float = TWO_PI,
) -> Mesh:
    major_segments = max(3, int(major_segments))
    minor_segments = max(3, int(minor_segments))
    vertices, normals, indices = [], [], []
    for i in range(major_segments + 1):
        u = arc * i / major_segments
        cu, su = math.cos(u), math.sin(u)
        for j in range(minor_segments + 1):
            v = TWO_PI * j / minor_segments
            cv, sv = math.cos(v), math.sin(v)
            nx, ny, nz = cv * cu, cv * su, sv
            vertices.append(
                ((major_radius + minor_radius * cv) * cu, (major_radius + minor_radius * cv) * su, minor_radius * sv)
            )
            normals.append((nx, ny, nz))
    stride = minor_segments + 1
    for i in range(major_segments):
        for j in range(minor_segments):
            a = i * stride + j
            b = a + stride
            indices.append((a, b, a + 1))
            indices.append((a + 1, b, b + 1))
    return Mesh(vertices, normals, indices, name)


def primitive_tube(
    radius_outer: float,
    radius_inner: float,
    height: float,
    segments: int = 24,
    name: str = "tube",
) -> Mesh:
    """Hollow cylinder (open ends show the wall thickness)."""
    outer = primitive_cylinder(radius_outer, height, segments, caps=False, name="outer")
    inner = primitive_cylinder(radius_inner, height, segments, caps=False, name="inner")
    inner.normals = -inner.normals
    inner.indices = inner.indices[:, ::-1].copy()

    half = height * 0.5
    rims: list[Mesh] = []
    for z, upward in ((half, True), (-half, False)):
        verts, norms, idx = [], [], []
        nz = 1.0 if upward else -1.0
        for i in range(segments):
            a = TWO_PI * i / segments
            ca, sa = math.cos(a), math.sin(a)
            verts.append((radius_outer * ca, radius_outer * sa, z))
            verts.append((radius_inner * ca, radius_inner * sa, z))
            norms.extend([(0.0, 0.0, nz)] * 2)
        for i in range(segments):
            nxt = (i + 1) % segments
            o0, i0 = 2 * i, 2 * i + 1
            o1, i1 = 2 * nxt, 2 * nxt + 1
            if upward:
                idx.extend([(o0, i0, i1), (o0, i1, o1)])
            else:
                idx.extend([(o0, i1, i0), (o0, o1, i1)])
        rims.append(Mesh(verts, norms, idx, name="rim"))
    return merge([outer, inner, *rims], name)


def primitive_prism(
    profile: Sequence[Sequence[float]],
    height: float,
    taper: float = 1.0,
    name: str = "prism",
    caps: bool = True,
) -> Mesh:
    """Extrude a closed 2D profile along +Z, optionally tapering the top."""
    profile = [(float(p[0]), float(p[1])) for p in profile]
    n = len(profile)
    if n < 3:
        raise ValueError("prism profile needs at least 3 points")
    half = height * 0.5
    bottom = np.array([(p[0], p[1], -half) for p in profile], dtype=np.float64)
    top = np.array([(p[0] * taper, p[1] * taper, half) for p in profile], dtype=np.float64)
    vertices = list(bottom) + list(top)
    indices = []
    for i in range(n):
        j = (i + 1) % n
        indices.append((i, j, j + n))
        indices.append((i, j + n, i + n))
    if caps:
        centroid = bottom[:, :2].mean(axis=0)
        base = len(vertices)
        vertices.append((centroid[0], centroid[1], -half))
        for i in range(n):
            j = (i + 1) % n
            indices.append((base, j, i))
        base = len(vertices)
        vertices.append((centroid[0] * taper, centroid[1] * taper, half))
        for i in range(n):
            j = (i + 1) % n
            indices.append((base, i + n, j + n))
    mesh = Mesh(np.array(vertices, dtype=np.float32), None, np.array(indices, dtype=np.uint32), name)
    return mesh.recompute_normals()


def primitive_loft(
    sections: Sequence[tuple[float, float, Sequence[Sequence[float]]]],
    name: str = "loft",
    cap_ends: bool = True,
) -> Mesh:
    """Loft through ``sections`` given as ``(x, scale, profile)`` along the X axis.

    The profile lives in the local Y/Z plane, so this is the natural primitive
    for the ship's pressure hull: each entry is a station along the keel.
    """
    if len(sections) < 2:
        raise ValueError("loft needs at least two sections")
    ref_len = len(sections[0][2])
    for _, _, prof in sections:
        if len(prof) != ref_len:
            raise ValueError("all loft sections must share the same profile point count")

    rings = []
    for x, scale, profile in sections:
        ring = np.array(
            [(x, p[0] * scale, p[1] * scale) for p in profile], dtype=np.float64
        )
        rings.append(ring)

    vertices = np.concatenate(rings, axis=0)
    indices = []
    for r in range(len(rings) - 1):
        base_a = r * ref_len
        base_b = (r + 1) * ref_len
        for i in range(ref_len):
            j = (i + 1) % ref_len
            indices.append((base_a + i, base_a + j, base_b + j))
            indices.append((base_a + i, base_b + j, base_b + i))
    if cap_ends:
        for ring_idx, ring in ((0, rings[0]), (len(rings) - 1, rings[-1])):
            centroid = ring.mean(axis=0)
            center = len(vertices)
            vertices = np.vstack([vertices, centroid.reshape(1, 3)])
            base = ring_idx * ref_len
            for i in range(ref_len):
                j = (i + 1) % ref_len
                if ring_idx == 0:
                    indices.append((center, base + j, base + i))
                else:
                    indices.append((center, base + i, base + j))
    mesh = Mesh(vertices, None, np.array(indices, dtype=np.uint32), name)
    return mesh.recompute_normals()


def beam_between(
    start: Sequence[float],
    end: Sequence[float],
    width: float,
    height: float,
    name: str = "beam",
) -> Mesh:
    """Rectangular beam spanning two points (used for truss lattices)."""
    start = np.asarray(start, dtype=np.float64)
    end = np.asarray(end, dtype=np.float64)
    length = float(np.linalg.norm(end - start))
    if length < 1e-6:
        return Mesh(name=name)
    box = primitive_box(length, width, height, name)
    # Orient the box's +X axis along the beam direction.
    direction = (end - start) / length
    up = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(direction, up))) > 0.999:
        up = np.array([0.0, 1.0, 0.0])
    side = np.cross(up, direction)
    side /= np.linalg.norm(side)
    real_up = np.cross(direction, side)
    rot = np.stack([direction, side, real_up], axis=1)
    matrix = np.eye(4)
    matrix[:3, :3] = rot
    matrix[:3, 3] = (start + end) * 0.5
    return box.transform(matrix)


def lattice_truss(
    start: Sequence[float],
    end: Sequence[float],
    width: float,
    height: float,
    bays: int,
    member: float = 0.6,
    name: str = "truss",
    diagonals: bool = True,
) -> Mesh:
    """Warren-style lattice truss between two points, cross-section ``width x height``."""
    start = np.asarray(start, dtype=np.float64)
    end = np.asarray(end, dtype=np.float64)
    direction = end - start
    length = float(np.linalg.norm(direction))
    if length < 1e-6 or bays < 1:
        return Mesh(name=name)
    direction /= length
    up = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(direction, up))) > 0.999:
        up = np.array([0.0, 1.0, 0.0])
    side = np.cross(up, direction)
    side /= np.linalg.norm(side)
    real_up = np.cross(direction, side)

    hw, hh = width * 0.5, height * 0.5
    corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]

    def station(t: float) -> list[np.ndarray]:
        base = start + direction * (length * t)
        return [base + side * cx + real_up * cz for cx, cz in corners]

    parts: list[Mesh] = []
    rings = [station(i / bays) for i in range(bays + 1)]
    for ring in rings:
        for i in range(4):
            parts.append(beam_between(ring[i], ring[(i + 1) % 4], member, member))
    for i in range(4):
        for r in range(bays):
            parts.append(beam_between(rings[r][i], rings[r + 1][i], member, member))
            if diagonals:
                j = (i + 1) % 4
                if r % 2 == 0:
                    parts.append(beam_between(rings[r][i], rings[r + 1][j], member * 0.8, member * 0.8))
                else:
                    parts.append(beam_between(rings[r + 1][i], rings[r][j], member * 0.8, member * 0.8))
    return merge(parts, name)


def grid_panel(
    width: float,
    length: float,
    thickness: float = 0.25,
    ribs: int = 6,
    rib_size: float = 0.35,
    name: str = "panel",
) -> Mesh:
    """Flat panel with structural ribs on its underside (radiators, solar wings)."""
    parts = [primitive_box(length, width, thickness, name="skin")]
    step = length / max(1, ribs)
    for i in range(ribs + 1):
        x = -length * 0.5 + step * i
        rib = primitive_box(rib_size, width, rib_size * 2.0, name="rib")
        rib.translate(x, 0.0, -thickness * 0.5 - rib_size)
        parts.append(rib)
    return merge(parts, name)


def rounded_profile(width: float, height: float, corners: int = 6) -> list[tuple[float, float]]:
    """Closed rounded-rectangle profile in the Y/Z plane (super-ellipse)."""
    points: list[tuple[float, float]] = []
    total = corners * 4
    hw, hh = width * 0.5, height * 0.5
    exponent = 2.6
    for i in range(total):
        a = TWO_PI * i / total
        ca, sa = math.cos(a), math.sin(a)
        y = hw * math.copysign(abs(ca) ** (2.0 / exponent), ca)
        z = hh * math.copysign(abs(sa) ** (2.0 / exponent), sa)
        points.append((y, z))
    return points


def hex_profile(width: float, height: float, chamfer: float = 0.22) -> list[tuple[float, float]]:
    """Chamfered hexagonal hull cross-section, a classic hard-SF pressure hull."""
    hw, hh = width * 0.5, height * 0.5
    cy, cz = hw * chamfer, hh * chamfer
    return [
        (hw, -hh + cz),
        (hw, hh - cz),
        (hw - cy, hh),
        (-hw + cy, hh),
        (-hw, hh - cz),
        (-hw, -hh + cz),
        (-hw + cy, -hh),
        (hw - cy, -hh),
    ]
