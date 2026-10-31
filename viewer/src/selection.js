/** Raycast result resolution shared by the pointer handler and the tests. */
import * as THREE from '../vendor/three.module.js';

function isVisibleInHierarchy(node) {
  let current = node;
  while (current) {
    if (current.visible === false) return false;
    current = current.parent;
  }
  return true;
}

function partNode(object) {
  let current = object;
  while (current) {
    if (current.userData?.partId) return current;
    current = current.parent;
  }
  return null;
}

/** First hit that belongs to a part whose whole ancestor chain is visible. */
export function pickPart(hits) {
  for (const hit of hits) {
    const object = hit?.object ?? hit;
    if (!object) continue;
    if (!isVisibleInHierarchy(object)) continue;
    const part = partNode(object);
    if (part) return part;
  }
  return null;
}

/** World-space centre of a part, used to re-target the orbit controls. */
export function focusTarget(node) {
  const box = new THREE.Box3().setFromObject(node);
  if (box.isEmpty()) return node.getWorldPosition(new THREE.Vector3());
  return box.getCenter(new THREE.Vector3());
}
