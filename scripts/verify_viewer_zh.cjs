// Verify the localised viewer in headless Edge over CDP.
const fs = require('node:fs');
const path = require('node:path');

const CDP = 'http://127.0.0.1:9223';
const URL_MATCH = 'http://127.0.0.1:8010/viewer/';
const OUT = 'C:/Users/kkxin/Desktop/DSX-01-delivery/deep-space-exploration-ship/reports';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function pageTarget() {
  const list = await (await fetch(`${CDP}/json/list`)).json();
  return list.find((t) => t.type === 'page' && t.url.startsWith(URL_MATCH));
}

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let id = 0;
    const pending = new Map();
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && pending.has(msg.id)) {
        const { resolve: done, reject: fail } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) fail(new Error(JSON.stringify(msg.error)));
        else done(msg.result);
      }
    };
    ws.onerror = reject;
    ws.onopen = () =>
      resolve({
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

async function waitForReady(client) {
  for (let i = 0; i < 60; i++) {
    const ready = await evaluate(
      client,
      `(() => {
        const stats = document.getElementById('hud-stats');
        const buttons = document.querySelectorAll('.asset-btn').length;
        return { stats: stats ? stats.textContent.trim() : '', buttons,
                 loading: !document.getElementById('loading').classList.contains('hidden') };
      })()`,
    );
    if (ready.stats && ready.buttons === 7 && !ready.loading) return ready;
    await sleep(250);
  }
  throw new Error('viewer never became ready');
}

async function clickAt(client, x, y) {
  const base = { x, y, button: 'left', clickCount: 1 };
  await client.send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
  await client.send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });
}

(async () => {
  const target = await pageTarget();
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
  await sleep(1500);
  await waitForReady(client);

  const report = await evaluate(client, `(() => {
    const text = (sel) => (document.querySelector(sel)?.textContent ?? '').replace(/\\s+/g, ' ').trim();
    const all = (sel) => [...document.querySelectorAll(sel)].map((n) => n.textContent.replace(/\\s+/g, ' ').trim());
    return {
      title: document.title,
      brand: text('.brand h1'),
      tagline: text('.tagline'),
      headings: all('#sidebar h2'),
      assets: all('.asset-btn'),
      presets: all('.preset-btn'),
      toggles: all('.toggle-grid label'),
      hint: text('#hud-hint'),
      stats: text('#hud-stats'),
      systems: all('#system-list span:last-child'),
      cutawayHidden: document.getElementById('cutaway-row').classList.contains('hidden'),
    };
  })()`);

  const canvasBox = await evaluate(client, `(() => {
    const r = document.getElementById('view').getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);
  await clickAt(client, canvasBox.x, canvasBox.y);
  await sleep(400);

  const info = await evaluate(client, `(() => {
    const panel = document.getElementById('info');
    return {
      visible: !panel.classList.contains('hidden'),
      label: document.getElementById('info-label').textContent.trim(),
      body: document.getElementById('info-body').textContent.replace(/\\s+/g, ' ').trim(),
      box: [...document.querySelectorAll('canvas')].length,
    };
  })()`);

  const shot = await client.send('Page.captureScreenshot', { format: 'png' });
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'viewer-zh-fullship.png'), Buffer.from(shot.data, 'base64'));

  console.log(JSON.stringify({ report, info }, null, 2));
  client.close();
})().catch((err) => {
  console.error('FAILED', err);
  process.exit(1);
});
