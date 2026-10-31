/** The viewer must render only Chinese copy, for shipped models and shell alike. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  deckLabel,
  presetLabel,
  translateAssetCategory,
  translateAssetLabel,
  translateDescription,
  translateMaterial,
  translatePart,
  translateSystem,
  ui,
} from '../src/i18n.js';
import { englishStringsInGlb, readGltfJson } from './helpers/glb-json.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..', '..');
const GLB_DIR = path.join(REPO, 'models', 'glb');
const manifest = JSON.parse(
  fs.readFileSync(path.join(GLB_DIR, 'manifest.json'), 'utf8'),
);

const assets = manifest.assets.map((asset) => ({
  ...asset,
  gltf: readGltfJson(path.join(GLB_DIR, asset.filename)),
}));

const CJK = /[\u4e00-\u9fff]/;

/** Assert `value` is Chinese copy with no English words carried over from `source`. */
function assertRenderedInChinese(source, value, context) {
  assert.match(value, CJK, `${context}: "${value}" has no Chinese characters`);
  const carried = [...new Set(source.match(/[A-Za-z]{4,}/g) ?? [])].filter((word) =>
    new RegExp(`\\b${word}\\b`, 'i').test(value),
  );
  assert.deepEqual(
    carried,
    [],
    `${context}: "${source}" -> "${value}" still shows English ${carried.join(', ')}`,
  );
}

test('every manifest system name renders in Chinese', () => {
  for (const [id, english] of Object.entries(manifest.systems)) {
    assertRenderedInChinese(english, translateSystem(id), `system ${id}`);
  }
});

test('every asset label and category renders in Chinese', () => {
  for (const asset of assets) {
    assertRenderedInChinese(asset.label, translateAssetLabel(asset.label), asset.assetId);
    assertRenderedInChinese(asset.category, translateAssetCategory(asset.category), `${asset.assetId} category`);
  }
});

test('every part label in the shipped models renders in Chinese', () => {
  const seen = new Set();
  for (const asset of assets) {
    for (const label of englishStringsInGlb(asset.gltf).labels) {
      if (seen.has(label)) continue;
      seen.add(label);
      assertRenderedInChinese(label, translatePart(label), `${asset.assetId} part`);
    }
  }
  assert.ok(seen.size >= 69, `expected the full part inventory, only saw ${seen.size}`);
});

test('every part description in the shipped models renders in Chinese', () => {
  const seen = new Set();
  for (const asset of assets) {
    for (const description of englishStringsInGlb(asset.gltf).descriptions) {
      if (seen.has(description)) continue;
      seen.add(description);
      assertRenderedInChinese(description, translateDescription(description), `${asset.assetId} description`);
    }
  }
  assert.ok(seen.size >= 70, `expected the full description inventory, only saw ${seen.size}`);
});

test('every material name in the shipped models renders in Chinese', () => {
  const seen = new Set();
  for (const asset of assets) {
    for (const name of englishStringsInGlb(asset.gltf).materials) {
      if (seen.has(name)) continue;
      seen.add(name);
      assertRenderedInChinese(name, translateMaterial(name), `material ${name}`);
    }
  }
  assert.equal(seen.size, 35);
});

test('strings that are already Chinese pass through untouched', () => {
  assert.equal(translatePart('舰桥'), '舰桥');
  assert.equal(translateDescription('十二个双层铺位。'), '十二个双层铺位。');
  assert.equal(translateMaterial('舱壁'), '舱壁');
  assert.equal(translateAssetLabel('DSX-01 整船'), 'DSX-01 整船');
});

test('camera presets have Chinese labels', () => {
  for (const name of ['hero', 'starboard', 'bow', 'stern', 'top', 'ring']) {
    assertRenderedInChinese(name, presetLabel(name), `preset ${name}`);
  }
});

test('deck numbers map to Chinese deck names', () => {
  assert.equal(deckLabel(1), '指挥与导航');
  assert.equal(deckLabel(2), '运作与科学');
  assert.equal(deckLabel(3), '居住与生命保障');
  assert.equal(deckLabel(4), '工程与动力');
  assert.equal(deckLabel(9), '暂无');
});

test('viewer chrome copy keys are all Chinese', () => {
  const keys = [
    'title', 'tagline', 'panel.assets', 'panel.systems', 'panel.view',
    'control.explode', 'control.wireframe', 'control.grid', 'control.autoRotate',
    'control.spinRing', 'control.starfield', 'control.cutaway',
    'hud.hint', 'hud.triangles', 'hud.meshes', 'hud.materials',
    'info.field.partId', 'info.field.system', 'info.field.deck',
    'info.field.triangles', 'info.field.size', 'info.empty', 'info.close',
    'loading', 'loadError', 'unknownComponent', 'notApplicable',
  ];
  for (const key of keys) {
    const value = ui(key);
    assert.ok(typeof value === 'string' && value.length > 0, `ui("${key}") is missing`);
    assert.match(value, CJK, `ui("${key}") -> "${value}" is not Chinese`);
  }
});

test('the shipped html shell contains no English copy', () => {
  const html = fs.readFileSync(path.join(REPO, 'viewer', 'index.html'), 'utf8')
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<!--[\s\S]*?-->/g, '');
  const text = html.split(/<[^>]*>/g).join(' ');
  const english = [...new Set(text.match(/[A-Za-z]{4,}/g) ?? [])];
  assert.deepEqual(english, [], `index.html still renders English: ${english.join(', ')}`);
});

test('localised text never leaks markup characters', () => {
  const values = [
    ...Object.keys(manifest.systems).map((id) => translateSystem(id)),
    ...assets.map((asset) => translateAssetLabel(asset.label)),
    ...assets.flatMap((asset) => englishStringsInGlb(asset.gltf).labels.map(translatePart)),
  ];
  for (const value of values) {
    assert.doesNotMatch(value, /[<>&]/, `"${value}" would break the panel markup`);
  }
});
