// "Dự án video" tab: shows the storyvid web UI (started by the main process) in place of the canvas.
(() => {
  const desktop = window.museDesktop;
  const view = document.getElementById('storyvidView');
  const frame = document.getElementById('storyvidFrame');
  const message = document.getElementById('storyvidMessage');
  const tabs = { storyvid: document.getElementById('viewStoryvidBtn'), canvas: document.getElementById('viewCanvasBtn') };
  let loaded = false;

  // ---------- progress diagram on the Canvas tab (storyvid /api/projects/<id>/flow) ----------
  const panel = document.getElementById('flowPanel');
  const stepsBox = document.getElementById('flowSteps');
  const picker = document.getElementById('flowProject');
  const STATE_TEXT = { done: 'xong', running: 'đang chạy', wait: 'chờ bạn', error: 'có lỗi', todo: 'chưa làm' };
  let flowTimer = null;
  let projectId = '';
  try { projectId = localStorage.getItem('museflow.flowProject') || ''; } catch {}

  function setProject(id) {
    projectId = id;
    try { localStorage.setItem('museflow.flowProject', id); } catch {}
  }

  // storyvid tells which project is open (see openProject in storyvid/web/static/app.js)
  window.addEventListener('message', event => {
    if (event.source !== frame.contentWindow || event.data?.type !== 'storyvid:project') return;
    if (/^[a-z0-9_]+$/.test(event.data.id || '')) setProject(event.data.id);
  });

  function openInStoryvid(tab) {
    show('storyvid');
    const post = () => frame.contentWindow?.postMessage({ type: 'storyvid:open', id: projectId, tab }, '*');
    if (loaded) post(); else frame.addEventListener('load', post, { once: true });
  }

  async function loadProjects() {
    const projects = await desktop.storyvidGet('/api/projects');
    if (!projectId || !projects.some(p => p.id === projectId)) setProject(projects[0]?.id || '');
    picker.replaceChildren(...projects.map(p => new Option(p.name || p.id, p.id, false, p.id === projectId)));
  }

  function drawFlow(flow) {
    const job = flow.job?.state === 'running' ? 'Đang chạy…' : '';
    document.getElementById('flowJob').textContent = job;
    stepsBox.replaceChildren();
    flow.steps.forEach((step, index) => {
      if (index) {
        const arrow = document.createElement('span');
        arrow.className = 'flow-arrow';
        arrow.textContent = '→';
        stepsBox.append(arrow);
      }
      const node = document.createElement('button');
      node.type = 'button';
      node.className = `flow-node ${step.state}`;
      node.title = `${step.label}: ${STATE_TEXT[step.state] || step.state}${step.detail ? ' · ' + step.detail : ''}`;
      const label = document.createElement('strong');
      label.textContent = step.label;
      const detail = document.createElement('small');
      detail.textContent = step.detail || STATE_TEXT[step.state] || '';
      node.append(label, detail);
      node.onclick = () => openInStoryvid(step.tab);
      stepsBox.append(node);
    });
  }

  async function refreshFlow() {
    try {
      if (!picker.options.length) await loadProjects();
      if (!projectId) { stepsBox.textContent = 'Chưa có dự án video nào.'; return; }
      drawFlow(await desktop.storyvidGet(`/api/projects/${projectId}/flow`));
    } catch (error) {
      stepsBox.textContent = `Chưa lấy được tiến độ từ storyvid: ${error.message || error}`;
    }
  }

  function watchFlow(on) {
    clearInterval(flowTimer);
    panel.classList.toggle('hidden', !on);
    if (!on) return;
    picker.replaceChildren();  // pick up new projects and the one opened last
    refreshFlow();
    flowTimer = setInterval(refreshFlow, 3000);
  }

  picker.onchange = () => { setProject(picker.value); refreshFlow(); };
  document.getElementById('flowOpenBtn').onclick = () => openInStoryvid('');
  document.getElementById('flowToggleBtn').onclick = event => {
    const open = panel.classList.toggle('collapsed') === false;
    event.currentTarget.textContent = open ? '▾' : '▸';
    event.currentTarget.setAttribute('aria-expanded', String(open));
  };

  function show(name) {
    watchFlow(name === 'canvas' && !!desktop?.storyvidGet);
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
