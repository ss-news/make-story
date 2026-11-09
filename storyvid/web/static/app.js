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
const JOBS = { script: "Viết kịch bản", render: "Dựng video", visuals_prompts: "Viết prompt hình",
  visuals_cast: "Tạo ảnh mẫu nhân vật", visuals_scenes: "Tạo ảnh và clip cảnh", style_samples: "Muse vẽ mẫu phong cách",
  script_review: "AI đánh giá kịch bản", script_revise: "AI sửa kịch bản", script_auto: "Đánh giá và sửa kịch bản",
  script_polish: "AI trau chuốt lời kể",
  finish_check: "Máy kiểm tra", finish_loudnorm: "Chuẩn hóa âm lượng", finish_review: "AI kiểm định",
  finish_publish: "Tạo gói đăng", auto: "Chạy tự động" };

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
      : p.published ? '<span class="badge video">đã đăng</span>'
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
  if (window.parent !== window) window.parent.postMessage({ type: "storyvid:project", id }, "*");  // MuseFlow's diagram
  state.musePage = 0;
  state.museFilter = "all";
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
  renderReview();
  $("#pGenre").value = p.meta.genre || "story";
  $("#pKeepText").checked = !!p.meta.keep_text;
  loadScriptReviews();
  loadFinish();
  await Promise.all([loadVisuals(), loadStyles(), loadVoices(), loadPlaces()]);
  checkMuse();
  renderJob(p.status);
  selectTab(tab || (!p.meta.style ? "style" : !p.script ? "story" : !p.approved ? "script"
    : p.has_video ? "video" : "muse"));
  loadProjects();
  if (p.status.state === "running") startPolling();
}

function selectTab(name) {
  try { sessionStorage.setItem("storyvid.tab", name); } catch {}
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
  renderStoryboard();
  renderScenes();
}

// ---------- storyboard (storyvid/storyboard.py): treatment above the scenes, a shot on each scene ----------
const textKey = (lines) => ((lines || []).map((l) => l.text || "").join(" ").toLowerCase()
  .match(/[\p{L}\p{N}_]+/gu) || []).join(" ");

function sceneShots() {
  const board = state.current?.storyboard;
  const scenes = state.script?.scenes || [];
  if (!board) return scenes.map(() => null);
  const pool = {};
  for (const shot of board.shots || []) (pool[shot.key] ||= []).push(shot);
  return scenes.map((s) => pool[textKey(s.lines)]?.shift() || null);
}

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
}

function renderStoryboard() {
  const box = $("#storyboardCard");
  const board = state.current?.storyboard;
  box.innerHTML = "";
  box.classList.toggle("hidden", !board || !state.script);
  if (!board || !state.script) return;
  const head = el("div", "sb-head");
  head.append(el("h2", "", "Storyboard"), el("p", "sb-logline", board.logline || ""));
  box.appendChild(head);
  const facts = el("dl", "sb-facts");
  for (const [k, label] of [["want", "Muốn"], ["obstacle", "Cản trở"], ["stakes", "Cái giá"], ["theme", "Chủ đề"]]) {
    if (!board[k]) continue;
    facts.append(el("dt", "", label), el("dd", "", board[k]));
  }
  if (board.cold_open?.question) facts.append(el("dt", "", "Câu hỏi mở đầu"), el("dd", "", board.cold_open.question));
  box.appendChild(facts);
  const beats = el("ol", "sb-beats");
  for (const b of board.beats || []) {
    const li = el("li");
    li.append(el("b", "", board.beat_labels?.[b.beat] || b.beat), el("span", "", ` ${b.summary || ""}`),
      el("span", "muted small", b.seconds ? ` · ${b.seconds}s` : ""));
    beats.appendChild(li);
  }
  box.appendChild(beats);
  const shots = sceneShots();
  const missing = shots.filter((s) => !s).length;
  if (missing) box.appendChild(el("p", "muted small",
    `${missing} cảnh đã sửa sau khi lập storyboard nên không còn ghi chú shot; prompt hình của các cảnh đó dựa theo kịch bản.`));
}

function shotStrip(shot, board) {
  const wrap = el("div", "shot");
  if (shot.first) {
    const film = el("div", "shot-scene");
    film.append(el("b", "", shot.slug || ""), el("span", "beat", board.beat_labels?.[shot.beat] || shot.beat));
    for (const [k, v] of [["Nối từ cảnh trước", shot.bridge], ["Bối cảnh", shot.setting], ["Mục đích", shot.purpose],
      ["Xung đột", shot.conflict], ["Bước ngoặt", shot.turn]]) {
      if (v) film.appendChild(el("div", "small", `${k}: ${v}`));
    }
    wrap.appendChild(film);
  }
  const tags = el("div", "shot-tags");
  if (shot.link) tags.appendChild(el("span", `tag link-${shot.link}`, board.links?.[shot.link] || shot.link));
  tags.append(el("span", "tag", shot.size), el("span", "tag", board.angles?.[shot.angle] || shot.angle),
    el("span", "tag", board.moves?.[shot.movement] || shot.movement));
  if (shot.transition && shot.transition !== "cut") tags.appendChild(el("span", "tag", shot.transition.replace("_", " ")));
  wrap.appendChild(tags);
  if (shot.description) wrap.appendChild(el("div", "shot-action", shot.description));
  for (const [k, v] of [["Hành động", shot.action], ["Diễn xuất", shot.performance], ["Khung cuối", shot.end_frame]]) {
    if (v) wrap.appendChild(el("div", "muted small", `${k}: ${v}`));
  }
  const extra = [shot.composition, shot.sound && `♪ ${shot.sound}`].filter(Boolean).join(" · ");
  if (extra) wrap.appendChild(el("div", "muted small", extra));
  if (shot.transition_note) wrap.appendChild(el("div", "shot-next small", `→ ${shot.transition_note}`));
  return wrap;
}

function renderScenes() {
  const box = $("#scenes");
  box.innerHTML = "";
  const sc = state.script;
  if (!sc) return;
  const bgs = state.current.backgrounds || {};
  const who = castNames();
  const shots = sceneShots();
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
    if (shots[i]) $(".scene-body", el).prepend(shotStrip(shots[i], state.current.storyboard));
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
  renderReview();
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
  $("#renderShortBtn").disabled = busy;
  for (const id of ["autoBtn", "approveCastBtn", "musePromptsBtn", "museCastBtn", "museImagesBtn", "museClipsBtn", "museSaveBtn", "approveBtn",
    "sampleStylesBtn", "sampleCustomBtn", "reviewBtn", "reviseBtn", "autoReviewBtn", "finishCheckBtn", "loudnormBtn",
  "finishReviewBtn", "finishShortBtn", "finishPublishBtn"]) $("#" + id).disabled = busy;
  $$(".muse-redo").forEach((b) => (b.disabled = busy));
  museSteps(busy);
}

// Steps 1-4 of the Muse tab open one after another; the next step to do is the highlighted one.
function museSteps(busy = state.jobRunning) {
  if (!state.current) return;
  state.jobRunning = busy;
  const v = state.visuals, approved = !!state.current.approved;
  const castDone = !!v && v.cast.every((c) => c.sheet), castOk = castDone && !!state.current.cast_approved;
  const images = v ? v.scenes.filter((s) => s.image).length : 0;
  const steps = [
    ["musePromptsBtn", approved, !!v, "Bấm “1. Viết prompt hình”, hoặc “▶ Chạy tự động”."],
    ["museCastBtn", !!v, castDone, "Bấm “2. Ảnh mẫu nhân vật”, hoặc “▶ Chạy tự động”."],
    ["approveCastBtn", castDone, castOk, "Xem ảnh mẫu từng nhân vật (sửa mô tả và tạo lại nếu chưa ưng), rồi bấm “✓ Duyệt nhân vật”."],
    ["museImagesBtn", castOk, !!v && images === v.scenes.length, "Bấm “▶ Chạy tự động” để làm hết ảnh, clip và video, hoặc “3. Ảnh các cảnh”."],
    ["museClipsBtn", images > 0, false, "Bấm “4. Clip từ ảnh”."],
  ];
  const next = steps.find(([, open, done]) => open && !done);
  for (const [id, open] of steps) {
    $("#" + id).disabled = busy || !open;
    $("#" + id).classList.toggle("primary", next?.[0] === id);
  }
  $("#approveCastBtn").classList.toggle("hidden", !castDone || castOk);
  $("#autoBtn").disabled = busy || !approved || (castDone && !castOk);
  $("#museNext").textContent = !approved ? "Duyệt kịch bản ở tab 3 trước." : next ? `Bước tiếp theo: ${next[3]}` : "";
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
    if ((status.kind?.startsWith("visuals_") || status.kind === "auto") && !state.visualsDirty) await loadVisuals();  // show progress
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
        const muse = status.kind?.startsWith("visuals_") || (status.kind === "auto" && !p.has_video);
        if (status.kind === "auto") await loadFinish();
        toast(muse || status.kind === "style_samples" ? `${JOBS[status.kind]}: xong`
          : status.kind === "auto" && !p.cast_approved ? "Ảnh mẫu nhân vật đã xong: xem rồi bấm “Duyệt nhân vật”"
          : status.kind === "script" ? "Đã viết xong kịch bản. Đọc kỹ rồi bấm Duyệt" : "Video đã dựng xong");
        if (status.kind === "style_samples") await loadStyles();
        if (status.kind?.startsWith("script")) await loadScriptReviews();
        if (status.kind?.startsWith("finish") || status.kind === "render") await loadFinish();
        renderReview();
        if (status.kind === "script_polish") { $("#story").value = state.current.story; }
        selectTab(status.kind === "style_samples" ? "style" : muse ? "muse" : status.kind === "script_polish" ? "story"
          : status.kind?.startsWith("script") ? "script"
          : status.kind?.startsWith("finish") ? "finish" : "video");
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

async function renderVideoJob(short = false) {
  if (state.dirty) await saveScript();
  await saveMeta();
  renderJob(await api(`/api/projects/${state.current.id}/render`, { method: "POST",
    body: { res: $("#res").value, short, visuals: $("#useMuse").checked } }));
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
  const shortPlayer = $("#shortPlayer");
  const shortDl = $("#downloadShortBtn");
  if (p.short_mtime) {
    const src = `/files/${p.id}/video_short.mp4?v=${p.short_mtime}`;
    if (shortPlayer.getAttribute("src") !== src) shortPlayer.src = src;
    shortDl.href = src;
    shortDl.setAttribute("download", `${p.id}_short.mp4`);
  } else {
    shortPlayer.removeAttribute("src");
  }
  shortPlayer.classList.toggle("hidden", !p.short_mtime);
  shortDl.classList.toggle("hidden", !p.short_mtime);
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

// ---------- project flow: style, review, voice ----------
async function saveProjectField(body) {
  state.current = await api(`/api/projects/${state.current.id}`, { method: "PUT", body });
  return state.current;
}

async function loadStyles() {
  state.styles = await api(`/api/projects/${state.current.id}/styles`);
  renderStyles();
}

function renderStyles() {
  const chosen = state.current.meta.style || {};
  $("#pRatio").value = state.current.meta.ratio || "9:16";
  const list = $("#styleList");
  list.innerHTML = "";
  for (const s of state.styles || []) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "style-card" + (chosen.preset === s.id ? " selected" : "");
    card.innerHTML = s.sample ? `<img alt="">` : `<div class="ph">Chưa có mẫu</div>`;
    if (s.sample) card.querySelector("img").src = s.sample;
    card.insertAdjacentHTML("beforeend", "<strong></strong><small></small>");
    card.querySelector("strong").textContent = s.label;
    card.querySelector("small").textContent = s.about;
    card.onclick = run(() => chooseStyle(s.id));
    list.appendChild(card);
  }
  $("#customStyleBox").classList.toggle("hidden", chosen.preset !== "custom");
  if (!state.customStyleDirty) $("#customStyle").value = chosen.preset === "custom" ? chosen.text || "" : "";
  const label = (state.styles || []).find((s) => s.id === chosen.preset)?.label;
  $("#styleChosen").textContent = label ? `Đã chọn: ${label}` : "Chưa chọn phong cách";
}

async function chooseStyle(preset) {
  const style = { preset, text: preset === "custom" ? $("#customStyle").value.trim() : "" };
  await saveProjectField({ style });
  state.customStyleDirty = false;
  renderStyles();
}

async function sampleStyles(body) {
  renderJob(await api(`/api/projects/${state.current.id}/styles/sample`, { method: "POST", body }));
  $("#log").textContent = "";
  startPolling();
  toast("Muse đang vẽ mẫu, mỗi kiểu khoảng 30 giây");
}

function renderStoryLangNote() {
  const lang = state.options.languages.find(([k]) => k === $("#pLang").value)?.[1] || $("#pLang").value;
  $("#storyLangNote").textContent = `Kịch bản, giọng đọc và phụ đề sẽ bằng ${lang}; truyện gốc ngôn ngữ nào cũng được.`;
}

function renderReview() {
  const p = state.current;
  renderStoryLangNote();
  const bar = $("#reviewBar");
  bar.classList.toggle("hidden", !p.script);
  bar.classList.toggle("ok", !!p.approved);
  $("#reviewText").textContent = p.approved
    ? "✓ Đã duyệt. Sửa kịch bản sẽ phải duyệt lại."
    : "Đọc kỹ toàn bộ kịch bản, sửa nếu cần, rồi duyệt. Các bước AI tạo hình chỉ mở sau khi duyệt.";
  $("#approveBtn").classList.toggle("hidden", !!p.approved);
  $("#museLocked").classList.toggle("hidden", !!p.approved);
  $('[data-pane="muse"]').classList.toggle("gated", !p.approved);
}

async function approveScript() {
  if (state.dirty) await saveScript();
  if (!confirm("Bạn đã đọc hết kịch bản và đồng ý cho bắt đầu bước AI tạo hình?")) return;
  state.current = await api(`/api/projects/${state.current.id}/approve`, { method: "POST" });
  renderReview();
  museSteps();
  toast("Đã duyệt kịch bản");
  selectTab("muse");
}

async function loadVoices() {
  state.voices = await api(`/api/voices?lang=${state.current.lang}`);
  const sel = $("#voiceProvider");
  sel.innerHTML = "";
  for (const p of state.voices.providers) sel.add(new Option(p.label, p.id));
  const chosen = state.current.meta.voice || {};
  sel.value = state.voices.providers.some((p) => p.id === chosen.provider) ? chosen.provider
    : state.voices.providers.some((p) => p.id === state.voices.default) ? state.voices.default : "edge";
  fillVoiceNames(chosen.voice);
}

function fillVoiceNames(selected) {
  const p = state.voices.providers.find((x) => x.id === $("#voiceProvider").value);
  const sel = $("#voiceName");
  sel.innerHTML = "";
  const named = (p?.voices || []).filter((v) => typeof v === "object");
  $("#voiceNameBox").classList.toggle("hidden", !named.length);
  for (const v of named) sel.add(new Option(v.label, v.id));
  if (selected && named.some((v) => v.id === selected)) sel.value = selected;
  $("#voicePreviewBtn").classList.toggle("hidden", p?.id === "elevenlabs");
}

async function saveVoice() {
  const voice = { provider: $("#voiceProvider").value, voice: $("#voiceNameBox").classList.contains("hidden") ? "" : $("#voiceName").value };
  await saveProjectField({ voice });
}

async function previewVoice() {
  const provider = $("#voiceProvider").value;
  toast(provider === "vieneu" ? "Đang đọc thử (lần đầu nạp model mất khoảng 10 giây)…" : "Đang đọc thử…");
  const r = await fetch("/api/voice-preview", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, voice: $("#voiceName").value, lang: state.current.lang }) });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || "Không đọc thử được");
  new Audio(URL.createObjectURL(await r.blob())).play();
}

// ---------- script review rounds ----------
async function loadScriptReviews() {
  const { rounds } = await api(`/api/projects/${state.current.id}/script-reviews`);
  const box = $("#reviewRounds");
  if (!rounds.length) return;
  box.innerHTML = "";
  for (const r of [...rounds].reverse()) {
    const el = document.createElement("div");
    el.className = "review-round";
    const when = new Date(r.at * 1000).toLocaleString("vi-VN");
    if (r.kind === "polish") {
      el.innerHTML = `<div></div><div class="crit"></div><div class="issues"></div>`;
      el.firstElementChild.textContent = `Vòng ${r.round} · AI trau chuốt lời kể (${r.provider}): ${r.words_before} → ${r.words_after} từ`
        + `${r.kept_parts.length ? `, giữ nguyên ${r.kept_parts.length}/${r.parts} đoạn để không mất sự thật` : ""} · bản trước lưu ở ${r.backup} · ${when}`;
      const crit = el.querySelector(".crit");
      for (const c of r.criteria) crit.insertAdjacentHTML("beforeend", `<b>${c.score}/10</b><span></span>`), (crit.lastElementChild.textContent = `${c.label}: ${c.comment}`);
      for (const n of r.notes) { const d = document.createElement("div"); d.className = "issue"; d.textContent = `• ${n}`; el.querySelector(".issues").appendChild(d); }
    } else if (r.kind === "revise") {
      el.textContent = `Vòng ${r.round} · AI sửa (${r.provider}) theo vòng ${r.from_round}: viết lại ${r.changed_scenes.length} cảnh, `
        + `${r.scenes_before} → ${r.scenes_after} cảnh · bản trước lưu ở ${r.backup} · ${when}`;
    } else {
      el.innerHTML = `<div>Vòng ${r.round} · AI đánh giá (${r.provider}) · ${when}</div>
        <span class="score ${r.verdict}"></span> <span></span><div class="crit"></div><div class="issues"></div>`;
      el.querySelector(".score").textContent = `${r.score}/100`;
      el.querySelector(".score + span").textContent = (r.verdict === "pass" ? "Đạt. " : "Cần sửa. ") + (r.summary || "");
      const crit = el.querySelector(".crit");
      for (const c of r.criteria) crit.insertAdjacentHTML("beforeend", `<b>${c.score}/10</b><span></span>`), (crit.lastElementChild.textContent = `${c.label}: ${c.comment}`);
      const issues = el.querySelector(".issues");
      for (const i of r.issues) {
        const row = document.createElement("div");
        row.className = "issue";
        row.innerHTML = `<span class="sev ${i.severity}">${i.severity === "major" ? "Nặng" : "Nhẹ"}</span>`;
        if (i.scene !== null) {
          const a = document.createElement("a");
          a.textContent = `Cảnh ${i.scene + 1}`;
          a.onclick = () => { const s = $$("#scenes .scene")[i.scene]; s?.scrollIntoView({ behavior: "smooth", block: "center" }); s?.classList.add("flash"); setTimeout(() => s?.classList.remove("flash"), 1500); };
          row.append(a, ": ");
        } else row.append("Cả video: ");
        row.append(`${i.problem} → ${i.fix}`);
        issues.appendChild(row);
      }
    }
    box.appendChild(el);
  }
}

async function runScriptReview(action) {
  if (state.dirty) await saveScript();
  if (action !== "review" && !confirm("AI sẽ viết lại các cảnh bị nêu lỗi (bản trước được lưu lại) và bỏ duyệt. Tiếp tục?")) return;
  renderJob(await api(`/api/projects/${state.current.id}/script-review`, { method: "POST",
    body: { action, provider: $("#reviewProvider").value, rounds: 2 } }));
  $("#log").textContent = "";
  startPolling();
}

// ---------- finishing ----------
const PUBLISH_CHECKLIST = [
  ["thumb", "Chọn thumbnail: một chủ thể to, chữ tối đa 3–4 từ, khớp với hình trong video"],
  ["hd", "Tải bản 1080p gốc (video.mp4), không dùng bản nén"],
  ["srt", "Tải phụ đề video.srt"],
  ["kids", "Đối tượng: không dành cho trẻ em"],
  ["desc", "Dán mô tả có chương, ghi nguồn và ghi chú AI; kiểm chứng số liệu trong mô tả"],
  ["short", "Short (nếu có): công khai, gắn Related video về bản dài"],
  ["playlist", "Thêm vào playlist; màn hình kết thúc trỏ video khác"],
  ["after48", "Sau 48 giờ: ghi CTR, thời lượng xem, nguồn đề xuất vào docs/research/"],
];

async function loadFinish() {
  state.finish = await api(`/api/projects/${state.current.id}/finish`);
  renderFinish();
}

function renderFinish() {
  const f = state.finish || {}, meta = state.current.meta || {};
  const which = $("#finishVideo").value || "video";
  const chk = (f.finish || {})[`check_${which}`];
  const box = $("#finishChecks");
  if (chk) {
    box.innerHTML = "";
    for (const c of chk.checks) {
      const row = document.createElement("div");
      row.className = "check-row";
      row.innerHTML = `<span class="${c.ok ? "ok" : "bad"}">${c.ok ? "✓" : "✗"}</span><span></span>`;
      row.lastElementChild.textContent = `${c.label}: ${c.detail}`;
      box.appendChild(row);
    }
    box.insertAdjacentHTML("afterbegin", `<b>${chk.ok ? "Đạt" : "Chưa đạt"}</b> · ${new Date(chk.at * 1000).toLocaleString("vi-VN")}`);
  }
  const rv = f.review, flagged = new Set((rv?.issues || []).filter((i) => i.scene !== null).map((i) => i.scene));
  const rbox = $("#finishReview");
  if (rv) {
    rbox.innerHTML = `<b>${rv.verdict === "pass" ? "Đạt" : "Cần sửa"}</b> · ${rv.issues.length} vấn đề. Bấm số cảnh để tới cảnh đó ở tab Hình Muse và tạo lại.`;
    for (const i of rv.issues) {
      const row = document.createElement("div");
      row.className = "issue";
      row.innerHTML = `<span class="sev ${i.severity === "minor" ? "" : "major"}">${i.severity === "minor" ? "Nhẹ" : "Nặng"}</span>`;
      if (i.scene !== null) {
        const a = document.createElement("a");
        a.textContent = `Cảnh ${i.scene + 1}`;
        a.onclick = () => { selectTab("muse"); const s = $$("#museScenes .scene")[i.scene]; s?.scrollIntoView({ block: "center" }); s?.classList.add("flash"); setTimeout(() => s?.classList.remove("flash"), 1500); };
        row.append(a, ": ");
      } else row.append("Cả video: ");
      row.append(`${i.problem} → ${i.fix}`);
      rbox.appendChild(row);
    }
  }
  const frames = $("#finishFrames");
  frames.innerHTML = "";
  for (const [idx, url] of Object.entries(f.frames || {})) {
    const fig = document.createElement("figure");
    if (flagged.has(Number(idx))) fig.className = "flag";
    fig.innerHTML = `<img alt="" loading="lazy"><figcaption>${Number(idx) + 1}</figcaption>`;
    fig.querySelector("img").src = url;
    frames.appendChild(fig);
  }
  if (document.activeElement !== $("#finishCredits")) $("#finishCredits").value = meta.credits || "";
  const pub = f.publish, pbox = $("#finishPublish");
  if (pub) {
    pbox.innerHTML = "";
    const block = (label, text, rows) => {
      const l = document.createElement("label");
      l.className = "block";
      l.innerHTML = `<span></span><textarea rows="${rows}" readonly></textarea><button class="btn small" type="button">Copy</button>`;
      l.firstElementChild.textContent = label;
      l.querySelector("textarea").value = text;
      l.querySelector("button").onclick = () => { navigator.clipboard.writeText(text); toast("Đã copy"); };
      pbox.appendChild(l);
    };
    pub.titles.forEach((t, k) => block(`Tiêu đề ${k + 1}`, t, 1));
    block("Mô tả", pub.description, 10);
    block("Tags", pub.tags.join(", "), 2);
    const thumbs = document.createElement("div");
    thumbs.className = "thumbs";
    for (const t of pub.thumbnails) {
      const a = document.createElement("a");
      a.href = `/files/${state.current.id}/${t.file}`;
      a.download = t.file.split("/").pop();
      a.innerHTML = `<img alt="">`;
      a.querySelector("img").src = `/files/${state.current.id}/${t.file}?v=${Date.now() % 1e7}`;
      thumbs.appendChild(a);
    }
    pbox.appendChild(thumbs);
  }
  const done = meta.publish_checklist || {};
  const cl = $("#finishChecklist");
  cl.innerHTML = "";
  for (const [key, label] of PUBLISH_CHECKLIST) {
    const l = document.createElement("label");
    l.innerHTML = `<input type="checkbox"><span></span>`;
    l.lastElementChild.textContent = label;
    const box = l.querySelector("input");
    box.checked = !!done[key];
    box.onchange = run(() => saveProjectField({ publish_checklist: { ...(state.current.meta.publish_checklist || {}), [key]: box.checked } }));
    cl.appendChild(l);
  }
  $("#pubLong").value = meta.published?.long || "";
  $("#pubShort").value = meta.published?.short || "";
  $("#publishedNote").textContent = meta.published ? `Đã đăng ${new Date(meta.published.at * 1000).toLocaleString("vi-VN")}.` : "";
  const steps = [chk?.ok, rv?.verdict === "pass", !!pub, !!meta.published].filter(Boolean).length;
  $("#finishCount").textContent = steps ? `${steps}/4` : "";
}

async function runFinish(step) {
  if (step === "publish") await saveProjectField({ credits: $("#finishCredits").value });
  renderJob(await api(`/api/projects/${state.current.id}/finish/${step}`, { method: "POST",
    body: { video: $("#finishVideo").value, provider: $("#finishProvider").value } }));
  $("#log").textContent = "";
  startPolling();
}

// ---------- Muse visuals ----------
async function checkMuse() {
  const box = $(".muse-status");
  try {
    const st = await api("/api/muse/status");
    box.classList.toggle("ok", st.running && st.ready > 0);
    $("#museStatus").textContent = !st.running ? "MuseFlow chưa chạy. Mở nó bằng: cd museflow && npm start"
      : st.ready ? `MuseFlow: ${st.ready}/${st.accounts.length} tài khoản Muse sẵn sàng`
      : "MuseFlow đang chạy nhưng chưa có tài khoản Muse nào đăng nhập (mở Accounts trong MuseFlow)";
  } catch (e) { $("#museStatus").textContent = e.message; }
}

async function loadVisuals() {
  state.visuals = await api(`/api/projects/${state.current.id}/visuals`);
  state.visualsDirty = false;
  renderMuse();
}

const museUrl = (file) => `/files/${state.current.id}/${file}?v=${state.visuals?._files?.[file] ?? 0}`;
const MUSE_PAGE = 12;
const MUSE_FILTERS = {
  all: ["Tất cả cảnh", () => true],
  todo: ["Chưa có ảnh", (s) => !s.image],
  noclip: ["Có ảnh, chưa có clip", (s) => s.image && !s.clip],
  error: ["Có lỗi", (s) => !!s.error],
  done: ["Đã có clip", (s) => !!s.clip],
};

function musePager(total, pages) {
  const bar = document.createElement("div");
  bar.className = "actions muse-pager";
  bar.innerHTML = `<label class="inline">Lọc <select></select></label><span class="muted small"></span><span class="grow"></span>
    <button class="btn small" data-p="prev">‹ Trước</button><span class="small page-no"></span>
    <button class="btn small" data-p="next">Sau ›</button>`;
  const sel = bar.querySelector("select");
  for (const [k, [label]] of Object.entries(MUSE_FILTERS)) sel.add(new Option(label, k));
  sel.value = state.museFilter;
  sel.onchange = () => { state.museFilter = sel.value; state.musePage = 0; renderMuse(); };
  bar.querySelector(".muted").textContent = `${total} cảnh`;
  bar.querySelector(".page-no").textContent = `Trang ${state.musePage + 1}/${pages}`;
  bar.querySelector('[data-p="prev"]').disabled = state.musePage === 0;
  bar.querySelector('[data-p="next"]').disabled = state.musePage >= pages - 1;
  bar.querySelector('[data-p="prev"]').onclick = () => { state.musePage--; renderMuse(); $("#museScenes").scrollIntoView(); };
  bar.querySelector('[data-p="next"]').onclick = () => { state.musePage++; renderMuse(); $("#museScenes").scrollIntoView(); };
  return bar;
}

function renderMuse() {
  const v = state.visuals, script = state.current.script;
  $("#museEmpty").classList.toggle("hidden", !!v);
  $("#museBody").classList.toggle("hidden", !v);
  const clips = v ? v.scenes.filter((s) => s.clip).length : 0;
  $("#museCount").textContent = v ? `${clips}/${v.scenes.length}` : "";
  $("#useMuse").checked = !!v && clips > 0;
  museSteps();
  if (!v) return;
  $("#museStyle").value = v.style;
  $("#museContinuity").value = v.continuity || "auto";
  $("#museContinuity").onchange = (e) => { v.continuity = e.target.value; state.visualsDirty = true; renderMuse(); };
  const mode = v.continuity || "auto", sc = script?.scenes || [];
  const linkedTo = (i) => i > 0 && (mode === "all" || (mode === "auto" && sc[i]?.bg_id === sc[i - 1]?.bg_id));
  $("#museStyle").oninput = (e) => { v.style = e.target.value; state.visualsDirty = true; };
  const names = Object.fromEntries((script?.cast || []).map((c) => [c.id, c.name]));
  names[HOST_ID] = state.settings?.channel?.host?.name || "Người dẫn";
  const cast = $("#museCast");
  cast.innerHTML = "";
  for (const c of v.cast) {
    const card = document.createElement("div");
    card.className = "muse-card";
    card.innerHTML = `<strong></strong><textarea></textarea><div class="muse-media"></div><div class="muse-error"></div>
      <button class="btn small muse-redo"></button>`;
    card.querySelector("strong").textContent = names[c.id] || c.id;
    const look = card.querySelector("textarea");
    look.value = c.look;
    look.oninput = () => { c.look = look.value; state.visualsDirty = true; };
    if (c.sheet) card.querySelector(".muse-media").innerHTML = `<img alt="" src="${museUrl(c.sheet)}">`;
    card.querySelector(".muse-error").textContent = c.error || "";
    const redo = card.querySelector("button");
    redo.textContent = c.sheet ? "↻ Tạo lại ảnh mẫu" : "▶ Tạo ảnh mẫu";
    redo.onclick = run(() => runVisuals("cast", { only: c.id, redo: true }));
    cast.appendChild(card);
  }
  const list = $("#museScenes");
  list.innerHTML = "";
  state.museFilter ??= "all";
  state.musePage ??= 0;
  const keep = MUSE_FILTERS[state.museFilter]?.[1] || (() => true);
  const shown = v.scenes.map((sc, i) => [sc, i]).filter(([sc]) => keep(sc));
  const pages = Math.max(1, Math.ceil(shown.length / MUSE_PAGE));
  state.musePage = Math.min(state.musePage, pages - 1);
  list.appendChild(musePager(shown.length, pages));
  shown.slice(state.musePage * MUSE_PAGE, (state.musePage + 1) * MUSE_PAGE).forEach(([sc, i]) => {
    const el = document.createElement("div");
    el.className = "scene muse-scene";
    const narration = (script?.scenes[i]?.lines || []).map((l) => l.text).join(" ");
    el.innerHTML = `<div><b>${i + 1}</b></div>
      <div class="muse-prompts"><p class="muted small"></p>
        <label class="block">Ảnh mở cảnh<textarea data-k="image_prompt"></textarea></label>
        <label class="block">Chuyển động (clip)<textarea data-k="video_prompt"></textarea></label>
        <div class="muse-error"></div></div>
      <div class="muse-media"><div class="files"></div>
        <button class="btn small muse-redo" data-redo="clip">↻ Tạo lại clip</button>
        <button class="btn small muse-redo" data-redo="all">↻ Tạo lại ảnh + clip</button></div>`;
    el.querySelector("p").textContent = (linkedTo(i) ? `⛓ nối tiếp từ khung cuối cảnh ${i} · ` : "") + narration;
    for (const ta of el.querySelectorAll("textarea")) {
      ta.value = sc[ta.dataset.k];
      ta.oninput = () => { sc[ta.dataset.k] = ta.value; state.visualsDirty = true; };
    }
    el.querySelector(".muse-error").textContent = sc.error || "";
    const files = el.querySelector(".files");
    if (sc.clip) files.innerHTML = `<video controls muted preload="metadata" src="${museUrl(sc.clip)}"></video>`;
    else if (sc.image) files.innerHTML = `<img alt="" src="${museUrl(sc.image)}">`;
    else files.innerHTML = `<p class="muted small">Chưa tạo</p>`;
    el.querySelector('[data-redo="clip"]').disabled = !sc.image;
    el.querySelector('[data-redo="clip"]').onclick = run(async () => {
      sc.clip = ""; state.visualsDirty = true;  // keep the image, make only a new clip
      await runVisuals("scenes", { only: i });
    });
    el.querySelector('[data-redo="all"]').onclick = run(() => runVisuals("scenes", { only: i, redo: true }));
    list.appendChild(el);
  });
  if (shown.length > MUSE_PAGE) list.appendChild(musePager(shown.length, pages));
}

// ---------- real places (refs/places.json) ----------
async function loadPlaces() {
  renderPlaces((await api(`/api/projects/${state.current.id}/places`)).places);
}

async function uploadPhotos(place, files) {
  const form = new FormData();
  for (const f of files) form.append("photos", f);
  const res = await fetch(`/api/projects/${state.current.id}/places/${place.id}/photos`, { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error || `Lỗi ${res.status}`);
  renderPlaces(data.places);
}

function renderPlaces(places) {
  const list = $("#placesList"), base = `/api/projects/${state.current.id}/places`;
  list.innerHTML = places.length ? "" : `<p class="muted small">Chưa có địa điểm nào.</p>`;
  for (const p of places) {
    const el = document.createElement("div");
    el.className = "place";
    el.innerHTML = `<div class="place-fields">
        <label>Tên<input data-k="name"></label>
        <label>Từ khóa (tiếng Anh, cách nhau dấu phẩy)<input data-k="keywords" placeholder="house, gate, yard"></label>
        <label>Luôn dùng ở cảnh<input data-k="scenes" placeholder="3, 7"></label>
        <label>Không dùng ở cảnh<input data-k="skip" placeholder="12"></label>
      </div>
      <p class="muted small place-used"></p>
      <div class="place-photos"></div>
      <div class="actions">
        <label class="btn small place-upload">＋ Ảnh từ máy<input type="file" accept="image/*" multiple hidden></label>
        <input class="place-url" placeholder="hoặc dán link ảnh https://…">
        <button class="btn small" data-act="url">Tải về</button>
        <span class="grow"></span>
        <button class="btn small" data-act="save">Lưu</button>
        <button class="btn small ghost" data-act="delete">Xóa địa điểm</button>
      </div>`;
    const field = (k) => el.querySelector(`[data-k="${k}"]`);
    field("name").value = p.name;
    field("keywords").value = p.keywords.join(", ");
    field("scenes").value = p.scenes.join(", ");
    field("skip").value = p.skip.join(", ");
    el.querySelector(".place-used").textContent = !p.files.length ? "Chưa có ảnh: thêm ít nhất một ảnh."
      : p.used_in.length ? `Gửi kèm ảnh đầu tiên ở ${p.used_in.length} cảnh: ${p.used_in.join(", ")}`
      : "Chưa khớp cảnh nào: thêm từ khóa có trong mô tả nền, hoặc ghi số cảnh.";
    const photos = el.querySelector(".place-photos");
    p.files.forEach((file, k) => {
      const fig = document.createElement("figure");
      fig.innerHTML = `<img alt=""><figcaption></figcaption><button class="btn small ghost" title="Xóa ảnh">×</button>`;
      fig.querySelector("img").src = `/files/${state.current.id}/${file}`;
      fig.querySelector("figcaption").textContent = (k === 0 ? "★ " : "") + file.split("/").pop();
      fig.querySelector("button").onclick = run(async () => {
        if (!confirm("Xóa ảnh này?")) return;
        const name = file.split("/").slice(2).join("/");
        renderPlaces((await api(`${base}/${p.id}/photos/${encodeURIComponent(name)}`, { method: "DELETE" })).places);
      });
      photos.appendChild(fig);
    });
    const picker = el.querySelector('input[type="file"]');
    picker.onchange = run(async () => { if (picker.files.length) await uploadPhotos(p, picker.files); });
    el.ondragover = (e) => { e.preventDefault(); el.classList.add("drop"); };
    el.ondragleave = () => el.classList.remove("drop");
    el.ondrop = run(async (e) => {
      e.preventDefault(); el.classList.remove("drop");
      const files = [...e.dataTransfer.files].filter((f) => f.type.startsWith("image/"));
      if (files.length) await uploadPhotos(p, files);
    });
    el.querySelector('[data-act="url"]').onclick = run(async () => {
      const url = el.querySelector(".place-url").value.trim();
      if (!url) return toast("Dán link ảnh trước", true);
      renderPlaces((await api(`${base}/${p.id}/photos`, { method: "POST", body: { url } })).places);
      toast("Đã tải ảnh về");
    });
    el.querySelector('[data-act="save"]').onclick = run(async () => {
      const body = Object.fromEntries(["name", "keywords", "scenes", "skip"].map((k) => [k, field(k).value]));
      renderPlaces((await api(`${base}/${p.id}`, { method: "PUT", body })).places);
      toast("Đã lưu địa điểm");
    });
    el.querySelector('[data-act="delete"]').onclick = run(async () => {
      if (!confirm(`Xóa địa điểm “${p.name}” và ảnh của nó?`)) return;
      renderPlaces((await api(`${base}/${p.id}`, { method: "DELETE" })).places);
    });
    list.appendChild(el);
  }
}

async function saveVisuals() {
  if (!state.visuals) return;
  await api(`/api/projects/${state.current.id}/visuals`, { method: "PUT", body: state.visuals });
  state.visualsDirty = false;
}

async function runVisuals(step, body = {}) {
  if (step !== "prompts") await saveVisuals();
  else if (state.visuals && !confirm("Viết lại prompt? Ảnh và clip của cảnh có prompt không đổi được giữ lại.")) return;
  if (state.dirty) await saveScript();
  renderJob(await api(`/api/projects/${state.current.id}/visuals/${step}`, { method: "POST", body }));
  $("#log").textContent = "";
  startPolling();
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
// MuseFlow (the desktop app around this page) asks to show a project's tab when a diagram step is clicked.
window.addEventListener("message", run(async (e) => {
  if (e.source !== window.parent || e.data?.type !== "storyvid:open") return;
  const { id, tab } = e.data;
  if (!/^[a-z0-9_]+$/.test(id || "")) return;
  if (state.current?.id !== id) await openProject(id, tab);
  else if (tab) selectTab(tab);
}));

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
    await openProject(p.id, "style");
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
  $("#renderBtn").onclick = run(() => renderVideoJob(false));
  $("#renderShortBtn").onclick = run(() => renderVideoJob(true));
  $("#museCheckBtn").onclick = run(checkMuse);
  $("#approveCastBtn").onclick = run(async () => {
    await saveVisuals();
    if (!confirm("Bạn đã xem ảnh mẫu của mọi nhân vật và đồng ý dùng chúng cho tất cả các cảnh?")) return;
    state.current = await api(`/api/projects/${state.current.id}/approve-cast`, { method: "POST" });
    museSteps();
    toast("Đã duyệt nhân vật");
  });
  $("#autoBtn").onclick = run(async () => {
    await saveVisuals();
    if (state.dirty) await saveScript();
    renderJob(await api(`/api/projects/${state.current.id}/auto`, { method: "POST",
      body: { res: "1080", provider: $("#museProvider").value } }));  // 1080p: the finish checks need it
    $("#log").textContent = "";
    startPolling();
  });
  $("#placeAddBtn").onclick = run(async () => {
    const name = $("#placeName").value.trim();
    if (!name) return toast("Nhập tên địa điểm", true);
    renderPlaces((await api(`/api/projects/${state.current.id}/places`, { method: "POST", body: { name } })).places);
    $("#placeName").value = "";
  });
  $("#musePromptsBtn").onclick = run(() => runVisuals("prompts", { provider: $("#museProvider").value, ratio: state.current.meta.ratio }));
  $("#museSaveBtn").onclick = run(async () => { await saveVisuals(); toast("Đã lưu prompt hình"); });
  $("#museCastBtn").onclick = run(() => runVisuals("cast"));
  $("#museImagesBtn").onclick = run(() => runVisuals("scenes", { images_only: true }));
  $("#museClipsBtn").onclick = run(() => runVisuals("scenes", { clips_only: true }));
  $("#museLaunchBtn").onclick = run(async () => {
    const r = await api("/api/muse/launch", { method: "POST" });
    toast(r.started ? "Đang mở MuseFlow… đăng nhập Muse trong cửa sổ Accounts nếu chưa có tài khoản" : "MuseFlow đang chạy");
    setTimeout(checkMuse, 8000);
  });
  $("#approveBtn").onclick = run(approveScript);
  $("#finishCheckBtn").onclick = run(() => runFinish("check"));
  $("#loudnormBtn").onclick = run(() => runFinish("loudnorm"));
  $("#finishReviewBtn").onclick = run(() => runFinish("review"));
  $("#finishPublishBtn").onclick = run(() => runFinish("publish"));
  $("#finishShortBtn").onclick = run(() => renderVideoJob(true));
  $("#finishVideo").onchange = renderFinish;
  $("#finishCredits").onchange = run(() => saveProjectField({ credits: $("#finishCredits").value }));
  $("#publishedBtn").onclick = run(async () => {
    if (!$("#pubLong").value.trim()) return toast("Dán link video đã đăng", true);
    await saveProjectField({ published: { long: $("#pubLong").value.trim(), short: $("#pubShort").value.trim() } });
    renderFinish(); loadProjects(); toast("Đã đánh dấu đã đăng");
  });
  $("#reviewBtn").onclick = run(() => runScriptReview("review"));
  $("#polishBtn").onclick = run(async () => {
    if (!$("#story").value.trim()) return toast("Chưa có lời kể", true);
    if (!confirm("Muse sẽ đánh giá và viết lại lời kể một lượt (bản cũ được lưu lại). Tiếp tục?")) return;
    await saveStory();
    renderJob(await api(`/api/projects/${state.current.id}/script-review`, { method: "POST",
      body: { action: "polish", provider: $("#reviewProvider").value } }));
    $("#log").textContent = "";
    startPolling();
  });
  $("#reviseBtn").onclick = run(() => runScriptReview("revise"));
  $("#autoReviewBtn").onclick = run(() => runScriptReview("auto"));
  $("#pGenre").onchange = run(() => saveProjectField({ genre: $("#pGenre").value }));
  $("#pKeepText").onchange = run(() => saveProjectField({ keep_text: $("#pKeepText").checked }));
  $("#sampleStylesBtn").onclick = run(() => sampleStyles({}));
  $("#sampleCustomBtn").onclick = run(async () => { await chooseStyle("custom"); await sampleStyles({ preset: "custom", redo: true }); });
  $("#customStyle").oninput = () => { state.customStyleDirty = true; };
  $("#pRatio").onchange = run(async () => { await saveProjectField({ ratio: $("#pRatio").value }); });
  $("#styleNextBtn").onclick = run(async () => {
    if ($("#customStyleBox").classList.contains("hidden") === false) await chooseStyle("custom");
    if (!state.current.meta.style) return toast("Chọn một phong cách trước", true);
    selectTab("story");
  });
  $("#voiceProvider").onchange = run(async () => { fillVoiceNames(); await saveVoice(); });
  $("#voiceName").onchange = run(saveVoice);
  $("#voicePreviewBtn").onclick = run(previewVoice);
  $("#pLang").addEventListener("change", run(async () => { await saveMeta(); await loadVoices(); renderStoryLangNote(); }));
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
  let tab = null;
  try { tab = sessionStorage.getItem("storyvid.reloadTab"); sessionStorage.setItem("storyvid.reloadTab", ""); } catch {}
  await route(tab);
  window.addEventListener("hashchange", run(() => route()));
  watchLive();
}

// ---------- live reload: newer files on disk (a job, an agent, another window) or a restarted server ----------
const LIVE_MS = 3000;
function watchLive() {
  let seen = null, warned = false, busy = false;
  setInterval(async () => {
    if (busy || document.hidden) return;
    busy = true;
    try {
      const live = await api("/api/live");
      const now = `${live.boot}|${live.ui}`;
      if (seen && now !== seen) {  // new server or new page code: reload, back on the same project and tab
        if (state.dirty || state.visualsDirty) {
          if (!warned) toast("App vừa cập nhật. Lưu thay đổi rồi tải lại trang để dùng bản mới.");
          warned = true;
        } else {
          try { sessionStorage.setItem("storyvid.reloadTab", sessionStorage.getItem("storyvid.tab") || ""); } catch {}
          location.reload();
          return;
        }
      }
      seen ||= now;
      await refreshIfChanged();
    } catch { /* server restarting: try again next tick */ }
    finally { busy = false; }
  }, LIVE_MS);
}

async function refreshIfChanged() {
  const cur = state.current;
  if (!cur || (state.poll && cur.status?.state === "running")) return;  // a running job refreshes the page itself
  const { stamp } = await api(`/api/projects/${cur.id}/stamp`);
  if (!cur.stamp || stamp <= cur.stamp || state.current?.id !== cur.id) return;
  const p = await api(`/api/projects/${cur.id}`);
  if (state.current?.id !== cur.id) return;
  state.current = p;
  if (!state.dirty) {
    state.script = p.script ? structuredClone(p.script) : null;
    $("#story").value = p.story;
    renderScript();
  } else {
    toast("Kịch bản trên đĩa vừa đổi; bạn đang có thay đổi chưa lưu nên trang chưa tải lại.");
  }
  renderVideo();
  renderReview();
  renderJob(p.status);
  loadScriptReviews();
  loadFinish();
  if (!state.visualsDirty) await loadVisuals();
  loadProjects();
}

async function route(tab) {
  const h = location.hash.slice(1);
  if (h === "settings") { if ($("#settingsView").classList.contains("hidden")) await openSettings(); }
  else if (h && h !== state.current?.id && state.projects.some((p) => p.id === h)) await openProject(h, tab || undefined);
}

run(init)();
