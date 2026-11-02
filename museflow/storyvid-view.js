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
  let projectId = null;  // '' = the shared canvas that is not tied to a project, null = not chosen yet
  try { projectId = localStorage.getItem('museflow.flowProject'); } catch {}

  // Each project has its own canvas workflow (app.js museflowSwitchWorkflow); the canvas follows the picker.
  async function switchCanvas() {
    if (panel.classList.contains('hidden') || !window.museflowSwitchWorkflow) return;
    const key = projectId ? `museflow:${projectId}` : 'museflow';
    if (!(await window.museflowSwitchWorkflow(key))) flowNote('Workflow đang chạy: canvas giữ nguyên đến khi chạy xong.', true);
  }

  function setProject(id) {
    const changed = id !== projectId;
    projectId = id;
    try { localStorage.setItem('museflow.flowProject', id); } catch {}
    if (changed) switchCanvas();
  }

  function flowNote(text, warn) {
    const box = document.getElementById('flowJob');
    box.textContent = text;
    box.classList.toggle('warn', !!warn);
  }

  // the canvas starts under the panel instead of behind it
  const statusbar = document.querySelector('.statusbar');
  function layoutPanel() {
    const on = !panel.classList.contains('hidden');
    document.body.style.setProperty('--flow-top', `${statusbar.getBoundingClientRect().bottom}px`);
    document.body.style.setProperty('--flow-h', on ? `${panel.offsetHeight + 12}px` : '0px');
    window.dispatchEvent(new Event('resize'));  // app.js redraws the wires
  }
  new ResizeObserver(layoutPanel).observe(panel);
  new ResizeObserver(layoutPanel).observe(statusbar);

  // storyvid tells which project is open (see openProject in storyvid/web/static/app.js)
  window.addEventListener('message', event => {
    if (event.source !== frame.contentWindow || event.data?.type !== 'storyvid:project') return;
    if (/^[a-z0-9_]+$/.test(event.data.id || '') && event.data.id !== projectId) {
      setProject(event.data.id);
      if (picker.options.length) picker.value = projectId;
    }
  });

  function openInStoryvid(tab) {
    show('storyvid');
    if (!projectId) return;
    const post = () => frame.contentWindow?.postMessage({ type: 'storyvid:open', id: projectId, tab }, '*');
    if (loaded) post(); else frame.addEventListener('load', post, { once: true });
  }

  async function loadProjects() {
    const projects = await desktop.storyvidGet('/api/projects');
    if (projectId === null || (projectId && !projects.some(p => p.id === projectId))) setProject(projects[0]?.id || '');
    picker.replaceChildren(new Option('Canvas chung (không gắn dự án)', ''),
      ...projects.map(p => new Option(p.name || p.id, p.id)));
    picker.value = projectId;
  }

  function drawFlow(flow) {
    flowNote(flow.job?.state === 'running' ? 'Đang chạy…' : '');
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
      if (!projectId) {
        flowNote('');
        stepsBox.innerHTML = '<span class="flow-hint">Canvas chung. Chọn một dự án video ở trên để xem tiến độ và canvas riêng của dự án đó.</span>';
        return;
      }
      drawFlow(await desktop.storyvidGet(`/api/projects/${projectId}/flow`));
    } catch (error) {
      // keep the last diagram: storyvid can be slow for a moment while a job writes files
      flowNote(`Chưa cập nhật được: ${String(error.message || error).replace(/^Error invoking remote method '[^']+': (Error: )?/, '')}`, true);
      if (!stepsBox.children.length) stepsBox.textContent = 'Đang đợi storyvid…';
    }
  }

  function watchFlow(on) {
    clearInterval(flowTimer);
    panel.classList.toggle('hidden', !on);
    layoutPanel();
    if (!on) return;
    picker.replaceChildren();  // pick up new projects and the one opened last
    refreshFlow().then(switchCanvas);
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
