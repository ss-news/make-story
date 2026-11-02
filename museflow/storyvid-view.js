// "Dự án video" tab: shows the storyvid web UI (started by the main process) in place of the canvas.
(() => {
  const desktop = window.museDesktop;
  const view = document.getElementById('storyvidView');
  const frame = document.getElementById('storyvidFrame');
  const message = document.getElementById('storyvidMessage');
  const tabs = { storyvid: document.getElementById('viewStoryvidBtn'), canvas: document.getElementById('viewCanvasBtn') };
  let loaded = false;

  function show(name) {
    document.body.classList.toggle('view-storyvid', name === 'storyvid');
    view.classList.toggle('hidden', name !== 'storyvid');
    for (const [key, button] of Object.entries(tabs)) button.setAttribute('aria-selected', String(key === name));
    try { localStorage.setItem('museflow.view', name); } catch {}
    if (name === 'storyvid' && !loaded) connect();
  }

  function setMessage(text, retry) {
    message.hidden = false;
    message.textContent = text;
    if (retry) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = 'Thử khởi động lại';
      button.onclick = async () => { setMessage('Đang khởi động lại storyvid…'); await desktop.restartStoryvid(); connect(); };
      message.append(document.createElement('br'), button);
    }
  }

  async function connect() {
    if (!desktop?.storyvidStatus) return setMessage('Tab này chỉ chạy trong app desktop.');
    for (;;) {
      const status = await desktop.storyvidStatus();
      if (status.state === 'ready') {
        frame.src = status.url;
        frame.hidden = false;
        message.hidden = true;
        loaded = true;
        return;
      }
      if (status.state === 'error') return setMessage(status.error, true);
      setMessage('Đang khởi động storyvid (python -m storyvid.web)…');
      await new Promise(r => setTimeout(r, 700));
    }
  }

  tabs.storyvid.onclick = () => show('storyvid');
  tabs.canvas.onclick = () => show('canvas');
  let saved = 'storyvid';
  try { saved = localStorage.getItem('museflow.view') || 'storyvid'; } catch {}
  show(saved === 'canvas' ? 'canvas' : 'storyvid');
})();
