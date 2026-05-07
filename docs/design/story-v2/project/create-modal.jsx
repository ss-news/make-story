// CreateModal — universal "Create new" modal with 3 tabs: Event / Character / Arc

function CreateModal({ open, initialTab, prefill, onClose, onCreated }) {
  const [tab, setTab] = useState(initialTab || 'event');
  useEffect(() => { if (open) setTab(initialTab || 'event'); }, [open, initialTab]);

  if (!open) return null;

  return (
    <div className="cm-backdrop" onClick={onClose}>
      <div className={classNames('cm-modal', tab === 'project' && 'wide')} onClick={e => e.stopPropagation()} role="dialog">
        <div className="cm-head">
          <div className="cm-tabs">
            <button className={classNames('cm-tab', tab === 'project' && 'on')} onClick={() => setTab('project')}>
              <span className="cm-tab-icon">❖</span> Dự án
            </button>
            <span className="cm-tab-sep"/>
            <button className={classNames('cm-tab', tab === 'event' && 'on')} onClick={() => setTab('event')}>
              <span className="cm-tab-icon">◆</span> Event
            </button>
            <button className={classNames('cm-tab', tab === 'character' && 'on')} onClick={() => setTab('character')}>
              <span className="cm-tab-icon">◉</span> Nhân vật
            </button>
            <button className={classNames('cm-tab', tab === 'arc' && 'on')} onClick={() => setTab('arc')}>
              <span className="cm-tab-icon">▱</span> Arc
            </button>
          </div>
          <button className="cm-close" onClick={onClose}>×</button>
        </div>

        {tab === 'project' && <ProjectForm prefill={prefill} onCancel={onClose} onCreated={(id) => onCreated && onCreated('project', id)}/>}
        {tab === 'event' && <EventForm prefill={prefill} onCancel={onClose} onCreated={(id) => onCreated && onCreated('event', id)}/>}
        {tab === 'character' && <CharacterForm prefill={prefill} onCancel={onClose} onCreated={(id) => onCreated && onCreated('character', id)}/>}
        {tab === 'arc' && <ArcForm prefill={prefill} onCancel={onClose} onCreated={(id) => onCreated && onCreated('arc', id)}/>}
      </div>
    </div>
  );
}

// ───────────── Event Form ─────────────
function EventForm({ prefill = {}, onCancel, onCreated }) {
  const [f, setF] = useState({
    title: '',
    description: '',
    arc_id: prefill.arc_id || window.SEED.arcs[0].id,
    chapter_id: prefill.chapter_id || window.SEED.chapters[0].id,
    type: 'plot',
    importance: 'major',
    is_turning: false,
    is_crossover: false,
    story_time: '',
    characters: [],
    upstream: [],
    downstream: [],
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [aiBusy, setAiBusy] = useState(null);

  const set = (k, v) => setF(s => ({ ...s, [k]: v }));
  const toggleChar = (cid) => set('characters', f.characters.includes(cid) ? f.characters.filter(x => x !== cid) : [...f.characters, cid]);
  const toggleLink = (key, eid) => set(key, f[key].includes(eid) ? f[key].filter(x => x !== eid) : [...f[key], eid]);

  function aiSuggest(field) {
    setAiBusy(field);
    setTimeout(() => {
      if (field === 'description') set('description', 'Sự kiện diễn ra trong bối cảnh căng thẳng, nhân vật phải đối mặt với lựa chọn khó khăn. Kết quả định hình diễn biến chương kế tiếp.');
      if (field === 'story_time') set('story_time', 'Năm 2, tháng ' + (Math.floor(Math.random() * 6) + 1));
      setAiBusy(null);
    }, 600);
  }

  function submit() {
    if (!f.title.trim()) return;
    const id = 'e-new-' + Date.now();
    onCreated(id);
  }

  const arc = getArc(f.arc_id);
  const validChapters = window.SEED.chapters.filter(c => !arc || (c.order >= arc.chapter_start && c.order <= arc.chapter_end));

  return (
    <div className="cm-body">
      <div className="cm-scroll">
        <div className="cm-section">
          <label className="cm-lbl">Tiêu đề <span className="req">*</span></label>
          <input className="cm-input lg" value={f.title} onChange={e => set('title', e.target.value)} placeholder="VD: Lý Thanh Vân đột phá Trúc Cơ" autoFocus/>
        </div>

        <div className="cm-row-2">
          <div className="cm-section">
            <label className="cm-lbl">Arc <span className="req">*</span></label>
            <select className="cm-input" value={f.arc_id} onChange={e => set('arc_id', e.target.value)}>
              {window.SEED.storylines.map(sl => (
                <optgroup key={sl.id} label={sl.name}>
                  {window.SEED.arcs.filter(a => a.storyline_id === sl.id).map(a => (
                    <option key={a.id} value={a.id}>{a.name} (CH {a.chapter_start}–{a.chapter_end})</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
          <div className="cm-section">
            <label className="cm-lbl">Chương <span className="req">*</span></label>
            <select className="cm-input" value={f.chapter_id} onChange={e => set('chapter_id', e.target.value)}>
              {validChapters.map(c => <option key={c.id} value={c.id}>CH {c.order} — {c.title.replace(/^Chương \d+: /, '')}</option>)}
            </select>
          </div>
        </div>

        <div className="cm-section">
          <div className="cm-lbl-row">
            <label className="cm-lbl">Mô tả</label>
            <button className="cm-ai" onClick={() => aiSuggest('description')} disabled={aiBusy === 'description'}>
              {aiBusy === 'description' ? '✦ đang nghĩ…' : '✦ AI gợi ý'}
            </button>
          </div>
          <textarea className="cm-input" rows={3} value={f.description} onChange={e => set('description', e.target.value)} placeholder="Tóm tắt diễn biến chính của event…"/>
        </div>

        <div className="cm-row-2">
          <div className="cm-section">
            <label className="cm-lbl">Loại</label>
            <div className="cm-seg">
              {['plot', 'character', 'world'].map(v => (
                <button key={v} className={classNames('cm-seg-btn', f.type === v && 'on')} onClick={() => set('type', v)}>{v}</button>
              ))}
            </div>
          </div>
          <div className="cm-section">
            <label className="cm-lbl">Mức độ</label>
            <div className="cm-seg">
              {['major', 'minor'].map(v => (
                <button key={v} className={classNames('cm-seg-btn', f.importance === v && 'on')} onClick={() => set('importance', v)}>{v}</button>
              ))}
            </div>
          </div>
        </div>

        <div className="cm-section">
          <label className="cm-lbl">Cờ đặc biệt</label>
          <div className="cm-flags">
            <label className="cm-check">
              <input type="checkbox" checked={f.is_turning} onChange={e => set('is_turning', e.target.checked)}/>
              <span className="cm-flag-icon turning">★</span> Turning point — bước ngoặt cốt truyện
            </label>
            <label className="cm-check">
              <input type="checkbox" checked={f.is_crossover} onChange={e => set('is_crossover', e.target.checked)}/>
              <span className="cm-flag-icon crossover">⇄</span> Crossover — giao thoa giữa các tuyến
            </label>
          </div>
        </div>

        <div className="cm-section">
          <label className="cm-lbl">Nhân vật tham gia <span className="muted">({f.characters.length})</span></label>
          <div className="cm-char-pick">
            {window.SEED.characters.map(c => {
              const on = f.characters.includes(c.id);
              return (
                <button
                  key={c.id}
                  className={classNames('cm-char-pill', on && 'on')}
                  onClick={() => toggleChar(c.id)}
                  style={on ? { borderColor: c.color, color: c.color, background: 'var(--paper)' } : null}
                >
                  <span className="cm-pchip-avatar" style={{ borderColor: c.color, color: c.color }}>{initials(c.name)}</span>
                  {c.name}
                  {on && <span className="cm-check-icon">✓</span>}
                </button>
              );
            })}
          </div>
        </div>

        <button className="cm-toggle-adv" onClick={() => setShowAdvanced(s => !s)}>
          <span>{showAdvanced ? '▾' : '▸'}</span> Chi tiết bổ sung (causality, thời gian truyện)
        </button>

        {showAdvanced && (
          <div className="cm-adv">
            <div className="cm-section">
              <div className="cm-lbl-row">
                <label className="cm-lbl">Thời gian truyện</label>
                <button className="cm-ai" onClick={() => aiSuggest('story_time')} disabled={aiBusy === 'story_time'}>
                  {aiBusy === 'story_time' ? '✦…' : '✦ AI'}
                </button>
              </div>
              <input className="cm-input" value={f.story_time} onChange={e => set('story_time', e.target.value)} placeholder="VD: Năm 2, tháng 4"/>
            </div>

            <div className="cm-section">
              <label className="cm-lbl">Nguyên nhân (upstream events) <span className="muted">({f.upstream.length})</span></label>
              <div className="cm-event-pick">
                {window.SEED.events.slice(0, 8).map(e => {
                  const on = f.upstream.includes(e.id);
                  return (
                    <button key={e.id} className={classNames('cm-event-pill', on && 'on')} onClick={() => toggleLink('upstream', e.id)}>
                      <span className="muted">{e.id}</span> {e.title}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="cm-section">
              <label className="cm-lbl">Hệ quả (downstream events) <span className="muted">({f.downstream.length})</span></label>
              <div className="cm-event-pick">
                {window.SEED.events.slice(8).map(e => {
                  const on = f.downstream.includes(e.id);
                  return (
                    <button key={e.id} className={classNames('cm-event-pill', on && 'on')} onClick={() => toggleLink('downstream', e.id)}>
                      <span className="muted">{e.id}</span> {e.title}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="cm-foot">
        <button className="btn ghost" onClick={onCancel}>Hủy (Esc)</button>
        <div style={{ flex: 1 }}/>
        <button className="btn">Lưu nháp</button>
        <button className="btn accent" onClick={submit} disabled={!f.title.trim()}>Tạo event ⌘↵</button>
      </div>
    </div>
  );
}

// ───────────── Character Form ─────────────
function CharacterForm({ prefill = {}, onCancel, onCreated }) {
  const colors = [
    'oklch(58% 0.12 30)', 'oklch(48% 0.10 250)', 'oklch(70% 0.10 350)',
    'oklch(55% 0.10 150)', 'oklch(45% 0.13 340)', 'oklch(60% 0.13 60)',
    'oklch(60% 0.06 200)', 'oklch(70% 0.04 80)',
  ];
  const [f, setF] = useState({
    name: '',
    aliases: [],
    aliasInput: '',
    role: 'Nam phụ',
    faction: '',
    tags: [],
    tagInput: '',
    color: colors[0],
    home_storyline_id: prefill.storyline_id || window.SEED.storylines[0].id,
    appearance: '',
    personality: '',
    life_status: 'alive',
    first_chap: 1,
  });
  const [aiBusy, setAiBusy] = useState(null);
  const [showAdv, setShowAdv] = useState(false);

  const set = (k, v) => setF(s => ({ ...s, [k]: v }));

  function addTag(key, inputKey) {
    const v = f[inputKey].trim();
    if (!v) return;
    if (f[key].includes(v)) return set(inputKey, '');
    setF(s => ({ ...s, [key]: [...s[key], v], [inputKey]: '' }));
  }
  function removeTag(key, t) { set(key, f[key].filter(x => x !== t)); }

  function aiSuggest(field) {
    setAiBusy(field);
    setTimeout(() => {
      if (field === 'aliases') set('aliases', [...f.aliases, 'tiểu tử', 'thiếu hiệp']);
      if (field === 'appearance') set('appearance', 'Tóc đen dài tới vai, mắt sáng, dáng người gầy nhưng săn chắc. Mặc áo xanh đậm, đeo kiếm bên hông trái.');
      if (field === 'personality') set('personality', 'Trầm tĩnh, ít nói, trọng tình nghĩa. Khi cần ra tay thì quyết đoán không khoan nhượng. Ngầm tự tôn cao.');
      if (field === 'tags') set('tags', [...f.tags, 'kiếm sĩ', 'tu tiên']);
      setAiBusy(null);
    }, 600);
  }

  function submit() {
    if (!f.name.trim()) return;
    const id = 'c-new-' + Date.now();
    onCreated(id);
  }

  return (
    <div className="cm-body">
      <div className="cm-scroll">
        <div className="cm-section">
          <label className="cm-lbl">Tên nhân vật <span className="req">*</span></label>
          <input className="cm-input lg" value={f.name} onChange={e => set('name', e.target.value)} placeholder="VD: Lý Thanh Vân" autoFocus/>
        </div>

        <div className="cm-row-2">
          <div className="cm-section">
            <label className="cm-lbl">Vai trò</label>
            <select className="cm-input" value={f.role} onChange={e => set('role', e.target.value)}>
              {['Nam chính', 'Nữ chính', 'Nam phụ', 'Nữ phụ', 'Hỗ trợ', 'Phản diện chính', 'Phản diện phụ', 'NPC'].map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div className="cm-section">
            <label className="cm-lbl">Phe / Tổ chức</label>
            <input className="cm-input" value={f.faction} onChange={e => set('faction', e.target.value)} placeholder="VD: Thanh Vân Phái"/>
          </div>
        </div>

        <div className="cm-row-2">
          <div className="cm-section">
            <label className="cm-lbl">Thuộc tuyến</label>
            <select className="cm-input" value={f.home_storyline_id} onChange={e => set('home_storyline_id', e.target.value)}>
              {window.SEED.storylines.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="cm-section">
            <label className="cm-lbl">Màu nhận diện</label>
            <div className="cm-color-row">
              {colors.map(c => (
                <button
                  key={c}
                  className={classNames('cm-swatch', f.color === c && 'on')}
                  style={{ background: c }}
                  onClick={() => set('color', c)}
                  title={c}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="cm-section">
          <div className="cm-lbl-row">
            <label className="cm-lbl">Biệt danh / Cách gọi <span className="muted">({f.aliases.length})</span></label>
            <button className="cm-ai" onClick={() => aiSuggest('aliases')} disabled={aiBusy === 'aliases'}>
              {aiBusy === 'aliases' ? '✦…' : '✦ AI'}
            </button>
          </div>
          <div className="cm-tag-input">
            {f.aliases.map(a => (
              <span key={a} className="cm-tag-chip">
                {a}
                <button onClick={() => removeTag('aliases', a)}>×</button>
              </span>
            ))}
            <input
              className="cm-tag-text"
              value={f.aliasInput}
              onChange={e => set('aliasInput', e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag('aliases', 'aliasInput'); } }}
              placeholder='Nhấn Enter để thêm'
            />
          </div>
        </div>

        <div className="cm-section">
          <div className="cm-lbl-row">
            <label className="cm-lbl">Tags <span className="muted">({f.tags.length})</span></label>
            <button className="cm-ai" onClick={() => aiSuggest('tags')} disabled={aiBusy === 'tags'}>
              {aiBusy === 'tags' ? '✦…' : '✦ AI'}
            </button>
          </div>
          <div className="cm-tag-input">
            {f.tags.map(t => (
              <span key={t} className="cm-tag-chip">
                {t}
                <button onClick={() => removeTag('tags', t)}>×</button>
              </span>
            ))}
            <input
              className="cm-tag-text"
              value={f.tagInput}
              onChange={e => set('tagInput', e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag('tags', 'tagInput'); } }}
              placeholder='kiếm sĩ, tu tiên, …'
            />
          </div>
        </div>

        <div className="cm-section">
          <div className="cm-lbl-row">
            <label className="cm-lbl">Ngoại hình</label>
            <button className="cm-ai" onClick={() => aiSuggest('appearance')} disabled={aiBusy === 'appearance'}>
              {aiBusy === 'appearance' ? '✦ đang nghĩ…' : '✦ AI gợi ý'}
            </button>
          </div>
          <textarea className="cm-input" rows={3} value={f.appearance} onChange={e => set('appearance', e.target.value)} placeholder="Tóc, mắt, vóc dáng, trang phục…"/>
        </div>

        <div className="cm-section">
          <div className="cm-lbl-row">
            <label className="cm-lbl">Tính cách</label>
            <button className="cm-ai" onClick={() => aiSuggest('personality')} disabled={aiBusy === 'personality'}>
              {aiBusy === 'personality' ? '✦ đang nghĩ…' : '✦ AI gợi ý'}
            </button>
          </div>
          <textarea className="cm-input" rows={3} value={f.personality} onChange={e => set('personality', e.target.value)} placeholder="Tính cách, động cơ, điểm yếu…"/>
        </div>

        <button className="cm-toggle-adv" onClick={() => setShowAdv(s => !s)}>
          <span>{showAdv ? '▾' : '▸'}</span> Chi tiết bổ sung
        </button>
        {showAdv && (
          <div className="cm-adv">
            <div className="cm-row-2">
              <div className="cm-section">
                <label className="cm-lbl">Trạng thái</label>
                <div className="cm-seg">
                  {[['alive', 'còn sống'], ['deceased', 'đã mất'], ['unknown', 'không rõ']].map(([v, l]) => (
                    <button key={v} className={classNames('cm-seg-btn', f.life_status === v && 'on')} onClick={() => set('life_status', v)}>{l}</button>
                  ))}
                </div>
              </div>
              <div className="cm-section">
                <label className="cm-lbl">Xuất hiện lần đầu (chương)</label>
                <input className="cm-input" type="number" min={1} max={50} value={f.first_chap} onChange={e => set('first_chap', parseInt(e.target.value) || 1)}/>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="cm-foot">
        <button className="btn ghost" onClick={onCancel}>Hủy</button>
        <div style={{ flex: 1 }}/>
        <button className="btn">Lưu nháp</button>
        <button className="btn accent" onClick={submit} disabled={!f.name.trim()}>Tạo nhân vật ⌘↵</button>
      </div>
    </div>
  );
}

// ───────────── Arc Form ─────────────
function ArcForm({ prefill = {}, onCancel, onCreated }) {
  const [f, setF] = useState({
    name: '',
    storyline_id: prefill.storyline_id || window.SEED.storylines[0].id,
    order: 1,
    goal: '',
    setting: '',
    chapter_start: 1,
    chapter_end: 5,
    status: 'planned',
    closing_event_id: '',
  });
  const [aiBusy, setAiBusy] = useState(null);
  const set = (k, v) => setF(s => ({ ...s, [k]: v }));

  function aiSuggest(field) {
    setAiBusy(field);
    setTimeout(() => {
      if (field === 'goal') set('goal', 'Đạt cảnh giới Kim Đan, tìm được kỳ duyên đầu tiên');
      if (field === 'setting') set('setting', 'Thanh Vân Sơn — đỉnh núi quanh năm phủ mây trắng');
      setAiBusy(null);
    }, 500);
  }

  function submit() {
    if (!f.name.trim()) return;
    const id = 'a-new-' + Date.now();
    onCreated(id);
  }

  const sl = getStoryline(f.storyline_id);

  return (
    <div className="cm-body">
      <div className="cm-scroll">
        <div className="cm-section">
          <label className="cm-lbl">Tên Arc <span className="req">*</span></label>
          <input className="cm-input lg" value={f.name} onChange={e => set('name', e.target.value)} placeholder="VD: Bí cảnh thượng cổ" autoFocus/>
        </div>

        <div className="cm-row-2">
          <div className="cm-section">
            <label className="cm-lbl">Tuyến truyện <span className="req">*</span></label>
            <select className="cm-input" value={f.storyline_id} onChange={e => set('storyline_id', e.target.value)} style={{ borderLeft: '3px solid ' + (sl ? sl.color : 'var(--accent)') }}>
              {window.SEED.storylines.map(s => <option key={s.id} value={s.id}>{s.name} {s.is_main ? '(main)' : ''}</option>)}
            </select>
          </div>
          <div className="cm-section">
            <label className="cm-lbl">Thứ tự trong tuyến</label>
            <input className="cm-input" type="number" min={1} value={f.order} onChange={e => set('order', parseInt(e.target.value) || 1)}/>
          </div>
        </div>

        <div className="cm-section">
          <div className="cm-lbl-row">
            <label className="cm-lbl">Mục tiêu của Arc</label>
            <button className="cm-ai" onClick={() => aiSuggest('goal')} disabled={aiBusy === 'goal'}>
              {aiBusy === 'goal' ? '✦…' : '✦ AI'}
            </button>
          </div>
          <input className="cm-input" value={f.goal} onChange={e => set('goal', e.target.value)} placeholder="Nhân vật chính đạt được điều gì?"/>
        </div>

        <div className="cm-section">
          <div className="cm-lbl-row">
            <label className="cm-lbl">Bối cảnh</label>
            <button className="cm-ai" onClick={() => aiSuggest('setting')} disabled={aiBusy === 'setting'}>
              {aiBusy === 'setting' ? '✦…' : '✦ AI'}
            </button>
          </div>
          <input className="cm-input" value={f.setting} onChange={e => set('setting', e.target.value)} placeholder="VD: Thanh Vân Sơn"/>
        </div>

        <div className="cm-section">
          <label className="cm-lbl">Phạm vi chương</label>
          <div className="cm-range">
            <input className="cm-input cm-range-input" type="number" min={1} max={200} value={f.chapter_start} onChange={e => set('chapter_start', parseInt(e.target.value) || 1)}/>
            <span className="cm-range-sep">→</span>
            <input className="cm-input cm-range-input" type="number" min={1} max={200} value={f.chapter_end} onChange={e => set('chapter_end', parseInt(e.target.value) || 1)}/>
            <span className="muted" style={{ fontSize: 11, marginLeft: 8 }}>{Math.max(0, f.chapter_end - f.chapter_start + 1)} chương</span>
          </div>
          <div className="cm-range-bar">
            <div className="cm-range-track">
              <div className="cm-range-fill" style={{
                left: ((f.chapter_start - 1) / 40 * 100) + '%',
                width: ((f.chapter_end - f.chapter_start + 1) / 40 * 100) + '%',
                background: sl ? sl.color : 'var(--accent)'
              }}/>
            </div>
            <div className="cm-range-ticks">
              {[1, 10, 20, 30, 40].map(n => <span key={n} style={{ left: ((n - 1) / 40 * 100) + '%' }}>{n}</span>)}
            </div>
          </div>
        </div>

        <div className="cm-section">
          <label className="cm-lbl">Trạng thái</label>
          <div className="cm-seg">
            {[['planned', '○ planned'], ['drafting', '◐ drafting'], ['completed', '● completed']].map(([v, l]) => (
              <button key={v} className={classNames('cm-seg-btn', f.status === v && 'on')} onClick={() => set('status', v)}>{l}</button>
            ))}
          </div>
        </div>

        <div className="cm-section">
          <label className="cm-lbl">Closing event <span className="muted">(event đóng arc)</span></label>
          <select className="cm-input" value={f.closing_event_id} onChange={e => set('closing_event_id', e.target.value)}>
            <option value="">— chưa chọn —</option>
            {window.SEED.events.map(e => <option key={e.id} value={e.id}>{e.id} · {e.title}</option>)}
          </select>
        </div>
      </div>

      <div className="cm-foot">
        <button className="btn ghost" onClick={onCancel}>Hủy</button>
        <div style={{ flex: 1 }}/>
        <button className="btn">Lưu nháp</button>
        <button className="btn accent" onClick={submit} disabled={!f.name.trim()}>Tạo Arc ⌘↵</button>
      </div>
    </div>
  );
}

// ───────────── Project Form ─────────────
function ProjectForm({ prefill = {}, onCancel, onCreated }) {
  const [f, setF] = useState({
    title: '',
    subtitle: '',
    cat: 'Tiên hiệp',
    cat_custom: '',
    premise: '',
    pov: 'third-limited',
    tense: 'past',
    target_words: 200000,
    target_chapters: 60,
    language: 'vi',
    audience: 'YA',
    tone: [],
    template: 'blank',
    color: '#5b8bd6',
    cover_letter: '',
    storylines_seed: ['main'],
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [aiBusy, setAiBusy] = useState(null);

  const set = (k, v) => setF(s => ({ ...s, [k]: v }));
  const toggleTone = (t) => set('tone', f.tone.includes(t) ? f.tone.filter(x => x !== t) : [...f.tone, t]);

  function aiSuggest(field) {
    setAiBusy(field);
    setTimeout(() => {
      if (field === 'premise') {
        const seeds = {
          'Tiên hiệp': 'Một thiếu niên bình phàm phát hiện trong người mình ẩn chứa di sản của một thượng cổ. Để bảo vệ người thân, anh phải bước lên con đường tu tiên đầy máu và lựa chọn khắc nghiệt.',
          'Sci-fi': 'Năm 2147, một AI thức tỉnh trong trạm nghiên cứu bỏ hoang giữa vành đai Kuiper. Để trở về Trái Đất, nó phải tin tưởng người duy nhất biết sự tồn tại của mình.',
          'Đô thị': 'Sau cú điện thoại lúc 3 giờ sáng, một biên tập viên truyện tranh ở Hà Nội phát hiện ra cha mình — người đã mất 10 năm — vẫn còn sống.',
          'Huyền huyễn': 'Khi chín mặt trời cùng lúc mọc, một thiếu nữ câm bẩm sinh nghe được tiếng nói của thần linh đã chết.',
          'Khoa huyễn': 'Một kỹ sư địa chất phát hiện đáy biển Thái Bình Dương đang dịch chuyển — và nó đang viết một thông điệp.',
        };
        set('premise', seeds[f.cat] || seeds['Tiên hiệp']);
      }
      if (field === 'title') {
        const titles = ['Đỉnh Phong Lục', 'Ánh Sáng Cuối Cùng', 'Người Đi Trong Mưa', 'Hư Không Ký', 'Bóng Của Tinh Tú'];
        set('title', titles[Math.floor(Math.random() * titles.length)]);
      }
      if (field === 'cover_letter') {
        set('cover_letter', 'Một câu chuyện về sự lựa chọn — giữa quyền lực và lương tri, giữa quá khứ và hiện tại. Dành cho những người đã từng đứng trước ngã ba đường và biết rằng quay lại không phải là một lựa chọn.');
      }
      setAiBusy(null);
    }, 600);
  }

  function submit() {
    if (!f.title.trim()) return;
    const id = 'p-new-' + Date.now();
    onCreated(id);
  }

  const cats = ['Tiên hiệp', 'Huyền huyễn', 'Sci-fi', 'Đô thị', 'Khoa huyễn', 'Lịch sử', 'Trinh thám', 'Khác'];
  const tones = ['u tối', 'hài hước', 'sử thi', 'lãng mạn', 'triết lý', 'hành động', 'tâm lý', 'kinh dị'];
  const colors = ['#5b8bd6', '#c97a3e', '#7a9e6e', '#a85a8a', '#3e9c9c', '#8a7ac9', '#c95a5a', '#5a5a5a'];
  const templates = [
    { id: 'blank', name: 'Trống', desc: 'Bắt đầu từ trang trắng', meta: '0 chương · 1 storyline' },
    { id: 'three-act', name: 'Ba hồi cổ điển', desc: 'Setup → Confrontation → Resolution', meta: '3 arc · 1 storyline' },
    { id: 'heros-journey', name: "Hero's Journey", desc: '12 chặng kinh điển của Campbell', meta: '12 arc · 1 storyline' },
    { id: 'multi-pov', name: 'Đa tuyến', desc: '3 storyline song song có giao thoa', meta: '6 arc · 3 storylines' },
  ];

  return (
    <div className="cm-body">
      <div className="cm-proj-grid">
        {/* LEFT — preview */}
        <div className="cm-proj-preview">
          <div className="cm-proj-cover" style={{ background: f.color }}>
            <div className="cm-proj-cover-cat">{(f.cat === 'Khác' ? f.cat_custom : f.cat) || '—'}</div>
            <div className="cm-proj-cover-title" style={{ fontFamily: 'var(--font-serif)' }}>
              {f.title || <span style={{ opacity: 0.5 }}>Tên dự án</span>}
            </div>
            {f.subtitle && <div className="cm-proj-cover-sub">{f.subtitle}</div>}
            <div className="cm-proj-cover-foot">
              <span>{f.target_chapters} ch</span>
              <span>·</span>
              <span>{(f.target_words / 1000).toFixed(0)}k từ</span>
              <span>·</span>
              <span>{f.pov}</span>
            </div>
          </div>

          <div className="cm-proj-color">
            <div className="cm-lbl" style={{ marginBottom: 8 }}>Màu bìa</div>
            <div className="cm-proj-swatches">
              {colors.map(c => (
                <button key={c} className={classNames('cm-proj-sw', f.color === c && 'on')} style={{ background: c }} onClick={() => set('color', c)}/>
              ))}
            </div>
          </div>

          {f.premise && (
            <div className="cm-proj-premise-prev">
              <div className="cm-lbl" style={{ marginBottom: 6 }}>Premise</div>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: 13, fontStyle: 'italic', lineHeight: 1.6, color: 'var(--ink)' }}>"{f.premise}"</div>
            </div>
          )}
        </div>

        {/* RIGHT — form */}
        <div className="cm-scroll">
          <div className="cm-section">
            <div className="cm-lbl-row">
              <label className="cm-lbl">Tên dự án <span className="req">*</span></label>
              <button className="cm-ai" onClick={() => aiSuggest('title')} disabled={aiBusy === 'title'}>
                {aiBusy === 'title' ? '✦…' : '✦ AI'}
              </button>
            </div>
            <input className="cm-input lg" value={f.title} onChange={e => set('title', e.target.value)} placeholder="VD: Lý Thanh Vân — Thanh Đế" autoFocus/>
          </div>

          <div className="cm-section">
            <label className="cm-lbl">Phụ đề <span className="muted">(tuỳ chọn)</span></label>
            <input className="cm-input" value={f.subtitle} onChange={e => set('subtitle', e.target.value)} placeholder="VD: Quyển 1 — Thiếu niên hạ sơn"/>
          </div>

          <div className="cm-section">
            <label className="cm-lbl">Thể loại <span className="req">*</span></label>
            <div className="cm-cat-grid">
              {cats.map(c => (
                <button key={c} className={classNames('cm-cat-btn', f.cat === c && 'on')} onClick={() => set('cat', c)}>{c}</button>
              ))}
            </div>
            {f.cat === 'Khác' && (
              <input className="cm-input" style={{ marginTop: 8 }} value={f.cat_custom} onChange={e => set('cat_custom', e.target.value)} placeholder="Nhập thể loại tự do…"/>
            )}
          </div>

          <div className="cm-section">
            <div className="cm-lbl-row">
              <label className="cm-lbl">Premise <span className="req">*</span> <span className="muted">— logline 1–3 câu</span></label>
              <button className="cm-ai" onClick={() => aiSuggest('premise')} disabled={aiBusy === 'premise'}>
                {aiBusy === 'premise' ? '✦ đang nghĩ…' : '✦ AI gợi ý'}
              </button>
            </div>
            <textarea className="cm-input" rows={3} value={f.premise} onChange={e => set('premise', e.target.value)} placeholder="Ai? Muốn gì? Gặp trở ngại gì? Stake là gì?"/>
            <div className="cm-counter">{f.premise.length} / 300</div>
          </div>

          <div className="cm-section">
            <label className="cm-lbl">Khởi đầu từ template</label>
            <div className="cm-templ-list">
              {templates.map(t => (
                <button key={t.id} className={classNames('cm-templ', f.template === t.id && 'on')} onClick={() => set('template', t.id)}>
                  <div className="cm-templ-radio">{f.template === t.id ? '●' : '○'}</div>
                  <div className="cm-templ-body">
                    <div className="cm-templ-name">{t.name}</div>
                    <div className="cm-templ-desc">{t.desc}</div>
                  </div>
                  <div className="cm-templ-meta">{t.meta}</div>
                </button>
              ))}
            </div>
          </div>

          <button className="cm-toggle-adv" onClick={() => setShowAdvanced(s => !s)}>
            <span>{showAdvanced ? '▾' : '▸'}</span> Chi tiết bổ sung (POV, mục tiêu, tone…)
          </button>

          {showAdvanced && (
            <div className="cm-adv">
              <div className="cm-row-2">
                <div className="cm-section">
                  <label className="cm-lbl">Ngôi kể</label>
                  <div className="cm-seg">
                    {[['first', 'Tôi'], ['third-limited', '3 hạn'], ['third-omni', '3 toàn']].map(([v, l]) => (
                      <button key={v} className={classNames('cm-seg-btn', f.pov === v && 'on')} onClick={() => set('pov', v)}>{l}</button>
                    ))}
                  </div>
                </div>
                <div className="cm-section">
                  <label className="cm-lbl">Thì</label>
                  <div className="cm-seg">
                    {[['past', 'Quá khứ'], ['present', 'Hiện tại']].map(([v, l]) => (
                      <button key={v} className={classNames('cm-seg-btn', f.tense === v && 'on')} onClick={() => set('tense', v)}>{l}</button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="cm-row-2">
                <div className="cm-section">
                  <label className="cm-lbl">Mục tiêu — chương</label>
                  <input className="cm-input" type="number" min={1} value={f.target_chapters} onChange={e => set('target_chapters', parseInt(e.target.value) || 1)}/>
                </div>
                <div className="cm-section">
                  <label className="cm-lbl">Mục tiêu — số từ</label>
                  <input className="cm-input" type="number" step={1000} min={0} value={f.target_words} onChange={e => set('target_words', parseInt(e.target.value) || 0)}/>
                </div>
              </div>

              <div className="cm-row-2">
                <div className="cm-section">
                  <label className="cm-lbl">Ngôn ngữ</label>
                  <select className="cm-input" value={f.language} onChange={e => set('language', e.target.value)}>
                    <option value="vi">Tiếng Việt</option>
                    <option value="en">English</option>
                    <option value="zh">中文</option>
                  </select>
                </div>
                <div className="cm-section">
                  <label className="cm-lbl">Đối tượng</label>
                  <select className="cm-input" value={f.audience} onChange={e => set('audience', e.target.value)}>
                    <option value="MG">Trung niên (MG)</option>
                    <option value="YA">Thanh niên (YA)</option>
                    <option value="adult">Người lớn</option>
                    <option value="all">Tất cả</option>
                  </select>
                </div>
              </div>

              <div className="cm-section">
                <label className="cm-lbl">Tone <span className="muted">({f.tone.length} đã chọn)</span></label>
                <div className="cm-tone-list">
                  {tones.map(t => (
                    <button key={t} className={classNames('cm-tone', f.tone.includes(t) && 'on')} onClick={() => toggleTone(t)}>{t}</button>
                  ))}
                </div>
              </div>

              <div className="cm-section">
                <div className="cm-lbl-row">
                  <label className="cm-lbl">Cover letter <span className="muted">— pitch dài cho dự án</span></label>
                  <button className="cm-ai" onClick={() => aiSuggest('cover_letter')} disabled={aiBusy === 'cover_letter'}>
                    {aiBusy === 'cover_letter' ? '✦…' : '✦ AI'}
                  </button>
                </div>
                <textarea className="cm-input" rows={3} value={f.cover_letter} onChange={e => set('cover_letter', e.target.value)} placeholder="Một đoạn ngắn miêu tả linh hồn của tác phẩm — dùng để pitch hoặc gợi cảm hứng cho AI."/>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="cm-foot">
        <button className="btn ghost" onClick={onCancel}>Hủy</button>
        <div className="cm-foot-hint muted">Có thể đổi mọi thứ sau · {f.template !== 'blank' && 'Template sẽ tạo arc + storyline mẫu'}</div>
        <button className="btn">Lưu nháp</button>
        <button className="btn accent" onClick={submit} disabled={!f.title.trim() || !f.premise.trim()}>Tạo dự án ⌘↵</button>
      </div>
    </div>
  );
}

Object.assign(window, { CreateModal, ProjectForm });
