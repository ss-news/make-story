// Preload for the canvas window: exposes the desktop API and a chrome.* shim covering
// what app.js still uses (storage, manifest, getURL).
const { contextBridge, ipcRenderer } = require('electron');

const version = ipcRenderer.sendSync('app:version');

// Chromium already defines window.chrome, so desktop-shim.js copies these onto it.
contextBridge.exposeInMainWorld('museChrome', {
  runtime: {
    getManifest: () => ({ version, name: 'MuseFlow Desktop' }),
    getURL: relative => `museflow://app/${String(relative).replace(/^\/+/, '')}`
  },
  storage: {
    local: {
      get: keys => ipcRenderer.invoke('storage:get', keys ?? null),
      set: items => ipcRenderer.invoke('storage:set', items)
    }
  }
});

contextBridge.exposeInMainWorld('museDesktop', {
  listProfiles: () => ipcRenderer.invoke('profiles:list'),
  addProfile: name => ipcRenderer.invoke('profiles:add', name),
  removeProfile: id => ipcRenderer.invoke('profiles:remove', id),
  renameProfile: (id, name) => ipcRenderer.invoke('profiles:rename', id, name),
  showProfile: (id, visible = true) => ipcRenderer.invoke('profiles:show', id, visible),
  reloadProfile: id => ipcRenderer.invoke('profiles:reload', id),
  checkProfiles: id => ipcRenderer.invoke('profiles:check', id ?? null),
  onProfilesChanged: callback => {
    const listener = (_event, list) => callback(list);
    ipcRenderer.on('profiles:changed', listener);
    return () => ipcRenderer.removeListener('profiles:changed', listener);
  },
  generate: request => ipcRenderer.invoke('muse:generate', request),
  chat: request => ipcRenderer.invoke('muse:chat', request),
  stop: requestId => ipcRenderer.invoke('muse:stop', requestId ?? null),
  openMediaFolder: () => ipcRenderer.invoke('media:folder')
});
