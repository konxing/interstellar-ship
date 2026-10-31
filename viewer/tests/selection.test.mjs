/** Picking must respect visibility, otherwise hidden systems answer clicks. */
import assert from 'node:assert/strict';
import { test } from 'node:test';

import * as THREE from '../vendor/three.module.js';
import { focusTarget, pickPart } from '../src/selection.js';

function partMesh(partId, { position = [0, 0, 0], size = [2, 2, 2] } = {}) {
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(...size),
    new THREE.MeshStandardMaterial(),
  );
  mesh.position.set(...position);
  mesh.userData.partId = partId;
  return mesh;
}

test('a click on a hidden system group reports nothing', () => {
  const root = new THREE.Group();
  const hidden = new THREE.Group();
  hidden.name = 'SYS_THERMAL';
  hidden.visible = false;
  const hiddenMesh = partMesh('PROP_Radiator');
  hidden.add(hiddenMesh);
  root.add(hidden);

  assert.equal(pickPart([hiddenMesh]), null);
});

test('a click on a visible part wins over a nearer hidden one', () => {
  const root = new THREE.Group();
  const hiddenGroup = new THREE.Group();
  hiddenGroup.visible = false;
  const hiddenMesh = partMesh('PROP_Radiator');
  hiddenGroup.add(hiddenMesh);
  const visibleMesh = partMesh('PROP_Nozzle');
  root.add(hiddenGroup, visibleMesh);

  const picked = pickPart([hiddenMesh, visibleMesh]);
  assert.equal(picked.userData.partId, 'PROP_Nozzle');
});

test('a hit on a child mesh resolves to its part node', () => {
  const group = new THREE.Group();
  group.userData.partId = 'DECK_Plate';
  const child = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial());
  group.add(child);

  assert.equal(pickPart([child]), group);
});

test('no hits means no selection', () => {
  assert.equal(pickPart([]), null);
  assert.equal(pickPart([new THREE.Mesh()]), null);
});

test('focus target is the world-space centre of the part', () => {
  const group = new THREE.Group();
  group.position.set(10, 0, 0);
  const mesh = partMesh('DECK_Plate', { position: [4, 2, -6], size: [2, 4, 2] });
  group.add(mesh);
  group.updateMatrixWorld(true);

  const target = focusTarget(mesh);
  assert.ok(target instanceof THREE.Vector3);
  assert.ok(target.distanceTo(new THREE.Vector3(14, 2, -6)) < 1e-6, target.toArray().join(','));
});
