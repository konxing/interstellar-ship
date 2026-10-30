"""Software rasteriser used to produce the project's preview renders.

No GPU, no Blender and no third-party renderer required: it runs on NumPy only,
so the acceptance report can always be regenerated from source. Output is a
24-bit PNG written with ``zlib`` directly.

Usage::

    python3 scripts/render_preview.py --all
    python3 scripts/render_preview.py --asset full_ship --view hero --width 1600
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import zlib
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geometry.glb import Material, read_glb              # noqa: E402
from shipspec.constants import MATERIALS                  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEW_DIR = os.path.join(REPO_ROOT, "assets", "preview")

# --------------------------------------------------------------------------- #
# Camera / view definitions
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class View:
    name: str
    label: str
    azimuth: float      # degrees, 0 = looking from -X (stern) towards +X
    elevation: float    # degrees above the horizon
    distance: float     # multiples of the model bounding radius
    fov: float = 38.0
    background: str = "space"


VIEWS: tuple[View, ...] = (
    View("hero", "Three-quarter hero view", 32.0, 16.0, 2.5),
    View("starboard", "Starboard broadside", 90.0, 4.0, 2.6),
    View("bow", "Bow quarter view", 12.0, 12.0, 2.4),
    View("stern", "Stern / drive view", 186.0, 9.0, 2.4),
    View("top", "Plan view", 60.0, 78.0, 2.6),
    View("ring", "Centrifuge ring detail", 66.0, 8.0, 1.5),
)


# --------------------------------------------------------------------------- #
# PNG writer
# --------------------------------------------------------------------------- #
def write_png(path: str, rgb: np.ndarray) -> None:
    """Write an (H, W, 3) uint8 array as a baseline PNG."""
    height, width, _ = rgb.shape
    raw = bytearray()
    stride = rgb.astype(np.uint8).tobytes()
    row_bytes = width * 3
    for y in range(height):
        raw.append(0)
        raw.extend(stride[y * row_bytes:(y + 1) * row_bytes])
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            len(data).to_bytes(4, "big")
            + tag
            + data
            + zlib.crc32(tag + data).to_bytes(4, "big")
        )

    header = struct_pack(width, height)
    with open(path, "wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\n")
        handle.write(chunk(b"IHDR", header))
        handle.write(chunk(b"IDAT", compressed))
        handle.write(chunk(b"IEND", b""))


def struct_pack(width: int, height: int) -> bytes:
    import struct

    return struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)


# --------------------------------------------------------------------------- #
# Renderer
# --------------------------------------------------------------------------- #
class SoftwareRenderer:
    """Z-buffered flat/gouraud shaded triangle rasteriser."""

    def __init__(self, width: int, height: int, supersample: int = 2) -> None:
        self.ss = int(supersample)
        self.width = int(width)
        self.height = int(height)
        self.rw = width * self.ss
        self.rh = height * self.ss

    # -- camera ----------------------------------------------------------- #
    @staticmethod
    def camera_basis(eye: np.ndarray, target: np.ndarray, up: np.ndarray):
        forward = target - eye
        forward /= np.linalg.norm(forward)
        right = np.cross(forward, up)
        norm = np.linalg.norm(right)
        if norm < 1e-9:
            right = np.cross(forward, np.array([0.0, 0.0, 1.0]))
            norm = np.linalg.norm(right)
        right /= norm
        real_up = np.cross(right, forward)
        return forward, right, real_up

    def view_matrix(self, eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
        forward, right, real_up = self.camera_basis(eye, target, up)
        rotation = np.stack([right, real_up, -forward], axis=0)
        matrix = np.eye(4)
        matrix[:3, :3] = rotation
        matrix[:3, 3] = -rotation @ eye
        return matrix

    # -- frame ------------------------------------------------------------ #
    def render(
        self,
        triangles: np.ndarray,
        normals: np.ndarray,
        colors: np.ndarray,
        eye: np.ndarray,
        target: np.ndarray,
        up: np.ndarray,
        fov: float,
        light_dir: np.ndarray,
        fill_light: np.ndarray,
    ) -> np.ndarray:
        view = self.view_matrix(eye, target, up)
        verts = triangles.reshape(-1, 3)
        homo = np.concatenate([verts, np.ones((verts.shape[0], 1))], axis=1)
        camera_space = (homo @ view.T)[:, :3].reshape(-1, 3, 3)

        tri_normals_world = normals
        rot = view[:3, :3]
        tri_normals_view = tri_normals_world @ rot.T

        near = 1.0
        z = -camera_space[:, :, 2]
        behind = (z < near).any(axis=1)
        aspect = self.rw / self.rh
        scale = 1.0 / math.tan(math.radians(fov) * 0.5)
        cx, cy = self.rw * 0.5, self.rh * 0.5

        with np.errstate(divide="ignore", invalid="ignore"):
            ndc_x = camera_space[:, :, 0] * scale / np.maximum(z, 1e-6) / aspect
            ndc_y = camera_space[:, :, 1] * scale / np.maximum(z, 1e-6)
        sx = (ndc_x * 0.5 + 0.5) * self.rw
        sy = (1.0 - (ndc_y * 0.5 + 0.5)) * self.rh

        # Shading per triangle (flat normals, two-light rig, distance fog-free).
        n = tri_normals_world
        n_len = np.linalg.norm(n, axis=1, keepdims=True)
        n_len[n_len == 0] = 1.0
        n = n / n_len
        key = np.clip(n @ light_dir, 0.0, 1.0)
        fill = np.clip(n @ fill_light, 0.0, 1.0)
        view_dir = eye - target
        view_dir /= np.linalg.norm(view_dir) or 1.0
        half = light_dir + view_dir
        half /= np.linalg.norm(half) or 1.0
        spec = np.clip(n @ half, 0.0, 1.0) ** 26.0

        shade = 0.20 + 0.72 * key + 0.18 * fill
        face_colors = colors * shade[:, None] + (spec * 0.35)[:, None]
        face_colors = np.clip(face_colors, 0.0, 1.0)

        keep = ~behind
        # Frustum reject: fully outside any screen edge.
        outside = (
            (sx.max(axis=1) < 0) | (sx.min(axis=1) > self.rw)
            | (sy.max(axis=1) < 0) | (sy.min(axis=1) > self.rh)
        )
        keep &= ~outside
        if not keep.any():
            return self._background(target, up)

        sx_k, sy_k, z_k = sx[keep], sy[keep], z[keep]
        colors_k = face_colors[keep]

        depth = np.full((self.rh, self.rw), np.inf, dtype=np.float32)
        frame = np.zeros((self.rh, self.rw, 3), dtype=np.float32)

        x0 = np.floor(sx_k.min(axis=1)).astype(np.int64)
        x1 = np.ceil(sx_k.max(axis=1)).astype(np.int64)
        y0 = np.floor(sy_k.min(axis=1)).astype(np.int64)
        y1 = np.ceil(sy_k.max(axis=1)).astype(np.int64)
        np.clip(x0, 0, self.rw - 1, out=x0)
        np.clip(x1, 0, self.rw, out=x1)
        np.clip(y0, 0, self.rh - 1, out=y0)
        np.clip(y1, 0, self.rh, out=y1)

        order = np.argsort(-z_k.mean(axis=1))  # far to near: fewer depth writes
        for i in order:
            xa, xb = x0[i], x1[i]
            ya, yb = y0[i], y1[i]
            if xb <= xa or yb <= ya:
                continue
            gx = np.arange(xa, xb) + 0.5
            gy = np.arange(ya, yb) + 0.5
            px, py = np.meshgrid(gx, gy)
            a, b = sx_k[i], sy_k[i]
            # Barycentric inside test.
            denom = ((b[1] - b[2]) * (a[0] - a[2]) + (a[2] - a[1]) * (b[0] - b[2]))
            if abs(denom) < 1e-9:
                continue
            w0 = ((b[1] - b[2]) * (px - a[2]) + (a[2] - a[1]) * (py - b[2])) / denom
            w1 = ((b[2] - b[0]) * (px - a[2]) + (a[0] - a[2]) * (py - b[2])) / denom
            w2 = 1.0 - w0 - w1
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not inside.any():
                continue
            zi = w0 * z_k[i, 0] + w1 * z_k[i, 1] + w2 * z_k[i, 2]
            sub_depth = depth[ya:yb, xa:xb]
            sub_color = frame[ya:yb, xa:xb]
            closer = inside & (zi < sub_depth)
            if not closer.any():
                continue
            sub_depth[closer] = zi[closer]
            sub_color[closer] = colors_k[i]

        covered = np.isfinite(depth)
        image = self._background(target, up)
        image[covered] = frame[covered]
        return self._finish(image)

    # -- environment ------------------------------------------------------ #
    def _background(self, target: np.ndarray, up: np.ndarray) -> np.ndarray:
        """Deep space gradient plus a deterministic star field."""
        yy, xx = np.mgrid[0:self.rh, 0:self.rw]
        vertical = (yy / max(1, self.rh - 1)).astype(np.float32)
        top = np.array([0.016, 0.020, 0.036], dtype=np.float32)
        bottom = np.array([0.004, 0.005, 0.012], dtype=np.float32)
        image = top[None, None, :] * vertical[:, :, None] + bottom[None, None, :] * (1.0 - vertical)[:, :, None]

        rng = np.random.default_rng(20260117)
        star_count = int(self.rw * self.rh / 2200)
        sx = rng.integers(0, self.rw, star_count)
        sy = rng.integers(0, self.rh, star_count)
        brightness = rng.uniform(0.25, 1.0, star_count).astype(np.float32)
        tint = rng.uniform(0.75, 1.0, (star_count, 3)).astype(np.float32)
        np.add.at(image, (sy, sx), brightness[:, None] * tint)

        # Faint nebula bloom for depth.
        cx, cy = self.rw * 0.72, self.rh * 0.28
        radius = np.sqrt(((xx - cx) / (self.rw * 0.32)) ** 2 + ((yy - cy) / (self.rh * 0.30)) ** 2)
        bloom = np.clip(1.0 - radius, 0.0, 1.0) ** 3 * 0.09
        image += bloom[:, :, None] * np.array([0.25, 0.35, 0.75], dtype=np.float32)
        return image

    def _finish(self, image: np.ndarray) -> np.ndarray:
        image = np.clip(image, 0.0, 1.0)
        # Reinhard-ish tone curve then gamma.
        image = image / (image + 0.55) * 1.55
        image = np.power(np.clip(image, 0.0, 1.0), 1.0 / 2.2)
        if self.ss > 1:
            h, w, _ = image.shape
            image = image.reshape(self.height, self.ss, self.width, self.ss, 3).mean(axis=(1, 3))
        return (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)


# --------------------------------------------------------------------------- #
# GLB -> renderer arrays
# --------------------------------------------------------------------------- #
COMPONENT_SIZE = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
COMPONENT_DTYPE = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
TYPE_COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def _accessor_array(gltf: dict, bin_chunk: bytes, index: int) -> np.ndarray:
    accessor = gltf["accessors"][index]
    view = gltf["bufferViews"][accessor["bufferView"]]
    dtype = COMPONENT_DTYPE[accessor["componentType"]]
    count = accessor["count"] * TYPE_COUNT[accessor["type"]]
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    itemsize = np.dtype(dtype).itemsize
    return np.frombuffer(bin_chunk, dtype=dtype, count=count, offset=offset)


def _material_rgb(material: dict) -> np.ndarray:
    pbr = material.get("pbrMetallicRoughness", {})
    base = np.array(pbr.get("baseColorFactor", [0.8, 0.8, 0.8, 1.0])[:3], dtype=np.float32)
    emissive = np.array(material.get("emissiveFactor", [0.0, 0.0, 0.0]), dtype=np.float32)
    metallic = float(pbr.get("metallicFactor", 0.0))
    roughness = float(pbr.get("roughnessFactor", 1.0))
    # Approximate PBR response: metals darken diffuse and add tint, emissive adds.
    diffuse = base * (1.0 - metallic * 0.72) * (0.35 + 0.65 * roughness)
    specular_tint = base * metallic * 0.55
    return np.clip(diffuse + specular_tint + emissive * 1.35, 0.0, 1.0)


def load_glb_for_render(path: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ``(triangles, normals, colors)`` arrays for a GLB file."""
    parsed = read_glb(path)
    gltf, bin_chunk = parsed["gltf"], parsed["bin"]
    materials = gltf.get("materials", [])
    triangles, normals, colors = [], [], []

    def node_matrix(node: dict) -> np.ndarray:
        matrix = np.eye(4)
        if "matrix" in node:
            matrix = np.array(node["matrix"], dtype=np.float64).reshape(4, 4).T
            return matrix
        scale = np.array(node.get("scale", [1, 1, 1]), dtype=np.float64)
        translation = np.array(node.get("translation", [0, 0, 0]), dtype=np.float64)
        x, y, z, w = node.get("rotation", [0, 0, 0, 1])
        rotation = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ], dtype=np.float64)
        matrix[:3, :3] = rotation @ np.diag(scale)
        matrix[:3, 3] = translation
        return matrix

    def walk(node_index: int, parent: np.ndarray) -> None:
        node = gltf["nodes"][node_index]
        local = parent @ node_matrix(node)
        if "mesh" in node:
            mesh = gltf["meshes"][node["mesh"]]
            for primitive in mesh["primitives"]:
                attrs = primitive["attributes"]
                positions = _accessor_array(gltf, bin_chunk, attrs["POSITION"]).reshape(-1, 3).astype(np.float64)
                homo = np.concatenate([positions, np.ones((positions.shape[0], 1))], axis=1)
                world = (homo @ local.T)[:, :3]
                rot = local[:3, :3]
                if "NORMAL" in attrs:
                    nrm = _accessor_array(gltf, bin_chunk, attrs["NORMAL"]).reshape(-1, 3).astype(np.float64)
                    world_n = nrm @ np.linalg.inv(rot).T
                    lengths = np.linalg.norm(world_n, axis=1, keepdims=True)
                    lengths[lengths == 0] = 1.0
                    world_n /= lengths
                else:
                    world_n = np.zeros_like(world)
                indices = _accessor_array(gltf, bin_chunk, primitive["indices"]).astype(np.int64)
                tris = world[indices].reshape(-1, 3, 3)
                tri_n = world_n[indices].reshape(-1, 3, 3).mean(axis=1)
                material = materials[primitive.get("material", 0)] if materials else {}
                color = _material_rgb(material)
                triangles.append(tris)
                normals.append(tri_n)
                colors.append(np.repeat(color[None, :], tris.shape[0], axis=0))
        for child in node.get("children", []):
            walk(child, local)

    scene = gltf["scenes"][gltf.get("scene", 0)]
    for root in scene["nodes"]:
        walk(root, np.eye(4))

    if not triangles:
        raise ValueError(f"{path}: no renderable geometry found")
    return (
        np.concatenate(triangles, axis=0),
        np.concatenate(normals, axis=0),
        np.concatenate(colors, axis=0),
    )


def render_asset(
    path: str,
    view: View,
    out_path: str,
    width: int = 1280,
    height: int = 800,
    supersample: int = 2,
    focus: str | None = None,
) -> str:
    triangles, normals, colors = load_glb_for_render(path)
    if focus:
        parsed = read_glb(path)
        keep = _focus_mask(parsed["gltf"], triangles, focus)
        if keep.any():
            triangles, normals, colors = triangles[keep], normals[keep], colors[keep]

    flat = triangles.reshape(-1, 3)
    lo = flat.min(axis=0)
    hi = flat.max(axis=0)
    center = (lo + hi) * 0.5
    radius = float(np.linalg.norm(hi - lo)) * 0.5

    azimuth = math.radians(view.azimuth)
    elevation = math.radians(view.elevation)
    distance = radius * view.distance
    eye = center + np.array([
        -math.cos(azimuth) * math.cos(elevation),
        -math.sin(elevation),
        math.sin(azimuth) * math.cos(elevation),
    ]) * distance

    # glTF is Y-up: world up is +Y.
    up = np.array([0.0, 1.0, 0.0])
    light_dir = np.array([-0.55, 0.72, 0.42])
    light_dir /= np.linalg.norm(light_dir)
    fill_dir = np.array([0.4, -0.2, -0.6])
    fill_dir /= np.linalg.norm(fill_dir)

    renderer = SoftwareRenderer(width, height, supersample)
    image = renderer.render(triangles, normals, colors, eye, center, up, view.fov, light_dir, fill_dir)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    write_png(out_path, image)
    return out_path


def _focus_mask(gltf: dict, triangles: np.ndarray, focus: str) -> np.ndarray:
    """Boolean mask keeping triangles that belong to nodes matching ``focus``."""
    mask = np.zeros(triangles.shape[0], dtype=bool)
    cursor = 0
    materials = gltf.get("materials", [])

    def walk(node_index: int, active: bool) -> None:
        nonlocal cursor
        node = gltf["nodes"][node_index]
        name = node.get("name", "")
        match = active or focus.lower() in name.lower()
        if "mesh" in node:
            for primitive in gltf["meshes"][node["mesh"]]["primitives"]:
                count = gltf["accessors"][primitive["indices"]]["count"] // 3
                if match:
                    mask[cursor:cursor + count] = True
                cursor += count
        for child in node.get("children", []):
            walk(child, match)

    scene = gltf["scenes"][gltf.get("scene", 0)]
    for root in scene["nodes"]:
        walk(root, focus.lower() in gltf["nodes"][root].get("name", "").lower())
    return mask


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
ASSET_VIEWS = {
    "dsx-01_full_ship.glb": ("hero", "starboard", "bow", "stern", "top"),
    "dsx-02_deck_01_command.glb": ("hero", "top"),
    "dsx-02_deck_02_operations.glb": ("hero",),
    "dsx-02_deck_03_habitat.glb": ("hero",),
    "dsx-02_deck_04_engineering.glb": ("hero",),
    "dsx-03_interior_compartments.glb": ("hero", "top"),
    "dsx-04_propulsion_system.glb": ("hero", "stern"),
}


def build_view_table() -> dict[str, View]:
    return {view.name: view for view in VIEWS}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="render every configured asset/view pair")
    parser.add_argument("--asset", help="GLB file name inside models/glb")
    parser.add_argument("--view", default="hero", help="view name: " + ", ".join(v.name for v in VIEWS))
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--supersample", type=int, default=2)
    parser.add_argument("--focus", help="only render nodes whose name contains this text")
    parser.add_argument("--out", help="output PNG path")
    args = parser.parse_args(argv)

    views = build_view_table()
    glb_dir = os.path.join(REPO_ROOT, "models", "glb")
    jobs: list[tuple[str, View, str]] = []

    if args.all:
        for asset, view_names in ASSET_VIEWS.items():
            path = os.path.join(glb_dir, asset)
            if not os.path.exists(path):
                print(f"skip {asset} (missing)")
                continue
            for view_name in view_names:
                stem = asset.replace(".glb", "")
                jobs.append((path, views[view_name], os.path.join(PREVIEW_DIR, f"{stem}__{view_name}.png")))
    else:
        asset = args.asset or "dsx-01_full_ship.glb"
        path = asset if os.path.isabs(asset) else os.path.join(glb_dir, asset)
        out = args.out or os.path.join(
            PREVIEW_DIR, f"{os.path.basename(path).replace('.glb', '')}__{args.view}.png"
        )
        jobs.append((path, views[args.view], out))

    for path, view, out in jobs:
        import time

        started = time.time()
        render_asset(path, view, out, args.width, args.height, args.supersample, args.focus)
        size = os.path.getsize(out)
        print(f"rendered {os.path.relpath(out, REPO_ROOT)} ({size/1024:.0f} KiB, {time.time()-started:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
