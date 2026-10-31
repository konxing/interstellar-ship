// Click through every asset and report the localised UI + centered part.
const fs = require('node:fs');
const path = require('node:path');

const CDP = 'http://127.0.0.1:9223';
const URL_MATCH = 'http://127.0.0.1:8010/viewer/';
const OUT = 'C:/Users/kkxin/Desktop/DSX-01-delivery/deep-space-exploration-ship/reports';
const ASSETS = [
  'dsx-01_full_ship',
  'dsx-02_deck_01_command',
  'dsx-02_deck_02_operations',
  'dsx-02_deck_03_habitat',
  'dsx-02_deck_04_engineering',
  'dsx-03_interior_compartments',
  'dsx-04_propulsion_system',
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let id = 0;
    const pending = new Map();
    const events = [];
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && pending.has(msg.id)) {
        const { resolve: done, reject: fail } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) fail(new Error(JSON.stringify(msg.error)));
        else done(msg.result);
      } else if (msg.method?.startsWith('Network.')) {
        events.push(msg);
      }
    };
    ws.onerror = reject;
    ws.onopen = () =>
      resolve({
        events,
        send(method, params = {}) {
          const messageId = ++id;
          ws.send(JSON.stringify({ id: messageId, method, params }));
          return new Promise((done, fail) => pending.set(messageId, { resolve: done, reject: fail }));
        },
        close: () => ws.close(),
      });
  });
}

async function evaluate(client, expression) {
  const result = await client.send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}

async function clickAt(client, x, y) {
  const base = { x, y, button: 'left', clickCount: 1 };
  await client.send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
  await client.send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });
}

async function waitFor(client, predicate, label) {
  for (let i = 0; i < 80; i++) {
    const value = await evaluate(client, predicate);
    if (value) return value;
    await sleep(200);
  }
  throw new Error(`timed out waiting for ${label}`);
}

(async () => {
  const list = await (await fetch(`${CDP}/json/list`)).json();
  const target = list.find((t) => t.type === 'page' && t.url.startsWith(URL_MATCH));
  if (!target) throw new Error('viewer page not open');
  const client = await connect(target.webSocketDebuggerUrl);
  await client.send('Page.enable');
  await client.send('Runtime.enable');
  await client.send('Network.enable');
  await client.send('Network.setCacheDisabled', { cacheDisabled: true });
  await client.send('Emulation.setDeviceMetricsOverride', {
    width: 1440, height: 900, deviceScaleFactor: 1, mobile: false,
  });
  await client.send('Page.reload', { ignoreCache: true });
  await sleep(1200);
  await waitFor(client, `document.querySelectorAll('.asset-btn').length === 7`, 'asset list');

  const canvas = await evaluate(client, `(() => {
    const r = document.getElementById('view').getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);

  const results = [];
  for (const assetId of ASSETS) {
    await evaluate(client, `document.querySelector('[data-id="${assetId}"]').click()`);
    await waitFor(
      client,
      `document.getElementById('loading').classList.contains('hidden') &&
       document.querySelector('[data-id="${assetId}"]').classList.contains('active')`,
      `${assetId} active`,
    );
    await sleep(400);

    const hud = await evaluate(client, `document.getElementById('hud-stats').textContent.replace(/\\s+/g, ' ').trim()`);
    const chrome = await evaluate(client, `({
      cutawayRow: !document.getElementById('cutaway-row').classList.contains('hidden'),
      cutawayChecked: document.getElementById('t-cutaway').checked,
    })`);

    await clickAt(client, canvas.x, canvas.y);
    await sleep(350);
    const info = await evaluate(client, `({
      visible: !document.getElementById('info').classList.contains('hidden'),
      label: document.getElementById('info-label').textContent.trim(),
      body: document.getElementById('info-body').textContent.replace(/\\s+/g, ' ').trim(),
    })`);

    results.push({ assetId, hud, chrome, info });

    if (assetId === 'dsx-04_propulsion_system') {
      const shot = await client.send('Page.captureScreenshot', { format: 'png' });
      fs.mkdirSync(OUT, { recursive: true });
      fs.writeFileSync(path.join(OUT, 'viewer-zh-propulsion-cutaway.png'), Buffer.from(shot.data, 'base64'));
    }
  }

  console.log(JSON.stringify(results, null, 2));
  client.close();
})().catch(async (err) => {
  console.error('FAILED', err.message);
  try {
    const list = await (await fetch(`${CDP}/json/list`)).json();
    const target = list.find((t) => t.type === 'page' && t.url.startsWith(URL_MATCH));
    const diag = await connect(target.webSocketDebuggerUrl);
    await diag.send('Runtime.enable');
    const result = await diag.send('Runtime.evaluate', {
      expression: `({
        loadingHidden: document.getElementById('loading').classList.contains('hidden'),
        loadingText: document.getElementById('loading').textContent.trim(),
        active: [...document.querySelectorAll('.asset-btn.active')].map((b) => b.dataset.id),
        hud: document.getElementById('hud-stats').textContent.replace(/\\s+/g, ' ').trim(),
        webgl: (() => { const c = document.getElementById('view'); const g = c.getContext('webgl2') || c.getContext('webgl'); return g ? g.isContextLost() : 'none'; })(),
      })`,
      returnByValue: true,
    });
    console.error('STATE', JSON.stringify(result.result.value, null, 2));
    diag.close();
  } catch (inner) {
    console.error('diag failed', inner.message);
  }
  process.exit(1);
});
