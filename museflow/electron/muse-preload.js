// Preload for each Muse account window: gives muse-bridge.js the small slice of the
// chrome.runtime API it uses, backed by Electron IPC, then loads the bridge unchanged.
const { ipcRenderer } = require('electron');

const listeners = [];
globalThis.chrome = {
  runtime: {
    onMessage: { addListener(fn) { listeners.push(fn); } }
  }
};

ipcRenderer.on('bridge:request', (_event, { rpcId, message }) => {
  let answered = false;
  const sendResponse = response => {
    if (answered) return;
    answered = true;
    ipcRenderer.send('bridge:response', { rpcId, response });
  };
  for (const fn of listeners) {
    try { fn(message, null, sendResponse); } catch (error) { sendResponse({ ok: false, error: error.message || String(error) }); }
  }
});

require('../muse-bridge.js');
