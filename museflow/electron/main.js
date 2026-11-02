// MuseFlow desktop main process.
// - Serves the existing canvas UI (app.html/app.js) over the privileged museflow:// scheme.
// - Keeps one persistent Electron session per Muse account ("profile"), each in its own window
//   with muse-bridge.js preloaded, so several signed-in accounts can generate in parallel.
// - Schedules generation/chat jobs onto whichever signed-in profile is free.
// - Starts the storyvid web UI (python -m storyvid.web in the parent repo) and shows it in the "Video projects" tab.
const { app, BrowserWindow, ipcMain, protocol, session, shell } = require('electron');
const { spawn } = require('node:child_process');
const http = require('node:http');
const path = require('node:path');
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const crypto = require('node:crypto');
const { Readable } = require('node:stream');
const { startApi } = require('./api');

const ROOT = path.join(__dirname, '..');
// MUSEFLOW_MUSE_HOME points accounts at a local mock chat page for testing (see test/mock-muse).
const MUSE_HOME = process.env.MUSEFLOW_MUSE_HOME || 'https://muse.ai/';
const MUSE_URL = process.env.MUSEFLOW_MUSE_HOME ? { test: url => String(url).startsWith(process.env.MUSEFLOW_MUSE_HOME) } : /^https:\/\/(?:[^/]+\.)?muse\.ai\//i;

protocol.registerSchemesAsPrivileged([{
  scheme: 'museflow',
  privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true, corsEnabled: true }
}]);

// storyvid lives one folder up (the video repo); STORYVID_PYTHON / STORYVID_WEB_PORT override the defaults.
const REPO = path.join(ROOT, '..');
const STORYVID_PORT = Number(process.env.STORYVID_WEB_PORT) || 8765;
const STORYVID_URL = `http://127.0.0.1:${STORYVID_PORT}/`;
let storyvid = { proc: null, state: 'starting', error: '' };

let appWindow = null;
let quitting = false;
let dataDir, mediaDir, profilesFile, storageFile;

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json', '.wasm': 'application/wasm', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.webp': 'image/webp', '.gif': 'image/gif', '.svg': 'image/svg+xml', '.txt': 'text/plain; charset=utf-8',
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime', '.m4v': 'video/mp4'
};

// ---------- museflow:// protocol (app files + downloaded media, with Range support for video) ----------

async function serveFile(file, request) {
  let stat;
  try { stat = await fsp.stat(file); } catch { return new Response('Not found', { status: 404 }); }
  if (!stat.isFile()) return new Response('Not found', { status: 404 });
  const type = MIME[path.extname(file).toLowerCase()] || 'application/octet-stream';
  const range = /^bytes=(\d*)-(\d*)$/.exec(request.headers.get('range') || '');
  if (range && (range[1] || range[2])) {
    let start = range[1] ? Number(range[1]) : Math.max(0, stat.size - Number(range[2]));
    let end = range[1] && range[2] ? Math.min(Number(range[2]), stat.size - 1) : stat.size - 1;
    if (start > end || start >= stat.size) return new Response(null, { status: 416, headers: { 'Content-Range': `bytes */${stat.size}` } });
    return new Response(Readable.toWeb(fs.createReadStream(file, { start, end })), {
      status: 206,
      headers: { 'Content-Type': type, 'Content-Length': String(end - start + 1), 'Content-Range': `bytes ${start}-${end}/${stat.size}`, 'Accept-Ranges': 'bytes' }
    });
  }
  return new Response(Readable.toWeb(fs.createReadStream(file)), {
    // no-store: app files change during development and must never come from the HTTP cache.
    headers: { 'Content-Type': type, 'Content-Length': String(stat.size), 'Accept-Ranges': 'bytes', 'Cache-Control': 'no-store' }
  });
}

function resolveInside(base, relative) {
  const target = path.normalize(path.join(base, decodeURIComponent(relative)));
  return target.startsWith(base + path.sep) ? target : null;
}

function handleMuseflowProtocol(request) {
  const url = new URL(request.url);
  const base = url.host === 'app' ? ROOT : url.host === 'media' ? mediaDir : null;
  const file = base && resolveInside(base, url.pathname.replace(/^\/+/, ''));
  if (!file) return new Response('Not found', { status: 404 });
  return serveFile(file, request);
}

// ---------- small JSON persistence ----------

function readJson(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return fallback; }
}
function writeJson(file, value) {
  const tmp = `${file}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(value));
  fs.renameSync(tmp, file);
}

// ---------- Profiles (one persistent session + window per Muse account) ----------

const profiles = new Map(); // id -> { id, name, lastUrl, window, status, busy, detail, checkTimer }

function profileSummary(p) {
  return { id: p.id, name: p.name, status: p.status, busy: p.busy, detail: p.detail || '', url: p.lastUrl || '', visible: Boolean(p.window && !p.window.isDestroyed() && p.window.isVisible()) };
}
function listProfiles() { return [...profiles.values()].map(profileSummary); }
function broadcastProfiles() {
  if (appWindow && !appWindow.isDestroyed()) appWindow.webContents.send('profiles:changed', listProfiles());
}
function saveProfiles() {
  writeJson(profilesFile, [...profiles.values()].map(p => ({ id: p.id, name: p.name, lastUrl: p.lastUrl })));
}
function setStatus(p, status, detail = '') {
  p.status = status; p.detail = detail;
  broadcastProfiles();
  if (status === 'ready') pumpQueue();
}

function chromeUserAgent(ses) {
  // Muse (and Google sign-in) may treat the default Electron UA as an unsupported browser.
  return ses.getUserAgent().replace(/\s*Electron\/\S+/, '').replace(/\s*museflow-desktop\/\S+/i, '');
}

function createProfileWindow(p) {
  const partition = `persist:muse-${p.id}`;
  const ses = session.fromPartition(partition);
  ses.setUserAgent(chromeUserAgent(ses));
  const win = new BrowserWindow({
    width: 1100, height: 820, show: false, title: `Muse · ${p.name}`,
    webPreferences: {
      partition,
      preload: path.join(__dirname, 'muse-preload.js'),
      contextIsolation: true,
      sandbox: false,
      backgroundThrottling: false
    }
  });
  p.window = win;
  win.on('page-title-updated', event => { event.preventDefault(); });
  win.on('close', event => {
    if (quitting) return;
    event.preventDefault(); win.hide(); broadcastProfiles();
  });
  win.on('show', broadcastProfiles);
  win.on('hide', broadcastProfiles);
  const wc = win.webContents;
  wc.setWindowOpenHandler(({ url }) => {
    // Sign-in popups (OAuth) must stay in the same session; everything else opens externally.
    if (MUSE_URL.test(url) || /accounts\.google\.com|appleid\.apple\.com|login|oauth|auth/i.test(url)) {
      return { action: 'allow', overrideBrowserWindowOptions: { webPreferences: { partition } } };
    }
    shell.openExternal(url);
    return { action: 'deny' };
  });
  const remember = (_e, url) => {
    if (MUSE_URL.test(url)) { p.lastUrl = url; saveProfiles(); }
  };
  wc.on('did-navigate', remember);
  wc.on('did-navigate-in-page', remember);
  wc.on('did-start-loading', () => { if (!p.busy) setStatus(p, 'loading'); });
  wc.on('did-finish-load', () => scheduleCheck(p, 2500));
  wc.on('did-navigate-in-page', () => scheduleCheck(p, 1500));
  wc.on('render-process-gone', () => setStatus(p, 'error', 'Page crashed. Reload this account.'));
  win.loadURL(p.lastUrl || MUSE_HOME);
}

function addProfile(name) {
  const id = crypto.randomUUID().slice(0, 8);
  const p = { id, name: String(name || '').trim() || `Account ${profiles.size + 1}`, lastUrl: '', status: 'loading', busy: false };
  profiles.set(id, p);
  saveProfiles();
  createProfileWindow(p);
  p.window.show(); // first time: user signs in
  broadcastProfiles();
  return profileSummary(p);
}

async function removeProfile(id) {
  const p = profiles.get(id);
  if (!p) return false;
  clearTimeout(p.checkTimer);
  if (p.window && !p.window.isDestroyed()) p.window.destroy();
  profiles.delete(id);
  saveProfiles();
  await session.fromPartition(`persist:muse-${id}`).clearStorageData().catch(() => {});
  broadcastProfiles();
  return true;
}

// ---------- Bridge RPC to a profile page ----------

const pendingBridge = new Map(); // rpcId -> { resolve, reject, timer }

ipcMain.on('bridge:response', (_event, { rpcId, response }) => {
  const pending = pendingBridge.get(rpcId);
  if (!pending) return;
  clearTimeout(pending.timer);
  pendingBridge.delete(rpcId);
  pending.resolve(response);
});

function bridgeCall(p, message, timeoutMs) {
  return new Promise((resolve, reject) => {
    if (!p.window || p.window.isDestroyed()) { reject(new Error(`Account "${p.name}" window is closed.`)); return; }
    const rpcId = crypto.randomUUID();
    const timer = setTimeout(() => { pendingBridge.delete(rpcId); reject(new Error(`Account "${p.name}" did not answer in time.`)); }, timeoutMs);
    pendingBridge.set(rpcId, { resolve, reject, timer });
    p.window.webContents.send('bridge:request', { rpcId, message });
  });
}

function scheduleCheck(p, delay) {
  clearTimeout(p.checkTimer);
  p.checkTimer = setTimeout(() => checkProfile(p), delay);
}

async function checkProfile(p) {
  if (p.busy) return profileSummary(p);
  try {
    const result = await bridgeCall(p, { type: 'MUSEFLOW_CHECK_SESSION' }, 20000);
    if (p.busy) return profileSummary(p);
    if (result?.composer && result?.signedIn) setStatus(p, 'ready');
    else if (result?.loginRequired) setStatus(p, 'login', 'Sign in to Muse in this window.');
    else setStatus(p, 'login', result?.error || 'Open the Muse chat page in this window.');
  } catch (error) {
    if (!p.busy) setStatus(p, 'login', error.message || String(error));
  }
  return profileSummary(p);
}

// ---------- Scheduler ----------

const queue = []; // { preferredId, resolve, reject, signalId }

function freeProfile(preferredId) {
  const candidates = [...profiles.values()].filter(p => p.status === 'ready' && !p.busy);
  return candidates.find(p => p.id === preferredId) || candidates[0] || null;
}

function pumpQueue() {
  while (queue.length) {
    const job = queue[0];
    const p = freeProfile(job.preferredId);
    if (!p) return;
    queue.shift();
    p.busy = true; broadcastProfiles();
    job.resolve(p);
  }
}

function acquireProfile(preferredId, requestId) {
  if (!profiles.size) return Promise.reject(new Error('No Muse accounts yet. Add an account and sign in first.'));
  return new Promise((resolve, reject) => {
    queue.push({ preferredId, resolve, reject, requestId });
    pumpQueue();
  });
}

function releaseProfile(p) {
  p.busy = false;
  broadcastProfiles();
  scheduleCheck(p, 1500);
  pumpQueue();
}

const runningRequests = new Map(); // requestId -> profile

async function toBridgeReference(url) {
  // Muse pages cannot read museflow:// files from another session, so hand them data URLs.
  if (typeof url !== 'string' || !url.startsWith('museflow://media/')) return url;
  const file = resolveInside(mediaDir, new URL(url).pathname.replace(/^\/+/, ''));
  const bytes = await fsp.readFile(file);
  const type = MIME[path.extname(file).toLowerCase()] || 'application/octet-stream';
  return `data:${type};base64,${bytes.toString('base64')}`;
}

async function storeMedia(p, url, kind) {
  // Videos come back as remote (cookie-protected) URLs or big data URLs; keep them on disk.
  if (!url || kind !== 'video') return url;
  let bytes, type = '';
  if (url.startsWith('data:')) {
    const match = /^data:([^;,]*)(;base64)?,(.*)$/s.exec(url);
    if (!match) return url;
    type = match[1];
    bytes = match[2] ? Buffer.from(match[3], 'base64') : Buffer.from(decodeURIComponent(match[3]));
  } else if (/^https?:/i.test(url)) {
    const response = await session.fromPartition(`persist:muse-${p.id}`).fetch(url);
    if (!response.ok) throw new Error(`Video download returned HTTP ${response.status}.`);
    type = response.headers.get('content-type') || '';
    bytes = Buffer.from(await response.arrayBuffer());
  } else {
    return url;
  }
  if (!bytes.length) throw new Error('Muse returned an empty video file.');
  const ext = /webm/i.test(type) ? '.webm' : /quicktime/i.test(type) ? '.mov' : '.mp4';
  const name = `${Date.now()}-${crypto.randomUUID().slice(0, 8)}${ext}`;
  await fsp.writeFile(path.join(mediaDir, name), bytes);
  return `museflow://media/${name}`;
}

async function runOnProfile(message, timeoutMs) {
  const p = await acquireProfile(message.profileId, message.requestId);
  if (message.requestId) runningRequests.set(message.requestId, p);
  setStatus(p, 'ready', message.type === 'MUSEFLOW_CHAT' ? 'Writing script…' : `Generating ${message.mediaType || ''}…`);
  try {
    const outgoing = { ...message };
    if (Array.isArray(outgoing.referenceImages)) outgoing.referenceImages = await Promise.all(outgoing.referenceImages.map(toBridgeReference));
    const reply = await bridgeCall(p, outgoing, timeoutMs);
    if (reply?.ok && message.type === 'MUSEFLOW_GENERATE') reply.url = await storeMedia(p, reply.url, message.mediaType);
    return { ...reply, profileId: p.id, profileName: p.name };
  } catch (error) {
    return { ok: false, error: error.message || String(error), profileId: p.id, profileName: p.name };
  } finally {
    if (message.requestId) runningRequests.delete(message.requestId);
    p.detail = '';
    releaseProfile(p);
  }
}

async function stopRequests(requestId) {
  // Drop queued jobs first so they never reach a page, then stop what is running.
  for (let i = queue.length - 1; i >= 0; i--) {
    if (!requestId || queue[i].requestId === requestId) {
      const [job] = queue.splice(i, 1);
      job.reject(Object.assign(new Error('Generation stopped by user.'), { name: 'AbortError' }));
    }
  }
  const targets = requestId ? [runningRequests.get(requestId)].filter(Boolean) : [...new Set(runningRequests.values())];
  await Promise.allSettled(targets.map(p => bridgeCall(p, { type: 'MUSEFLOW_STOP_GENERATION', requestId }, 5000)));
  return true;
}

// ---------- IPC for the canvas window ----------

function registerIpc() {
  ipcMain.handle('profiles:list', () => listProfiles());
  ipcMain.handle('profiles:add', (_e, name) => addProfile(name));
  ipcMain.handle('profiles:remove', (_e, id) => removeProfile(id));
  ipcMain.handle('profiles:rename', (_e, id, name) => {
    const p = profiles.get(id);
    if (p && String(name || '').trim()) { p.name = String(name).trim(); p.window?.setTitle(`Muse · ${p.name}`); saveProfiles(); broadcastProfiles(); }
    return listProfiles();
  });
  ipcMain.handle('profiles:show', (_e, id, visible = true) => {
    const p = profiles.get(id);
    if (!p) return false;
    if (!p.window || p.window.isDestroyed()) createProfileWindow(p);
    if (visible) { p.window.show(); p.window.focus(); } else p.window.hide();
    return true;
  });
  ipcMain.handle('profiles:reload', (_e, id) => {
    const p = profiles.get(id);
    if (p?.window && !p.window.isDestroyed()) p.window.webContents.reload();
    return true;
  });
  ipcMain.handle('profiles:check', async (_e, id) => {
    const targets = id ? [profiles.get(id)].filter(Boolean) : [...profiles.values()];
    await Promise.all(targets.map(checkProfile));
    return listProfiles();
  });

  ipcMain.handle('muse:generate', (_e, request) => {
    const timeoutMs = (Math.min(900, Math.max(30, Number(request.timeoutSec) || 600)) + 60) * 1000;
    return runOnProfile({ ...request, type: 'MUSEFLOW_GENERATE' }, timeoutMs);
  });
  ipcMain.handle('muse:chat', (_e, request) => {
    const timeoutMs = (Math.min(900, Math.max(30, Number(request.timeoutSec) || 420)) + 60) * 1000;
    return runOnProfile({ ...request, type: 'MUSEFLOW_CHAT' }, timeoutMs);
  });
  ipcMain.handle('muse:stop', (_e, requestId) => stopRequests(requestId));

  ipcMain.on('app:version', event => { event.returnValue = app.getVersion(); });
  ipcMain.handle('storage:get', (_e, keys) => {
    const all = readJson(storageFile, {});
    if (keys == null) return all;
    const list = Array.isArray(keys) ? keys : typeof keys === 'string' ? [keys] : Object.keys(keys);
    const out = {};
    for (const key of list) {
      if (key in all) out[key] = all[key];
      else if (keys && typeof keys === 'object' && !Array.isArray(keys)) out[key] = keys[key];
    }
    return out;
  });
  ipcMain.handle('storage:set', (_e, items) => {
    writeJson(storageFile, { ...readJson(storageFile, {}), ...items });
    return true;
  });
  ipcMain.handle('media:folder', () => { shell.openPath(mediaDir); return mediaDir; });
  // Read-only storyvid data for the Canvas progress diagram (the main process has no CORS limits).
  ipcMain.handle('storyvid:get', (_e, apiPath) => new Promise((resolve, reject) => {
    if (!/^\/api\/projects(\/[a-z0-9_]+\/flow)?$/.test(String(apiPath))) return reject(new Error('Not allowed: ' + apiPath));
    const req = http.get(STORYVID_URL.replace(/\/$/, '') + apiPath, { timeout: 5000 }, res => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', chunk => { body += chunk; });
      res.on('end', () => { try { resolve(JSON.parse(body)); } catch (error) { reject(error); } });
    });
    req.on('error', reject);
    req.on('timeout', () => req.destroy(new Error('storyvid did not answer')));
  }));
  ipcMain.handle('storyvid:status', () => ({ url: STORYVID_URL, state: storyvid.state, error: storyvid.error }));
  ipcMain.handle('storyvid:restart', async () => { stopStoryvid(); await startStoryvid(); return { url: STORYVID_URL, state: storyvid.state, error: storyvid.error }; });
}

// ---------- storyvid web UI ----------

function storyvidAnswers() {
  return new Promise(resolve => {
    const req = http.get(STORYVID_URL, { timeout: 1500 }, res => { res.resume(); resolve(res.statusCode === 200); });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
  });
}

// Reuses a server that is already running (started from a terminal); otherwise starts one and stops it on quit.
async function startStoryvid() {
  storyvid = { proc: null, state: 'starting', error: '' };
  if (await storyvidAnswers()) return (storyvid.state = 'ready');
  const python = process.env.STORYVID_PYTHON || path.join(REPO, '.venv', 'bin', 'python');
  if (!fs.existsSync(python)) {
    storyvid = { proc: null, state: 'error', error: `Python not found at ${python}. Create the venv in ${REPO} (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt) or set STORYVID_PYTHON.` };
    return storyvid.state;
  }
  const logFile = path.join(dataDir, 'storyvid-web.log');
  const log = fs.openSync(logFile, 'a');
  const proc = spawn(python, ['-m', 'storyvid.web'], { cwd: REPO, env: { ...process.env, PORT: String(STORYVID_PORT) }, stdio: ['ignore', log, log] });
  storyvid.proc = proc;
  proc.on('exit', code => {
    if (storyvid.proc !== proc) return;
    storyvid = { proc: null, state: 'error', error: `storyvid web UI stopped (exit ${code}). Log: ${logFile}` };
  });
  for (let i = 0; i < 60 && storyvid.proc === proc; i++) {
    if (await storyvidAnswers()) return (storyvid.state = 'ready');
    await new Promise(r => setTimeout(r, 500));
  }
  if (storyvid.state === 'starting') storyvid = { proc, state: 'error', error: `storyvid web UI did not answer on ${STORYVID_URL}. Log: ${logFile}` };
  return storyvid.state;
}

function stopStoryvid() {
  if (storyvid.proc && storyvid.proc.exitCode === null) storyvid.proc.kill('SIGTERM');
  storyvid.proc = null;
}

// ---------- App lifecycle ----------

function createAppWindow() {
  appWindow = new BrowserWindow({
    width: 1500, height: 940, title: 'MuseFlow',
    icon: path.join(ROOT, 'icons', 'icon128.png'),
    webPreferences: { preload: path.join(__dirname, 'app-preload.js'), contextIsolation: true, sandbox: false, backgroundThrottling: false }
  });
  appWindow.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
  // Save exports without a dialog so the automatic story pipeline can finish unattended.
  appWindow.webContents.session.on('will-download', (_event, item) => {
    const dir = process.env.MUSEFLOW_DOWNLOADS || path.join(app.getPath('downloads'), 'MuseFlow');
    fs.mkdirSync(dir, { recursive: true });
    item.setSavePath(path.join(dir, item.getFilename()));
    item.once('done', (_e, state) => {
      if (state === 'completed' && /\.(mp4|webm)$/i.test(item.getFilename())) shell.showItemInFolder(item.getSavePath());
    });
  });
  appWindow.loadURL('museflow://app/app.html');
  appWindow.on('closed', () => { appWindow = null; app.quit(); });
}

app.whenReady().then(() => {
  if (process.env.MUSEFLOW_USER_DATA) app.setPath('userData', process.env.MUSEFLOW_USER_DATA);
  dataDir = app.getPath('userData');
  mediaDir = path.join(dataDir, 'media');
  profilesFile = path.join(dataDir, 'profiles.json');
  storageFile = path.join(dataDir, 'storage.json');
  fs.mkdirSync(mediaDir, { recursive: true });

  protocol.handle('museflow', handleMuseflowProtocol);
  registerIpc();
  for (const saved of readJson(profilesFile, [])) {
    const p = { ...saved, status: 'loading', busy: false };
    profiles.set(p.id, p);
    createProfileWindow(p);
  }
  createAppWindow();
  startStoryvid();
  startApi({
    port: Number(process.env.MUSEFLOW_API_PORT) || 8770,
    listProfiles,
    runOnProfile: (message, timeoutMs) => runOnProfile(message, timeoutMs).catch(error => ({ ok: false, error: error.message || String(error) })),
    stopAll: () => stopRequests(null),
    mediaFilePath: url => (typeof url === 'string' && url.startsWith('museflow://media/') ? resolveInside(mediaDir, new URL(url).pathname.replace(/^\/+/, '')) : null)
  });
  setInterval(() => { for (const p of profiles.values()) if (!p.busy) checkProfile(p); }, 60000);
});

app.on('before-quit', () => { quitting = true; });
app.on('will-quit', stopStoryvid);
// A kill from a terminal skips will-quit unless it goes through app.quit(); the storyvid server would outlive the app.
for (const signal of ['SIGTERM', 'SIGINT']) process.on(signal, () => app.quit());
app.on('window-all-closed', () => app.quit());
