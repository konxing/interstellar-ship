import assert from 'node:assert/strict';
import test from 'node:test';
import * as THREE from '../vendor/three.module.js';
import {
  applyCutaway,
  cutawayCameraScale,
  cutawayDefault,
} from '../src/cutaway.js';

function makePart(partId, material) {
  const part = new THREE.Group();
  part.userData.partId = partId;
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), material);
  part.add(mesh);
  return { part, mesh };
}

test('propulsion opens in cutaway mode while other assets stay intact', () => {
  assert.equal(cutawayDefault('dsx-04_propulsion_system'), true);
  assert.equal(cutawayDefault('dsx-01_full_ship'), false);
  assert.equal(cutawayDefault('dsx-03_interior_compartments'), false);
});

test('propulsion camera leaves room to inspect the complete sectioned engine', () => {
  assert.equal(cutawayCameraScale('dsx-04_propulsion_system'), 1.8);
  assert.equal(cutawayCameraScale('dsx-01_full_ship'), 1);
});

test('cutaway clips only sectioned shells and preserves shared internal materials', () => {
  const root = new THREE.Group();
  const shared = new THREE.MeshStandardMaterial({ side: THREE.FrontSide });
  const chamber = makePart('PROP_Drive_FusionChamber', shared);
  const pumps = makePart('PROP_Drive_Turbopumps', shared);
  root.add(chamber.part, pumps.part);
  const plane = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);

  applyCutaway(root, { assetId: 'dsx-04_propulsion_system', enabled: true, plane });

  assert.notEqual(chamber.mesh.material, shared);
  assert.deepEqual(chamber.mesh.material.clippingPlanes, [plane]);
  assert.equal(chamber.mesh.material.side, THREE.DoubleSide);
  assert.equal(pumps.mesh.material, shared);
  assert.equal(pumps.mesh.material.clippingPlanes, null);

  applyCutaway(root, { assetId: 'dsx-04_propulsion_system', enabled: false, plane });
  assert.equal(chamber.mesh.material.clippingPlanes, null);
  assert.equal(chamber.mesh.material.side, THREE.FrontSide);
});

test('cutaway never activates for another asset', () => {
  const root = new THREE.Group();
  const chamber = makePart('PROP_Drive_FusionChamber', new THREE.MeshStandardMaterial());
  root.add(chamber.part);

  applyCutaway(root, { assetId: 'dsx-01_full_ship', enabled: true, plane: new THREE.Plane() });

  assert.equal(chamber.mesh.material.clippingPlanes, null);
});
