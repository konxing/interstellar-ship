/** A superseded glTF callback must not overwrite the model that replaced it. */
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { createLoadGuard } from '../src/load-guard.js';

test('a load superseded by a newer request is rejected', () => {
  const guard = createLoadGuard();
  const first = guard.begin();
  assert.equal(guard.isCurrent(first), true);

  const second = guard.begin();
  assert.equal(guard.isCurrent(first), false, 'the older asset must not apply');
  assert.equal(guard.isCurrent(second), true);
});

test('only one request is current at a time', () => {
  const guard = createLoadGuard();
  const tokens = [guard.begin(), guard.begin(), guard.begin()];
  assert.deepEqual(
    tokens.map((token) => guard.isCurrent(token)),
    [false, false, true],
  );
});
