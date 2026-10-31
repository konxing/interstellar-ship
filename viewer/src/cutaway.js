import * as THREE from '../vendor/three.module.js';

const PROPULSION_ASSET = 'dsx-04_propulsion_system';
const SECTIONED_PARTS = new Set([
  'PROP_Drive_GimbalMount',
  'PROP_Drive_FusionChamber',
  'PROP_Drive_MagneticNozzle',
  'PROP_RCS_Pod',
]);

export function cutawayDefault(assetId) {
  return assetId === PROPULSION_ASSET;
}

export function cutawayCameraScale(assetId) {
  return assetId === PROPULSION_ASSET ? 1.8 : 1;
}

function findPartId(node) {
  let current = node;
  while (current) {
    if (current.userData?.partId) return current.userData.partId;
    current = current.parent;
  }
  return null;
}

function ensureClonedMaterials(mesh) {
  if (mesh.userData.cutawayClone) return;
  const originals = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  const clones = originals.map((material) => {
    const clone = material.clone();
    clone.userData.cutawayOriginalSide = material.side;
    return clone;
  });
  mesh.material = Array.isArray(mesh.material) ? clones : clones[0];
  mesh.userData.cutawayClone = true;
}

export function applyCutaway(root, { assetId, enabled, plane }) {
  if (!root) return;
  const active = assetId === PROPULSION_ASSET && enabled;
  root.traverse((node) => {
    if (!node.isMesh || !SECTIONED_PARTS.has(findPartId(node))) return;
    ensureClonedMaterials(node);
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    for (const material of materials) {
      material.clippingPlanes = active ? [plane] : null;
      material.side = active ? THREE.DoubleSide : material.userData.cutawayOriginalSide;
      material.clipShadows = active;
      material.needsUpdate = true;
    }
  });
}
