const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

const state = { options: null, projects: [], current: null, script: null, dirty: false, poll: null, settings: null };

const LABELS = {
  pose: { idle: "Đứng yên", talk: "Nói", point: "Chỉ tay", scared: "Hoảng sợ", think: "Suy nghĩ", shrug: "Nhún vai",
    reach: "Với tay", wave: "Vẫy tay", cower: "Co rúm" },
  expression: { neutral: "Bình thường", happy: "Vui", scared: "Sợ", surprised: "Ngạc nhiên", sad: "Buồn", angry: "Giận", smirk: "Nhếch mép" },
  position: { far_left: "Sát trái", left: "Trái", center: "Giữa", right: "Phải", far_right: "Sát phải" },
  action: { none: "Đứng tại chỗ", enter: "Đi vào", exit: "Đi ra", approach: "Tiến lại gần", jump: "Giật mình", shake: "Run rẩy" },
  kind: { human: "Người", ghost: "Ma" },
  camera: { zoom_in: "Zoom vào", zoom_out: "Zoom ra", pan_left: "Lia trái", pan_right: "Lia phải", static: "Đứng yên" },
};
const STATUS = { running: "đang chạy", done: "xong", failed: "lỗi", interrupted: "bị ngắt", idle: "" };
const JOBS = { script: "Viết kịch bản", render: "Dựng video" };

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: opts.body ? { "Content-Type": "application/json" } : {},
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (!res.ok) throw new Error(data?.error || `Lỗi ${res.status}`);
  return data;
}

function toast(msg, error = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = `toast show${error ? " error" : ""}`;
  clearTimeout(t._h);
  t._h = setTimeout(() => (t.className = "toast"), 3500);
}

const run = (fn) => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message, true); } };

function show(view) {
  for (const id of ["emptyView", "projectView", "settingsView"]) $("#" + id).classList.toggle("hidden", id !== view);
}

// ---------- sidebar ----------
async function loadProjects() {
  state.projects = await api("/api/projects");
  const nav = $("#projectList");
  nav.innerHTML = "";
  if (!state.projects.length) nav.innerHTML = '<p class="muted">Chưa có dự án.</p>';
  for (const p of state.projects) {
    const b = document.createElement("button");
    b.className = "project-item" + (state.current?.id === p.id ? " active" : "");
    const st = p.status?.state;
    const badge = st === "running" || st === "failed" ? `<span class="badge ${st}">${STATUS[st]}</span>`
      : p.has_video ? '<span class="badge video">video</span>' : "";
    b.innerHTML = `<span class="pi-name"></span><span class="pi-meta">${p.lang.toUpperCase()} · ${p.scenes} cảnh ${badge}</span>`;
    b.querySelector(".pi-name").textContent = p.name;
    b.onclick = run(() => openProject(p.id));
    nav.appendChild(b);
  }
}

// ---------- project ----------
async function openProject(id, tab) {
  if (state.dirty && !confirm("Kịch bản chưa lưu. Bỏ thay đổi?")) return;
  const p = await api(`/api/projects/${id}`);
  state.current = p;
  state.script = p.script ? structuredClone(p.script) : null;
  state.dirty = false;
  location.hash = id;
  show("projectView");
  $("#pName").value = p.name;
  $("#pLang").value = p.lang;
  $("#pMinutes").value = p.meta.minutes ?? 2;
  $("#story").value = p.story;
  renderScript();
  renderVideo();
  renderJob(p.status);
  selectTab(tab || (p.has_video ? "video" : p.script ? "script" : "story"));
  loadProjects();
  if (p.status.state === "running") startPolling();
}

function selectTab(name) {
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  $$(".tabpane").forEach((p) => p.classList.toggle("hidden", p.dataset.pane !== name));
}

async function saveMeta() {
  const id = state.current.id;
  await api(`/api/projects/${id}`, { method: "PUT", body: {
    name: $("#pName").value.trim() || id, lang: $("#pLang").value, minutes: Number($("#pMinutes").value) || 2,
  } });
  loadProjects();
}

async function saveStory() {
  await api(`/api/projects/${state.current.id}`, { method: "PUT", body: { story: $("#story").value } });
}

// ---------- script editor ----------
const HOST_ID = "host", NARRATOR_ID = "narrator";

function select(field, value, values, labels) {
  const s = document.createElement("select");
  s.dataset.field = field;
  for (const v of values) {
    const [val, label] = Array.isArray(v) ? v : [v, labels?.[v] || v];
    s.add(new Option(label, val, false, val === value));
  }
  return s;
}
const sceneSelect = (field, value) => select(field, value, state.options[field + "s"], LABELS[field]);

function labeled(text, control) {
  const l = document.createElement("label");
  l.textContent = text;
  l.appendChild(control);
  return l;
}

function castNames() {
  return [[HOST_ID, "Người dẫn chuyện"], ...(state.script?.cast || []).map((c) => [c.id, c.name || c.id])];
}

function slugify(text) {
  return text.toLowerCase().replace(/đ/g, "d").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "nv";
}

function renderCast() {
  const box = $("#castList");
  box.innerHTML = "";
  $("#castEditor").classList.toggle("hidden", !state.script);
  if (!state.script) return;
  const cast = (state.script.cast ||= []);
  if (!cast.length) box.innerHTML = '<p class="muted">Chưa có nhân vật. Video chỉ có người dẫn chuyện.</p>';
  cast.forEach((c, i) => {
    const el = document.createElement("div");
    el.className = "cast-card";
    const img = document.createElement("img");
    img.alt = "";
    const refresh = () => (img.src = `/api/character-thumb?${new URLSearchParams({ preset: c.preset, outfit: c.outfit, accessory: c.accessory, kind: c.kind })}`);
    refresh();
    const fields = document.createElement("div");
    fields.className = "cast-fields";
    const name = document.createElement("input");
    name.value = c.name;
    name.dataset.field = "name";
    fields.append(
      labeled("Tên", name),
      labeled("Nhân vật", select("preset", c.preset, state.options.characters.map((x) => [x.id, x.label]))),
      labeled("Trang phục", select("outfit", c.outfit, state.options.outfits.map((x) => [x.id, x.label]))),
      labeled("Phụ kiện", select("accessory", c.accessory, state.options.accessories.map((x) => [x.id, x.label]))),
      labeled("Loại", select("kind", c.kind, state.options.kinds, LABELS.kind)),
    );
    const del = document.createElement("button");
    del.className = "btn ghost small danger";
    del.textContent = "Xóa";
    del.onclick = () => {
      const used = state.script.scenes.some((s) => s.actors.some((a) => a.id === c.id) || s.lines.some((l) => l.speaker === c.id));
      if (used && !confirm(`${c.name} đang có trong kịch bản. Xóa luôn khỏi các cảnh?`)) return;
      cast.splice(i, 1);
      for (const s of state.script.scenes) {
        s.actors = s.actors.filter((a) => a.id !== c.id);
        for (const l of s.lines) if (l.speaker === c.id) l.speaker = NARRATOR_ID;
      }
      state.dirty = true;
      renderScript();
    };
    el.addEventListener("change", (e) => {
      const f = e.target.dataset.field;
      if (!f) return;
      c[f] = e.target.value;
      state.dirty = true;
      if (f === "name") renderScenes(); else refresh();
    });
    el.append(img, fields, del);
    box.appendChild(el);
  });
}

function addCast() {
  const cast = (state.script.cast ||= []);
  const name = prompt("Tên nhân vật (ví dụ: Bà Tư, Ma da):");
  if (!name?.trim()) return;
  let id = slugify(name), n = 2;
  while (id === HOST_ID || id === NARRATOR_ID || cast.some((c) => c.id === id)) id = `${slugify(name)}_${n++}`;
  cast.push({ id, name: name.trim(), preset: state.options.characters[0].id, outfit: state.options.outfits[0].id,
    accessory: "none", kind: "human" });
  state.dirty = true;
  renderScript();
}

function renderScript() {
  const sc = state.script;
  $("#noScript").classList.toggle("hidden", !!sc);
  $("#sceneCount").textContent = sc ? `(${sc.scenes.length})` : "";
  $("#scriptTitle").value = sc?.title || "";
  $("#scriptTitle").disabled = !sc;
  $("#saveScriptBtn").disabled = !sc;
  renderCharacterEditor();
  renderCast();
  renderScenes();
}

function renderScenes() {
  const box = $("#scenes");
  box.innerHTML = "";
  const sc = state.script;
  if (!sc) return;
  const bgs = state.current.backgrounds || {};
  const who = castNames();
  sc.scenes.forEach((s, i) => {
    const el = document.createElement("div");
    el.className = "scene";
    el.innerHTML = `
      <div><div class="scene-no">${i + 1}</div>
        <div class="scene-tools">
          <button class="btn ghost small" data-act="up" title="Lên">↑</button>
          <button class="btn ghost small" data-act="down" title="Xuống">↓</button>
          <button class="btn ghost small danger" data-act="del" title="Xóa cảnh">✕</button>
        </div></div>
      <div class="scene-body">
        <div class="sub-head"><b>Lời thoại</b><button class="btn ghost small" data-act="add-line">+ Câu</button></div>
        <div class="lines"></div>
        <div class="sub-head"><b>Trên sân khấu</b><button class="btn ghost small" data-act="add-actor">+ Diễn viên</button></div>
        <div class="actors"></div>
        <div class="sub-head"><b>Đồ vật, con vật</b><button class="btn ghost small" data-act="add-prop">+ Đồ vật</button></div>
        <div class="props"></div>
        <div class="scene-bg">
          <label>Mã nền <input data-scene="bg_id" list="packBackgrounds"></label>
          <label>Mô tả nền (tiếng Anh) <input data-scene="bg_prompt"></label>
          <label class="cam"></label>
        </div>
      </div>
      <div class="scene-thumb"></div>`;
    $("[data-scene=bg_id]", el).value = s.bg_id;
    $("[data-scene=bg_prompt]", el).value = s.bg_prompt;
    const cam = sceneSelect("camera", s.camera);
    cam.dataset.scene = "camera";
    delete cam.dataset.field;
    $(".cam", el).replaceWith(labeled("Máy quay", cam));

    const lineBox = $(".lines", el);
    s.lines.forEach((ln, j) => {
      const row = document.createElement("div");
      row.className = "line-row";
      const speaker = select("speaker", ln.speaker, [[NARRATOR_ID, "Dẫn chuyện"], ...who.slice(1)]);
      const text = document.createElement("textarea");
      text.value = ln.text;
      text.rows = 2;
      text.dataset.field = "text";
      text.setAttribute("aria-label", "Lời thoại");
      const del = document.createElement("button");
      del.className = "btn ghost small danger";
      del.textContent = "✕";
      del.title = "Xóa câu";
      del.onclick = () => { if (s.lines.length > 1) { s.lines.splice(j, 1); state.dirty = true; renderScenes(); } };
      row.addEventListener("input", (e) => { ln[e.target.dataset.field] = e.target.value; state.dirty = true; });
      row.append(speaker, text, del);
      lineBox.appendChild(row);
    });

    const actorBox = $(".actors", el);
    if (!s.actors.length) actorBox.innerHTML = '<p class="muted small">Không ai trên sân khấu (chỉ có nền).</p>';
    s.actors.forEach((a, j) => {
      const row = document.createElement("div");
      row.className = "actor-row";
      row.append(
        select("id", a.id, who),
        sceneSelect("position", a.position), sceneSelect("pose", a.pose),
        sceneSelect("expression", a.expression), sceneSelect("action", a.action),
      );
      const del = document.createElement("button");
      del.className = "btn ghost small danger";
      del.textContent = "✕";
      del.title = "Bỏ khỏi cảnh";
      del.onclick = () => { s.actors.splice(j, 1); state.dirty = true; renderScenes(); };
      row.appendChild(del);
      row.addEventListener("change", (e) => {
        const f = e.target.dataset.field;
        if (f === "id" && s.actors.some((o, k) => k !== j && o.id === e.target.value)) {
          toast("Nhân vật này đã có trong cảnh", true);
          e.target.value = a.id;
          return;
        }
        a[f] = e.target.value;
        state.dirty = true;
      });
      actorBox.appendChild(row);
    });

    s.props = s.props || [];
    const propBox = $(".props", el);
    s.props.forEach((pr, j) => {
      const row = document.createElement("div");
      row.className = "prop-row";
      row.append(select("id", pr.id, state.options.props), sceneSelect("position", pr.position));
      const del = document.createElement("button");
      del.className = "btn ghost small danger";
      del.textContent = "✕";
      del.title = "Bỏ khỏi cảnh";
      del.onclick = () => { s.props.splice(j, 1); state.dirty = true; renderScenes(); };
      row.appendChild(del);
      row.addEventListener("change", (e) => { pr[e.target.dataset.field] = e.target.value; state.dirty = true; });
      propBox.appendChild(row);
    });

    const thumb = $(".scene-thumb", el);
    if (bgs[s.bg_id]) thumb.style.backgroundImage = `url("${bgs[s.bg_id]}")`;
    else thumb.textContent = "Ảnh nền tạo khi dựng video";
    el.addEventListener("input", (e) => {
      const f = e.target.dataset.scene;
      if (f) { s[f] = e.target.value; state.dirty = true; }
    });
    el.addEventListener("click", (e) => {
      const act = e.target.dataset.act;
      if (!act) return;
      const arr = sc.scenes;
      if (act === "del" && arr.length > 1) arr.splice(i, 1);
      if (act === "up" && i > 0) [arr[i - 1], arr[i]] = [arr[i], arr[i - 1]];
      if (act === "down" && i < arr.length - 1) [arr[i + 1], arr[i]] = [arr[i], arr[i + 1]];
      if (act === "add-line") s.lines.push({ speaker: s.actors.find((a) => a.id !== HOST_ID)?.id || NARRATOR_ID, text: "" });
      if (act === "add-prop") {
        if (s.props.length >= 3) return toast("Tối đa 3 đồ vật mỗi cảnh", true);
        const taken = new Set([...s.actors, ...s.props].map((a) => a.position));
        const pos = ["far_right", "far_left", "center", "right", "left"].find((p) => !taken.has(p)) || "far_right";
        s.props.push({ id: state.options.props[0][0], position: pos });
      }
      if (act === "add-actor") {
        const free = who.find(([id]) => !s.actors.some((a) => a.id === id));
        if (!free) return toast("Tất cả nhân vật đã có trong cảnh", true);
        const taken = new Set(s.actors.map((a) => a.position));
        const pos = state.options.positions.find((p) => !taken.has(p)) || "center";
        s.actors.push({ id: free[0], position: pos, pose: "idle", expression: "neutral", action: "none" });
      }
      state.dirty = true;
      renderScenes();
      $("#sceneCount").textContent = `(${sc.scenes.length})`;
    });
    box.appendChild(el);
  });
}

async function saveScript() {
  state.script.title = $("#scriptTitle").value;
  const p = await api(`/api/projects/${state.current.id}`, { method: "PUT", body: { script: state.script } });
  state.current = p;
  state.script = structuredClone(p.script);
  state.dirty = false;
  renderScript();
  loadProjects();
  toast("Đã lưu kịch bản");
}

// ---------- per-video character ----------
let videoPreviewSequence = 0;
let videoPreviewTimer;
const characterColorKeys = ["skin_color", "hair_color", "shirt_color", "outline_color"];
function renderCharacterEditor() {
  const sc = state.script;
  $("#characterEditor").classList.toggle("hidden", !sc);
  if (!sc) { ++videoPreviewSequence; return; }
  const choice = { ...state.options.default_character, ...sc.character };
  const palette = state.options.characters.find((item) => item.id === choice.preset)?.colors || choice;
  const outfitColor = state.options.outfits.find((item) => item.id === choice.outfit)?.color;
  const colors = { ...palette, ...(sc.character?.outfit ? { shirt_color: outfitColor } : {}), ...sc.character };
  for (const el of $$("[data-character]")) el.value = choice[el.dataset.character];
  const custom = characterColorKeys.some((key) => sc.character?.[key]);
  $("#customCharacterColors").checked = custom;
  $("#videoColors").classList.toggle("hidden", !custom);
  for (const el of $$("[data-character-color]")) el.value = colors[el.dataset.characterColor];
  previewVideoCharacter();
}
function updateVideoCharacter(event) {
  if (!state.script) return;
  const choice = {};
  for (const el of $$("[data-character]")) choice[el.dataset.character] = el.value;
  const custom = $("#customCharacterColors").checked;
  if (!custom || event?.target.id === "customCharacterColors") {
    const palette = state.options.characters.find((item) => item.id === choice.preset)?.colors || state.options.default_character;
    const outfitColor = state.options.outfits.find((item) => item.id === choice.outfit)?.color;
    for (const el of $$("[data-character-color]")) el.value = el.dataset.characterColor === "shirt_color" ? outfitColor : palette[el.dataset.characterColor];
  }
  $("#videoColors").classList.toggle("hidden", !custom);
  if (custom) for (const el of $$("[data-character-color]")) choice[el.dataset.characterColor] = el.value;
  state.script.character = choice;
  state.dirty = true;
  previewVideoCharacter();
}
function previewVideoCharacter() {
  clearTimeout(videoPreviewTimer);
  const sequence = ++videoPreviewSequence;
  const id = state.current?.id;
  const character = structuredClone(state.script?.character || {});
  $("#characterPreviewStatus").textContent = "Đang cập nhật hình xem trước…";
  videoPreviewTimer = setTimeout(run(async () => {
    try {
      const response = await fetch("/api/character-preview", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ character }),
      });
      if (!response.ok) throw new Error("Không thể xem trước nhân vật");
      const blob = await response.blob();
      if (sequence !== videoPreviewSequence || state.current?.id !== id) return;
      const img = $("#videoCharacterPreview");
      if (img.src.startsWith("blob:")) URL.revokeObjectURL(img.src);
      img.src = URL.createObjectURL(blob);
      $("#characterPreviewStatus").textContent = "Hàng trên: các tư thế · Hàng dưới: biểu cảm. Lưu kịch bản để giữ phiên bản này.";
    } catch (e) {
      if (sequence === videoPreviewSequence) $("#characterPreviewStatus").textContent = e.message;
    }
  }), 150);
}

// ---------- jobs ----------
function renderJob(st) {
  const bar = $("#jobBar");
  const s = st?.state;
  if (!s || s === "idle") { bar.classList.add("hidden"); return; }
  bar.classList.remove("hidden");
  bar.className = `jobbar ${s}`;
  const name = JOBS[st.kind] || "Tác vụ";
  $("#jobText").textContent = s === "running" ? `Đang ${name.toLowerCase()}…` : s === "done" ? `${name}: xong`
    : s === "failed" ? `${name}: lỗi. Xem nhật ký ở tab Video.` : `${name}: bị ngắt khi server khởi động lại`;
  $("#stopBtn").classList.toggle("hidden", s !== "running");
  const busy = s === "running";
  $("#writeScriptBtn").disabled = busy;
  $("#renderBtn").disabled = busy;
}

function startPolling() {
  clearInterval(state.poll);
  const id = state.current.id;
  state.poll = setInterval(run(async () => {
    if (state.current?.id !== id) return clearInterval(state.poll);
    const { status, log } = await api(`/api/projects/${id}/log`);
    $("#log").textContent = log;
    const pre = $("#log");
    pre.scrollTop = pre.scrollHeight;
    renderJob(status);
    if (status.state !== "running") {
      clearInterval(state.poll);
      if (status.state === "failed") { $("#logBox").open = true; toast("Tác vụ bị lỗi, xem nhật ký", true); }
      const keepDirty = state.dirty;
      const p = await api(`/api/projects/${id}`);
      state.current = p;
      if (!keepDirty) { state.script = p.script ? structuredClone(p.script) : null; renderScript(); }
      renderVideo();
      loadProjects();
      if (status.state === "done") {
        toast(status.kind === "script" ? "Đã viết xong kịch bản" : "Video đã dựng xong");
        selectTab(status.kind === "script" ? "script" : "video");
      }
    }
  }), 1500);
}

async function writeScript() {
  if (!$("#story").value.trim()) return toast("Chưa có nội dung truyện", true);
  if (state.script && !confirm("Viết lại sẽ thay kịch bản hiện tại. Tiếp tục?")) return;
  if (state.dirty && state.script) await saveScript();
  await saveMeta();
  await saveStory();
  const provider = $("#provider").value;
  renderJob(await api(`/api/projects/${state.current.id}/script`, { method: "POST", body: provider ? { provider } : {} }));
  $("#log").textContent = "";
  startPolling();
}

async function renderVideoJob() {
  if (state.dirty) await saveScript();
  await saveMeta();
  renderJob(await api(`/api/projects/${state.current.id}/render`, { method: "POST", body: { res: $("#res").value } }));
  $("#logBox").open = true;
  startPolling();
}

function renderVideo() {
  const p = state.current;
  const player = $("#player");
  const dl = $("#downloadBtn");
  if (p.has_video) {
    const src = `/files/${p.id}/video.mp4?v=${p.video_mtime}`;
    if (player.getAttribute("src") !== src) player.src = src;
    dl.href = src;
    dl.setAttribute("download", `${p.id}.mp4`);
  } else {
    player.removeAttribute("src");
  }
  player.classList.toggle("hidden", !p.has_video);
  dl.classList.toggle("hidden", !p.has_video);
  const strip = $("#bgStrip");
  strip.innerHTML = "";
  for (const [k, url] of Object.entries(p.backgrounds || {})) {
    const f = document.createElement("figure");
    f.innerHTML = `<img alt=""><figcaption></figcaption>`;
    f.querySelector("img").src = url;
    f.querySelector("figcaption").textContent = k;
    strip.appendChild(f);
  }
  api(`/api/projects/${p.id}/log`).then(({ log }) => ($("#log").textContent = log || "Chưa chạy lần nào."));
}

// ---------- settings ----------
async function openSettings() {
  if (state.dirty && !confirm("Kịch bản chưa lưu. Bỏ thay đổi?")) return;
  state.dirty = false;
  state.current = null;
  location.hash = "settings";
  loadProjects();
  const s = (state.settings = await api("/api/settings"));
  for (const el of $$("[data-env]")) el.value = s.env[el.dataset.env] ?? "";
  for (const el of $$("[data-secret]")) {
    el.textContent = s.env._secret_set[el.dataset.secret] ? "Đã lưu key (để trống = giữ nguyên)" : "";
  }
  for (const el of $$("[data-ch]")) el.value = s.channel[el.dataset.ch] ?? "";
  for (const el of $$("[data-host]")) el.value = s.channel.host?.[el.dataset.host] ?? "";
  const v = $("#voices");
  v.innerHTML = "";
  for (const [lang, voice] of Object.entries(s.channel.voices || {})) {
    const l = document.createElement("label");
    l.textContent = lang.toUpperCase();
    const i = document.createElement("input");
    i.dataset.voice = lang;
    i.value = voice;
    l.appendChild(i);
    v.appendChild(l);
  }
  $("#settingsMsg").textContent = "";
  show("settingsView");
  previewCharacter();
}

function collectChannel() {
  const ch = structuredClone(state.settings.channel);
  for (const el of $$("[data-ch]")) ch[el.dataset.ch] = el.value;
  ch.host = ch.host || {};
  for (const el of $$("[data-host]")) ch.host[el.dataset.host] = el.value;
  for (const el of $$("[data-voice]")) ch.voices[el.dataset.voice] = el.value.trim();
  return ch;
}

let previewTimer;
function previewCharacter() {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(run(async () => {
    const res = await fetch("/api/character-preview", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ host: collectChannel().host }),
    });
    if (!res.ok) return;
    const img = $("#charPreview");
    if (img.src.startsWith("blob:")) URL.revokeObjectURL(img.src);
    img.src = URL.createObjectURL(await res.blob());
  }), 200);
}

async function saveSettings() {
  const env = {};
  for (const el of $$("[data-env]")) env[el.dataset.env] = el.value;
  state.settings = await api("/api/settings", { method: "PUT", body: { env, channel: collectChannel() } });
  state.options = await api("/api/options");
  for (const el of $$("[data-env][type=password]")) el.value = "";
  for (const el of $$("[data-secret]")) {
    el.textContent = state.settings.env._secret_set[el.dataset.secret] ? "Đã lưu key (để trống = giữ nguyên)" : "";
  }
  $("#settingsMsg").textContent = "Đã lưu. Áp dụng cho lần chạy tiếp theo.";
  toast("Đã lưu cài đặt");
}

// ---------- wiring ----------
async function init() {
  state.options = await api("/api/options");
  for (const [id, list] of [["videoCharacter", "characters"], ["videoOutfit", "outfits"], ["videoAccessory", "accessories"]]) {
    for (const item of state.options[list]) $("#" + id).add(new Option(item.label, item.id));
  }
  for (const el of $$("[data-character], [data-character-color], #customCharacterColors")) el.addEventListener("change", updateVideoCharacter);
  const bgList = document.createElement("datalist");
  bgList.id = "packBackgrounds";
  for (const [id, label] of state.options.backgrounds) bgList.appendChild(new Option(label, id));
  document.body.appendChild(bgList);
  for (const sel of [$("#pLang"), $("#newLang")]) {
    for (const [k, v] of state.options.languages) sel.add(new Option(v, k));
  }
  $("#newProjectBtn").onclick = () => { $("#newForm").reset(); $("#newDialog").showModal(); };
  $("#newDialog").addEventListener("close", run(async () => {
    if ($("#newDialog").returnValue !== "ok") return;
    const f = new FormData($("#newForm"));
    const p = await api("/api/projects", { method: "POST", body: Object.fromEntries(f) });
    await openProject(p.id, "story");
  }));
  $("#settingsBtn").onclick = run(openSettings);
  $$(".tab").forEach((t) => (t.onclick = () => selectTab(t.dataset.tab)));
  $("#pName").onchange = run(saveMeta);
  $("#pLang").onchange = run(saveMeta);
  $("#pMinutes").onchange = run(saveMeta);
  $("#saveStoryBtn").onclick = run(async () => { await saveStory(); toast("Đã lưu truyện"); });
  $("#writeScriptBtn").onclick = run(writeScript);
  $("#saveScriptBtn").onclick = run(saveScript);
  $("#addSceneBtn").onclick = () => {
    if (!state.script) state.script = { title: $("#pName").value, cast: [], scenes: [] };
    const last = state.script.scenes.at(-1);
    state.script.scenes.push({ bg_id: last?.bg_id || "bg0", bg_prompt: last?.bg_prompt || "misty village at dusk",
      camera: "static", actors: structuredClone(last?.actors || [{ id: HOST_ID, position: "center", pose: "talk",
        expression: "neutral", action: "none" }]).map((a) => ({ ...a, action: "none" })),
      lines: [{ speaker: NARRATOR_ID, text: "" }] });
    state.dirty = true;
    renderScript();
  };
  $("#addCastBtn").onclick = addCast;
  $("#renderBtn").onclick = run(renderVideoJob);
  $("#stopBtn").onclick = run(() => api(`/api/projects/${state.current.id}/stop`, { method: "POST" }));
  $("#deleteBtn").onclick = run(async () => {
    if (!confirm(`Xóa dự án "${state.current.name}" và toàn bộ file của nó?`)) return;
    await api(`/api/projects/${state.current.id}`, { method: "DELETE" });
    state.current = null; state.dirty = false; location.hash = "";
    show("emptyView");
    loadProjects();
  });
  $("#saveSettingsBtn").onclick = run(saveSettings);
  $$("[data-host]").forEach((el) => el.addEventListener("input", previewCharacter));
  window.addEventListener("beforeunload", (e) => { if (state.dirty) e.preventDefault(); });

  await loadProjects();
  await route();
  window.addEventListener("hashchange", run(route));
}

async function route() {
  const h = location.hash.slice(1);
  if (h === "settings") { if ($("#settingsView").classList.contains("hidden")) await openSettings(); }
  else if (h && h !== state.current?.id && state.projects.some((p) => p.id === h)) await openProject(h);
}

run(init)();
