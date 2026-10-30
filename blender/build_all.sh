#!/usr/bin/env bash
# Build every DSX-01 asset as a native Blender .blend (and, optionally, a
# Blender-exported .glb for cross-validation against the Python exporter).
#
#   ./blender/build_all.sh                 # .blend files only -> models/blend/
#   ./blender/build_all.sh --with-glb DIR  # also write cross-check GLBs to DIR
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BLEND_DIR="${ROOT}/models/blend"
GLB_DIR=""

if [[ "${1:-}" == "--with-glb" ]]; then
  GLB_DIR="${2:?--with-glb requires an output directory}"
  mkdir -p "${GLB_DIR}"
fi

ASSETS=(
  dsx-01_full_ship
  dsx-02_deck_01_command
  dsx-02_deck_02_operations
  dsx-02_deck_03_habitat
  dsx-02_deck_04_engineering
  dsx-03_interior_compartments
  dsx-04_propulsion_system
)

mkdir -p "${BLEND_DIR}"
for asset in "${ASSETS[@]}"; do
  args=(--asset "${asset}" --blend "${BLEND_DIR}/${asset}.blend")
  if [[ -n "${GLB_DIR}" ]]; then
    args+=(--glb "${GLB_DIR}/${asset}.blender.glb")
  fi
  echo "== ${asset}"
  blender -b -P "${ROOT}/blender/build_asset.py" -- "${args[@]}" \
    | grep -E "DSX_BLENDER_RESULT" || true
done
echo "Done. Blends in ${BLEND_DIR}"
