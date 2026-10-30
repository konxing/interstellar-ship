/**
 * DSX-01 Kairos Horizon — interactive Three.js workbench.
 *
 * Loads the glTF-binary assets produced by scripts/build_models.py, exposes an
 * asset switcher, per-system isolation, an exploded view, camera presets and an
 * info panel driven entirely by the node `extras` written by the exporter, so
 * the viewer never hard-codes model structure.
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const MODEL_BASE = '../models/glb/';

const SYSTEM_COLORS = {
  SYS_HULL: '#9fb2c8',
  SYS_COMMAND: '#5ad1ff',
  SYS_OPERATIONS: '#7dffb0',
  SYS_HABITAT: '#ffd166',
  SYS_ENGINEERING: '#ff8f5a',
  SYS_SPINE: '#b0a6ff',
  SYS_THERMAL: '#ff6b6b',
  SYS_CENTRIFUGE: '#6bffd9',
  SYS_PROPULSION: '#ffa94d',
  SYS_SENSORS: '#8ecae6',
  SYS_UTILITY: '#c0c0c0',
};

const CAMERA_PRESETS = {
  hero: new THREE.Vector3(1.0, 0.55, -1.0),
  starboard: new THREE.Vector3(0.05, 0.12, -1.6),
  bow: new THREE.Vector3(1.6, 0.18, -0.1),
  stern: new THREE.Vector3(-1.6, 0.2, -0.1),
  top: new THREE.Vector3(0.0, 1.6, -0.02),
  ring: new THREE.Vector3(0.35, 0.3, -0.9),
};

const state = {
  manifest: null,
  assetId: null,
  root: null,            // loaded gltf.scene
  groups: [],            // top-level system groups
  groupMeta: [],         // {group, base:Vector3, dir:Vector3}
  center: new THREE.Vector3(),
  radius: 1,
  centrifuge: null,
  selected: null,
  wireframe: false,
  explode: 0,
};

// --------------------------------------------------------------------------- //
// Renderer / scene bootstrap
// --------------------------------------------------------------------------- //
const canvas = document.getElementById('view');
let renderer = null;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
} catch (err) {
  // No WebGL (headless / software-only clients): keep the workbench usable for
  // inspection and parsing, just without rasterisation.
  console.warn('WebGL unavailable; viewer runs in parse-only mode.', err);
}

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x070a12);

const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 20000);
camera.position.set(300, 180, -300);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.06;

// Lighting rig: soft key + cool fill + rim so the hull reads without textures.
scene.add(new THREE.HemisphereLight(0xbfd8ff, 0x0a0d16, 0.85));
const key = new THREE.DirectionalLight(0xffffff, 1.6);
key.position.set(-1.2, 1.6, 1.0);
scene.add(key);
const fill = new THREE.DirectionalLight(0x88aaff, 0.5);
fill.position.set(1.4, -0.4, -1.2);
scene.add(fill);
const rim = new THREE.DirectionalLight(0xffd9a0, 0.35);
rim.position.set(0.2, -1.0, 1.4);
scene.add(rim);

// Reference grid (glTF XZ plane == ship horizontal plane).
const grid = new THREE.GridHelper(1200, 60, 0x2a3a58, 0x16203a);
grid.material.transparent = true;
grid.material.opacity = 0.5;
scene.add(grid);

// Deterministic starfield shell.
const starfield = (() => {
  const count = 2400;
  const pos = new Float32Array(count * 3);
  let seed = 20260117;
  const rand = () => (seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296;
  for (let i = 0; i < count; i++) {
    const r = 3000 + rand() * 2000;
    const theta = rand() * Math.PI * 2;
    const phi = Math.acos(2 * rand() - 1);
    pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    pos[i * 3 + 1] = r * Math.cos(phi);
    pos[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const mat = new THREE.PointsMaterial({ color: 0xbfd4ff, size: 3, sizeAttenuation: false, transparent: true, opacity: 0.8 });
  const points = new THREE.Points(geo, mat);
  scene.add(points);
  return points;
})();

// --------------------------------------------------------------------------- //
// UI wiring
// --------------------------------------------------------------------------- //
const el = {
  assetList: document.getElementById('asset-list'),
  systemList: document.getElementById('system-list'),
  presets: document.getElementById('camera-presets'),
  explode: document.getElementById('explode'),
  wire: document.getElementById('t-wire'),
  grid: document.getElementById('t-grid'),
  rotate: document.getElementById('t-rotate'),
  spin: document.getElementById('t-spin'),
  stars: document.getElementById('t-stars'),
  hudStats: document.getElementById('hud-stats'),
  info: document.getElementById('info'),
  infoLabel: document.getElementById('info-label'),
  infoBody: document.getElementById('info-body'),
  infoClose: document.getElementById('info-close'),
  loading: document.getElementById('loading'),
};

function showLoading(on) { el.loading.classList.toggle('hidden', !on); }

function buildAssetButtons() {
  el.assetList.innerHTML = '';
  for (const asset of state.manifest.assets) {
    const btn = document.createElement('button');
    btn.className = 'asset-btn';
    btn.dataset.id = asset.assetId;
    btn.innerHTML = `<span class="cat">${asset.category}</span>${asset.label}`;
    btn.addEventListener('click', () => loadAsset(asset.assetId));
    el.assetList.appendChild(btn);
  }
}

function buildSystemList() {
  el.systemList.innerHTML = '';
  if (!state.root) return;
  for (const group of state.groups) {
    const id = group.name || 'SYS_UNKNOWN';
    const label = (state.manifest.systems && state.manifest.systems[id]) || id;
    const row = document.createElement('label');
    const box = document.createElement('input');
    box.type = 'checkbox';
    box.checked = group.visible;
    box.addEventListener('change', () => { group.visible = box.checked; });
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = SYSTEM_COLORS[id] || '#888';
    const text = document.createElement('span');
    text.textContent = label;
    row.append(box, sw, text);
    el.systemList.appendChild(row);
  }
}

function buildPresets() {
  el.presets.innerHTML = '';
  for (const name of Object.keys(CAMERA_PRESETS)) {
    const btn = document.createElement('button');
    btn.className = 'preset-btn';
    btn.textContent = name;
    btn.addEventListener('click', () => applyPreset(name));
    el.presets.appendChild(btn);
  }
}

function applyPreset(name) {
  const dir = CAMERA_PRESETS[name];
  if (!dir) return;
  const dist = state.radius * (name === 'ring' ? 0.55 : 1.0);
  const target = name === 'ring' && state.centrifuge
    ? new THREE.Vector3().setFromMatrixPosition(state.centrifuge.matrixWorld)
    : state.center.clone();
  camera.position.copy(target).addScaledVector(dir.clone().normalize(), dist);
  controls.target.copy(target);
  controls.update();
}

// --------------------------------------------------------------------------- //
// Asset loading
// --------------------------------------------------------------------------- //
const loader = new GLTFLoader();

function disposeObject(obj) {
  obj.traverse((node) => {
    if (node.geometry) node.geometry.dispose();
    if (node.material) {
      const mats = Array.isArray(node.material) ? node.material : [node.material];
      mats.forEach((m) => m.dispose());
    }
  });
}

function loadAsset(assetId) {
  const asset = state.manifest.assets.find((a) => a.assetId === assetId);
  if (!asset) return;
  state.assetId = assetId;
  for (const btn of el.assetList.children) btn.classList.toggle('active', btn.dataset.id === assetId);

  showLoading(true);
  hideInfo();

  if (state.root) {
    scene.remove(state.root);
    disposeObject(state.root);
    state.root = null;
    state.centrifuge = null;
  }

  loader.load(
    MODEL_BASE + asset.filename,
    (gltf) => {
      const root = gltf.scene;
      state.root = root;
      scene.add(root);

      // Top-level groups are the system isolation units.
      state.groups = root.children.filter((c) => c.isGroup || c.isObject3D);
      state.groupMeta = [];

      const box = new THREE.Box3().setFromObject(root);
      if (box.isEmpty()) box.set(new THREE.Vector3(-1, -1, -1), new THREE.Vector3(1, 1, 1));
      box.getCenter(state.center);
      state.radius = box.getSize(new THREE.Vector3()).length() * 0.5;

      for (const group of state.groups) {
        const gb = new THREE.Box3().setFromObject(group);
        const gc = gb.isEmpty() ? state.center.clone() : gb.getCenter(new THREE.Vector3());
        const dir = gc.clone().sub(state.center);
        if (dir.lengthSq() < 1e-6) dir.set(0, 1, 0);
        dir.normalize();
        state.groupMeta.push({ group, base: group.position.clone(), dir });
        if (/CENTRIFUGE/i.test(group.name || '')) state.centrifuge = group;
      }

      // Fit grid to the asset footprint.
      grid.scale.setScalar(Math.max(1, state.radius / 300));
      applyExplode();
      applyWireframe();
      buildSystemList();
      applyPreset('hero');
      updateHud(asset);
      showLoading(false);
      // Machine-readable handshake for automated smoke tests.
      console.info(`DSX_VIEWER_READY ${asset.assetId} groups=${state.groups.length} radius=${state.radius.toFixed(1)}`);
    },
    undefined,
    (err) => {
      console.error('failed to load', asset.filename, err);
      showLoading(false);
    },
  );
}

function applyExplode() {
  const t = state.explode;
  const scale = state.radius * 0.9;
  for (const meta of state.groupMeta) {
    meta.group.position.copy(meta.base).addScaledVector(meta.dir, t * scale);
  }
}

function applyWireframe() {
  if (!state.root) return;
  state.root.traverse((node) => {
    if (node.material) {
      const mats = Array.isArray(node.material) ? node.material : [node.material];
      mats.forEach((m) => { m.wireframe = state.wireframe; });
    }
  });
}

function updateHud(asset) {
  let tris = 0, meshes = 0, mats = new Set();
  state.root.traverse((n) => {
    if (n.isMesh) {
      meshes++;
      const g = n.geometry;
      tris += (g.index ? g.index.count : g.attributes.position.count) / 3;
      const m = Array.isArray(n.material) ? n.material : [n.material];
      m.forEach((mm) => mats.add(mm.name || mm.uuid));
    }
  });
  const size = new THREE.Box3().setFromObject(state.root).getSize(new THREE.Vector3());
  el.hudStats.textContent =
    `${asset.label}\n` +
    `${Math.round(tris).toLocaleString()} tris · ${meshes} meshes · ${mats.size} materials\n` +
    `${size.x.toFixed(0)} × ${size.y.toFixed(0)} × ${size.z.toFixed(0)} m`;
}

// --------------------------------------------------------------------------- //
// Selection + info panel
// --------------------------------------------------------------------------- //
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let downPos = null;

canvas.addEventListener('pointerdown', (e) => { downPos = [e.clientX, e.clientY]; });
canvas.addEventListener('pointerup', (e) => {
  if (!downPos) return;
  const dx = e.clientX - downPos[0];
  const dy = e.clientY - downPos[1];
  downPos = null;
  if (dx * dx + dy * dy > 25) return;   // it was a drag, not a click
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(state.root ? [state.root] : [], true);
  for (const hit of hits) {
    let obj = hit.object;
    while (obj && !obj.userData?.partId) obj = obj.parent;
    if (obj) { showInfo(obj.userData); return; }
  }
  hideInfo();
});

function showInfo(data) {
  el.infoLabel.textContent = data.label || data.partId || 'component';
  const sys = (state.manifest.systems && state.manifest.systems[data.system]) || data.system || '—';
  const rows = [
    ['part id', data.partId || '—'],
    ['system', sys],
    ['deck', data.deck != null ? `Deck 0${data.deck}` : '—'],
    ['triangles', data.triangleCount != null ? Number(data.triangleCount).toLocaleString() : '—'],
  ];
  if (data.bounds) {
    const s = data.bounds.size || [
      data.bounds.max[0] - data.bounds.min[0],
      data.bounds.max[1] - data.bounds.min[1],
      data.bounds.max[2] - data.bounds.min[2],
    ];
    rows.push(['size (m)', `${s[0].toFixed(1)} × ${s[1].toFixed(1)} × ${s[2].toFixed(1)}`]);
  }
  let html = '<dl class="kv">' + rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('') + '</dl>';
  if (data.description) html += `<p class="desc">${data.description}</p>`;
  if (data.materials && data.materials.length) {
    html += '<div class="chips">' + data.materials.map((m) => `<span class="chip">${m}</span>`).join('') + '</div>';
  }
  el.infoBody.innerHTML = html;
  el.info.classList.remove('hidden');
}

function hideInfo() { el.info.classList.add('hidden'); }
el.infoClose.addEventListener('click', hideInfo);

// --------------------------------------------------------------------------- //
// Controls
// --------------------------------------------------------------------------- //
el.explode.addEventListener('input', () => {
  state.explode = el.explode.value / 100;
  applyExplode();
});
el.wire.addEventListener('change', () => { state.wireframe = el.wire.checked; applyWireframe(); });
el.grid.addEventListener('change', () => { grid.visible = el.grid.checked; });
el.stars.addEventListener('change', () => { starfield.visible = el.stars.checked; });

// --------------------------------------------------------------------------- //
// Resize + main loop
// --------------------------------------------------------------------------- //
function resize() {
  const w = canvas.clientWidth || canvas.parentElement.clientWidth;
  const h = canvas.clientHeight || canvas.parentElement.clientHeight;
  if (renderer) renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);

const clock = new THREE.Clock();
function tick() {
  requestAnimationFrame(tick);
  const dt = clock.getDelta();
  controls.autoRotate = el.rotate.checked;
  controls.autoRotateSpeed = 0.6;
  if (el.spin.checked && state.centrifuge) state.centrifuge.rotation.x += dt * 0.35;
  controls.update();
  if (renderer) renderer.render(scene, camera);
}

// --------------------------------------------------------------------------- //
// Boot
// --------------------------------------------------------------------------- //
async function boot() {
  try {
    const res = await fetch(MODEL_BASE + 'manifest.json');
    state.manifest = await res.json();
  } catch (err) {
    console.error('manifest unavailable', err);
    state.manifest = { assets: [], systems: {} };
  }
  buildAssetButtons();
  buildPresets();
  resize();
  tick();
  const first = state.manifest.assets[0];
  if (first) loadAsset(first.assetId);
}

boot();
