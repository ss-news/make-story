// Canvas — Timeline + Arc swimlanes + on-click character cluster (arrows) + detail panel
// Layout: [time col] [arc swimlanes (5)] [cluster zone — appears on click] [detail panel]

function Canvas() {
  const gridRef = useRef(null);
  const [events, setEvents] = useState(() => window.SEED.events.map(e => ({ ...e })));
  const [arcs] = useState(() => window.SEED.arcs.map(a => ({ ...a })));
  const characters = window.SEED.characters;
  const chapters = window.SEED.chapters;

  const [visibleArcIds, setVisibleArcIds] = useState(['a1', 'a2', 'a3', 'a5', 'a6']);
  const [sel, setSel] = useState(null); // { kind: 'event'|'character', id }

  const visibleArcs = visibleArcIds.map(id => arcs.find(a => a.id === id)).filter(Boolean);

  const allChapterOrders = useMemo(() => {
    const orders = new Set();
    visibleArcs.forEach(a => {
      for (let i = a.chapter_start; i <= Math.min(a.chapter_end, 19); i++) orders.add(i);
    });
    return Array.from(orders).sort((x, y) => x - y);
  }, [visibleArcIds]);

  function eventsAt(arcId, chapterOrder) {
    const ch = chapters.find(c => c.order === chapterOrder);
    if (!ch) return [];
    return events.filter(e => e.arc_id === arcId && e.chapter_id === ch.id);
  }

  function updateEvent(id, patch) {
    setEvents(evs => evs.map(ev => ev.id === id ? { ...ev, ...patch } : ev));
  }
  function deleteEvent(id) {
    setEvents(evs => evs.filter(ev => ev.id !== id));
    setSel(null);
  }
  function createEvent(arcId, chapterId) {
    const id = 'e-new-' + Date.now();
    setEvents(evs => [...evs, {
      id, arc_id: arcId, chapter_id: chapterId,
      title: 'Sự kiện mới', description: '', characters: [],
      importance: 'minor', type: 'plot', is_turning: false, is_crossover: false, story_time: '',
    }]);
    setSel({ kind: 'event', id });
  }

  // ──────────── Cluster: chỉ hiển thị khi click event ────────────
  // Click character → chỉ mở detail panel, không hiển thị cluster/arrows
  const cluster = useMemo(() => {
    if (!sel || sel.kind !== 'event') return null;
    const ev = events.find(e => e.id === sel.id);
    if (!ev) return null;
    const chars = ev.characters.map(id => characters.find(c => c.id === id)).filter(Boolean);
    return { sourceKind: 'event', source: ev, items: chars.map(c => ({ kind: 'character', data: c })) };
  }, [sel, events]);

  return (
    <div className="cv2-root">
      {/* Header strip — arc visibility toggles */}
      <div className="cv2-strip">
        <span className="uppercase muted" style={{ fontSize: 10, letterSpacing: 0.12 + 'em' }}>Hiển thị arc</span>
        {arcs.map(a => {
          const sl = getStoryline(a.storyline_id);
          const on = visibleArcIds.includes(a.id);
          return (
            <button
              key={a.id}
              className={classNames('cv2-arc-toggle', on && 'on')}
              style={on ? { borderColor: sl.color, color: sl.color } : null}
              onClick={() => {
                if (on) setVisibleArcIds(ids => ids.filter(x => x !== a.id));
                else if (visibleArcIds.length < 5) setVisibleArcIds(ids => [...ids, a.id]);
              }}
              disabled={!on && visibleArcIds.length >= 5}
              title={a.name}
            >
              <span className="cv2-arc-dot" style={{ background: sl.color }}/>
              {a.name}
            </button>
          );
        })}
        <span className="muted" style={{ marginLeft: 'auto', fontSize: 10 }}>{visibleArcIds.length}/5 arc · click event hoặc nhân vật để xem liên kết</span>
      </div>

      {/* Main grid: [time] [arc lanes] [cluster zone] [detail panel] */}
      <div className={classNames('cv2-grid', sel && 'with-detail')} ref={gridRef}>
        {cluster && <ArrowLayer cluster={cluster} gridRef={gridRef}/>}
        {/* TIME column */}
        <div className="cv2-time">
          <div className="cv2-time-head">
            <span className="uppercase muted">thời gian</span>
          </div>
          {allChapterOrders.map(ord => {
            const ch = chapters.find(c => c.order === ord);
            return (
              <div key={ord} className="cv2-time-row">
                <div className="cv2-tick"/>
                <div className="cv2-time-label">
                  <div className="cv2-time-num">CH {String(ord).padStart(2, '0')}</div>
                  <div className="cv2-time-title">{ch ? ch.title.replace(/^Chương \d+: /, '') : ''}</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* ARC swimlanes */}
        <div className="cv2-lanes" style={{ gridTemplateColumns: `repeat(${visibleArcs.length}, minmax(180px, 1fr))` }}>
          {/* Header row */}
          {visibleArcs.map(a => {
            const sl = getStoryline(a.storyline_id);
            return (
              <div key={'h-' + a.id} className="cv2-lane-head" style={{ '--arc-c': sl.color }}>
                <div className="cv2-lane-head-meta">
                  <span className="cv2-arc-dot" style={{ background: sl.color }}/>
                  <span className="uppercase muted">arc</span>
                </div>
                <div className="cv2-lane-name">{a.name}</div>
                <div className="cv2-lane-range muted">CH {a.chapter_start}–{a.chapter_end}</div>
              </div>
            );
          })}

          {/* Body rows */}
          {allChapterOrders.map(ord => (
            <React.Fragment key={ord}>
              {visibleArcs.map(a => {
                const inRange = ord >= a.chapter_start && ord <= a.chapter_end;
                const ch = chapters.find(c => c.order === ord);
                const cellEvents = inRange && ch ? eventsAt(a.id, ord) : [];
                return (
                  <div
                    key={a.id + '-' + ord}
                    className={classNames('cv2-cell', !inRange && 'oob')}
                  >
                    {inRange && (
                      <div className="cv2-lane-track" style={{ '--arc-c': getStoryline(a.storyline_id).color }}/>
                    )}
                    {cellEvents.map(ev => {
                      const sl2 = getStoryline(a.storyline_id);
                      const evChars = ev.characters.map(cid => characters.find(x => x.id === cid)).filter(Boolean);
                      return (
                      <div
                        key={ev.id}
                        id={'cv2-event-' + ev.id}
                        className={classNames('cv2-evbox',
                          sel && sel.kind === 'event' && sel.id === ev.id && 'selected',
                          ev.is_turning && 'turning',
                          ev.is_crossover && 'crossover',
                          'imp-' + ev.importance,
                        )}
                        style={{ '--ev-c': sl2.color }}
                        onClick={() => setSel({ kind: 'event', id: ev.id })}
                        title={ev.title + (ev.story_time ? ' · ' + ev.story_time : '')}
                      >
                        <div className="cv2-evbox-top">
                          <span className="cv2-evbox-num">#{ev.narrative_order || '—'}</span>
                          <span className="cv2-evbox-chap">{(ev.chapter_id || '').toUpperCase()}</span>
                          <span className="cv2-evbox-flags">
                            {ev.is_turning && <span title="Turning point" style={{ color: 'oklch(60% 0.13 60)' }}>★</span>}
                            {ev.is_crossover && <span title="Crossover" style={{ color: 'var(--accent)' }}>⇄</span>}
                            {ev.importance === 'major' && <span className="cv2-evbox-major" title="Major"/>}
                          </span>
                        </div>
                        <div className="cv2-evbox-title">{ev.title}</div>
                        {(ev.story_time || ev.location) && (
                          <div className="cv2-evbox-meta">
                            {ev.story_time && <span>⏱ {ev.story_time}</span>}
                            {ev.location && <span>· {ev.location}</span>}
                          </div>
                        )}
                        <div className="cv2-evbox-bottom">
                          <span className={classNames('cv2-evbox-type', 'type-' + ev.type)}>{ev.type}</span>
                          {evChars.length > 0 && (
                            <span className="cv2-evbox-chars">
                              {evChars.slice(0, 4).map(c => (
                                <span key={c.id} className="cv2-evbox-avatar" style={{ borderColor: c.color, color: c.color, background: 'var(--paper)' }} title={c.name}>{initials(c.name)}</span>
                              ))}
                              {evChars.length > 4 && <span className="cv2-evbox-more">+{evChars.length - 4}</span>}
                            </span>
                          )}
                        </div>
                      </div>
                      );
                    })}
                    {inRange && cellEvents.length === 0 && ch && (
                      <button className="cv2-add" onClick={() => createEvent(a.id, ch.id)} title="Thêm event">+</button>
                    )}
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>

        {/* CLUSTER zone — characters/events branching off the selected node */}
        <div className="cv2-cluster" id="cv2-cluster-zone">
          {cluster && <ClusterView cluster={cluster} onPick={(kind, id) => setSel({ kind, id })} sel={sel}/>}
          {!cluster && (
            <div className="cv2-cluster-empty muted">
              <div className="cv2-cluster-empty-icon">⤴</div>
              <div>Click event hoặc nhân vật<br/>để xem liên kết</div>
            </div>
          )}
        </div>

        {/* DETAIL panel */}
        {sel && (
          <DetailPanel
            sel={sel}
            event={sel.kind === 'event' ? events.find(e => e.id === sel.id) : null}
            character={sel.kind === 'character' ? characters.find(c => c.id === sel.id) : null}
            characters={characters}
            arcs={arcs}
            chapters={chapters}
            onClose={() => setSel(null)}
            onUpdate={(patch) => sel.kind === 'event' && updateEvent(sel.id, patch)}
            onDelete={() => sel.kind === 'event' && deleteEvent(sel.id)}
            onJump={(kind, id) => setSel({ kind, id })}
          />
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// ClusterView — branching arrows from selected event/character
// ────────────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────
// ArrowLayer — top-level SVG covering full grid, draws arrows
// from event boxes (left) to cluster cards (right)
// ────────────────────────────────────────────────────────────
function ArrowLayer({ cluster, gridRef }) {
  const [paths, setPaths] = useState([]);
  const { sourceKind, source, items } = cluster;

  useEffect(() => {
    function compute() {
      if (!gridRef.current) return;
      const gridRect = gridRef.current.getBoundingClientRect();

      let sourceEl = null;
      if (sourceKind === 'event') {
        sourceEl = document.getElementById('cv2-event-' + source.id);
      } else {
        sourceEl = document.querySelector('.cv2-source-pin');
      }
      if (!sourceEl) { setPaths([]); return; }

      const sRect = sourceEl.getBoundingClientRect();
      const sx = sRect.right - gridRect.left + 4;
      const sy = sRect.top + sRect.height / 2 - gridRect.top;

      const newPaths = items.map(it => {
        const el = document.querySelector('[data-cluster-item="' + it.data.id + '"]');
        if (!el) return null;
        const r = el.getBoundingClientRect();
        const tx = r.left - gridRect.left - 4;
        const ty = r.top + r.height / 2 - gridRect.top;
        const dx = Math.max(60, (tx - sx) * 0.5);
        const d = `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`;
        const color = it.kind === 'character' ? it.data.color : 'oklch(48% 0.10 250)';
        return { d, color, key: it.data.id };
      }).filter(Boolean);
      setPaths(newPaths);
    }
    compute();
    const id = setInterval(compute, 250);
    window.addEventListener('resize', compute);
    return () => { clearInterval(id); window.removeEventListener('resize', compute); };
  }, [cluster]);

  return (
    <svg className="cv2-arrows-top" preserveAspectRatio="none">
      <defs>
        <marker id="cv2-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/>
        </marker>
      </defs>
      {paths.map(p => (
        <path key={p.key} d={p.d} stroke={p.color} fill="none" strokeWidth="1.6" markerEnd="url(#cv2-arrow)"/>
      ))}
    </svg>
  );
}

function ClusterView({ cluster, onPick, sel }) {
  const wrapRef = useRef(null);
  const { sourceKind, source, items } = cluster;
  const itemCount = items.length;
  return (
    <div className="cv2-cluster-wrap" ref={wrapRef}>
      {/* Source pin (visible only when source is character — to anchor the fan) */}
      {sourceKind === 'character' && (
        <div className="cv2-source-pin" style={{ borderColor: source.color, color: source.color }}>
          <span className="cv2-pin-avatar" style={{ borderColor: source.color, color: source.color }}>{initials(source.name)}</span>
          <div>
            <div className="uppercase muted" style={{ fontSize: 9 }}>nhân vật</div>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 14 }}>{source.name}</div>
          </div>
        </div>
      )}

      {/* Items column */}
      <div className="cv2-cluster-list" style={{ '--n': itemCount }}>
        {items.map((it, i) => {
          if (it.kind === 'character') {
            const c = it.data;
            return (
              <button
                key={c.id}
                className={classNames('cv2-cluster-card char', sel && sel.kind === 'character' && sel.id === c.id && 'selected')}
                data-cluster-item={c.id}
                style={{ borderColor: c.color }}
                onClick={() => onPick('character', c.id)}
              >
                <span className="cv2-cluster-avatar" style={{ borderColor: c.color, color: c.color }}>{initials(c.name)}</span>
                <div className="cv2-cluster-body">
                  <div className="cv2-cluster-name" style={{ color: c.color }}>{c.name}</div>
                  <div className="cv2-cluster-sub muted">{c.role}{c.faction ? ' · ' + c.faction : ''}</div>
                </div>
              </button>
            );
          }
          // event
          const ev = it.data;
          const arc = window.SEED.arcs.find(a => a.id === ev.arc_id);
          const sl = arc ? getStoryline(arc.storyline_id) : null;
          return (
            <button
              key={ev.id}
              className={classNames('cv2-cluster-card event', sel && sel.kind === 'event' && sel.id === ev.id && 'selected')}
              data-cluster-item={ev.id}
              style={{ borderColor: sl ? sl.color : 'var(--accent)' }}
              onClick={() => onPick('event', ev.id)}
            >
              <span className="cv2-cluster-evicon" style={{ color: sl ? sl.color : 'var(--accent)' }}>
                {ev.is_turning ? '★' : '◆'}
              </span>
              <div className="cv2-cluster-body">
                <div className="cv2-cluster-name">{ev.title}</div>
                <div className="cv2-cluster-sub muted">{arc ? arc.name : ''}{ev.chapter_id ? ' · ' + ev.chapter_id.toUpperCase() : ''}</div>
              </div>
            </button>
          );
        })}
        {itemCount === 0 && (
          <div className="muted" style={{ fontSize: 11, fontStyle: 'italic', padding: '12px 8px' }}>
            {sourceKind === 'event' ? 'Event này chưa có nhân vật.' : 'Nhân vật này chưa xuất hiện trong event nào.'}
          </div>
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Detail panel (kept compact)
// ────────────────────────────────────────────────────────────
function DetailPanel({ sel, event: ev, character: ch, characters, arcs, chapters, onClose, onUpdate, onDelete, onJump }) {
  if (sel.kind === 'event' && ev) {
    const arc = arcs.find(a => a.id === ev.arc_id);
    const chap = chapters.find(c => c.id === ev.chapter_id);
    const sl = arc ? getStoryline(arc.storyline_id) : null;
    const causes = (window.SEED.causality || []).filter(c => c.to === ev.id);
    const effects = (window.SEED.causality || []).filter(c => c.from === ev.id);
    const allEvents = window.SEED.events;
    return (
      <aside className="cv2-detail">
        <div className="cv2-detail-head">
          <span className="uppercase" style={{ color: sl ? sl.color : 'var(--accent)', fontSize: 10, letterSpacing: 0.12 + 'em' }}>
            EVENT · {ev.id}
            {ev.is_turning && <span style={{ color: 'oklch(60% 0.13 60)', marginLeft: 8 }}>★ TURNING</span>}
            {ev.is_crossover && <span style={{ color: 'var(--accent)', marginLeft: 8 }}>⇄ CROSSOVER</span>}
          </span>
          <button className="btn ghost" onClick={onClose}>×</button>
        </div>
        <div className="cv2-detail-body">
          <input
            className="cv2-detail-title"
            value={ev.title}
            onChange={e => onUpdate({ title: e.target.value })}
          />
          <div className="cv2-detail-meta">
            <span className="muted uppercase" style={{ fontSize: 9 }}>Arc</span>
            <span style={{ color: sl ? sl.color : 'var(--ink)', fontSize: 12 }}>{arc ? arc.name : '—'}</span>
            <span className="muted">·</span>
            <span className="muted uppercase" style={{ fontSize: 9 }}>Ch</span>
            <span style={{ fontSize: 12 }}>{chap ? 'CH ' + chap.order + ' — ' + chap.title.replace(/^Chương \d+: /, '') : '—'}</span>
            {typeof ev.narrative_order === 'number' && (
              <>
                <span className="muted">·</span>
                <span className="muted uppercase" style={{ fontSize: 9 }}>#</span>
                <span style={{ fontSize: 12 }}>{ev.narrative_order}</span>
              </>
            )}
          </div>

          <div className="cv2-detail-row">
            <label className="muted uppercase">Mức độ</label>
            <div className="cm-seg">
              {['major', 'minor'].map(v => (
                <button key={v} className={classNames('cm-seg-btn', ev.importance === v && 'on')} onClick={() => onUpdate({ importance: v })}>{v}</button>
              ))}
            </div>
          </div>
          <div className="cv2-detail-row">
            <label className="muted uppercase">Loại</label>
            <div className="cm-seg">
              {['plot', 'character', 'world'].map(v => (
                <button key={v} className={classNames('cm-seg-btn', ev.type === v && 'on')} onClick={() => onUpdate({ type: v })}>{v}</button>
              ))}
            </div>
          </div>
          <div className="cv2-detail-row">
            <label className="muted uppercase">Cờ</label>
            <div className="cm-seg">
              <button className={classNames('cm-seg-btn', ev.is_turning && 'on')} onClick={() => onUpdate({ is_turning: !ev.is_turning })}>★ Turning</button>
              <button className={classNames('cm-seg-btn', ev.is_crossover && 'on')} onClick={() => onUpdate({ is_crossover: !ev.is_crossover })}>⇄ Crossover</button>
            </div>
          </div>

          <div className="cv2-detail-grid-2">
            <div className="cv2-detail-section" style={{ marginTop: 0 }}>
              <div className="lbl">Thời gian truyện</div>
              <input className="cv2-detail-input" value={ev.story_time || ''} onChange={e => onUpdate({ story_time: e.target.value })} placeholder="VD: Năm 2, tháng 4"/>
            </div>
            <div className="cv2-detail-section" style={{ marginTop: 0 }}>
              <div className="lbl">Địa điểm</div>
              <input className="cv2-detail-input" value={ev.location || ''} onChange={e => onUpdate({ location: e.target.value })} placeholder="VD: Rừng Thanh Khê"/>
            </div>
          </div>

          <div className="cv2-detail-section">
            <div className="lbl">Tóm tắt</div>
            <textarea className="cv2-detail-textarea" value={ev.description} onChange={e => onUpdate({ description: e.target.value })} rows={4} placeholder="Chuyện gì xảy ra trong event này..."/>
          </div>

          <div className="cv2-detail-section">
            <div className="lbl">Hệ quả / Outcome</div>
            <textarea className="cv2-detail-textarea" value={ev.outcome || ''} onChange={e => onUpdate({ outcome: e.target.value })} rows={3} placeholder="Sau event này thay đổi gì? Nhân vật nào ảnh hưởng?"/>
          </div>

          <div className="cv2-detail-section">
            <div className="lbl">Ghi chú riêng tư</div>
            <textarea className="cv2-detail-textarea" value={ev.notes || ''} onChange={e => onUpdate({ notes: e.target.value })} rows={2} placeholder="Note cho writer, không xuất bản..."/>
          </div>

          <div className="cv2-detail-section">
            <div className="lbl">Nhân vật ({ev.characters.length})</div>
            <div className="cv2-detail-chars">
              {ev.characters.map(cid => {
                const c = characters.find(x => x.id === cid);
                if (!c) return null;
                return (
                  <div key={cid} className="cv2-detail-char-row" onClick={() => onJump('character', cid)}>
                    <span className="cv2-cluster-avatar" style={{ borderColor: c.color, color: c.color }}>{initials(c.name)}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontFamily: 'var(--font-serif)', fontSize: 13 }}>{c.name}</div>
                      <div className="muted" style={{ fontSize: 10 }}>{c.role}{c.faction ? ' · ' + c.faction : ''}</div>
                    </div>
                    <button className="btn ghost" onClick={(e) => { e.stopPropagation(); onUpdate({ characters: ev.characters.filter(x => x !== cid) }); }} style={{ fontSize: 10 }}>gỡ</button>
                  </div>
                );
              })}
              {ev.characters.length === 0 && <div className="muted" style={{ fontSize: 11, fontStyle: 'italic' }}>Chưa có nhân vật.</div>}
            </div>
          </div>

          {(causes.length > 0 || effects.length > 0) && (
            <div className="cv2-detail-section">
              <div className="lbl">Nhân quả</div>
              {causes.length > 0 && (
                <div className="cv2-causal-block">
                  <div className="cv2-causal-label">← do</div>
                  {causes.map(c => {
                    const e = allEvents.find(x => x.id === c.from);
                    if (!e) return null;
                    return (
                      <div key={c.from} className="cv2-causal-row" onClick={() => onJump('event', e.id)}>
                        <span className="cv2-causal-arrow">←</span>
                        <span className="cv2-causal-title">{e.title}</span>
                      </div>
                    );
                  })}
                </div>
              )}
              {effects.length > 0 && (
                <div className="cv2-causal-block">
                  <div className="cv2-causal-label">→ dẫn đến</div>
                  {effects.map(c => {
                    const e = allEvents.find(x => x.id === c.to);
                    if (!e) return null;
                    return (
                      <div key={c.to} className="cv2-causal-row" onClick={() => onJump('event', e.id)}>
                        <span className="cv2-causal-arrow">→</span>
                        <span className="cv2-causal-title">{e.title}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {chap && chap.summary && (
            <div className="cv2-detail-section">
              <div className="lbl">Bối cảnh chương</div>
              <div className="cv2-chap-context">
                <div className="cv2-chap-title">{chap.title}</div>
                <div className="cv2-chap-summary">{chap.summary}</div>
                <div className="cv2-chap-meta muted">{chap.word_count?.toLocaleString()} từ · {chap.status}</div>
              </div>
            </div>
          )}

          <div className="cv2-detail-foot">
            <button className="btn ghost" onClick={onDelete} style={{ color: 'var(--warn)' }}>Xóa event</button>
            <button className="btn">Mở trong Editor</button>
          </div>
        </div>
      </aside>
    );
  }

  if (sel.kind === 'character' && ch) {
    const charEvents = window.SEED.events.filter(e => e.characters.includes(ch.id));
    const traits = (window.SEED.traits || []).filter(t => t.character_id === ch.id);
    const rels = (window.SEED.relationships || []).filter(r => r.from === ch.id || r.to === ch.id);
    return (
      <aside className="cv2-detail">
        <div className="cv2-detail-head">
          <span className="uppercase" style={{ color: ch.color, fontSize: 10, letterSpacing: 0.12 + 'em' }}>CHARACTER · {ch.id}</span>
          <button className="btn ghost" onClick={onClose}>×</button>
        </div>
        <div className="cv2-detail-body">
          <div className="cv2-detail-char-hero">
            <div className="cv2-detail-char-avatar" style={{ borderColor: ch.color, color: ch.color }}>{initials(ch.name)}</div>
            <div>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: 22, color: ch.color }}>{ch.name}</div>
              <div className="muted" style={{ fontSize: 11 }}>{(ch.aliases || []).map(a => '"' + a + '"').join(' · ')}</div>
            </div>
          </div>

          <div className="cv2-detail-row">
            <label className="muted uppercase">Vai trò</label>
            <span style={{ fontSize: 12 }}>{ch.role}</span>
          </div>
          <div className="cv2-detail-row">
            <label className="muted uppercase">Phe</label>
            <span style={{ fontSize: 12 }}>{ch.faction || '—'}</span>
          </div>
          <div className="cv2-detail-row">
            <label className="muted uppercase">Trạng thái</label>
            <span style={{ color: ch.life_status === 'alive' ? 'var(--ok)' : 'var(--warn)', fontSize: 12 }}>{ch.life_status === 'alive' ? '○ còn sống' : '× đã mất'}</span>
          </div>

          {ch.appearance && (
            <div className="cv2-detail-section">
              <div className="lbl">Ngoại hình</div>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: 12, lineHeight: 1.55, color: 'var(--ink-2)' }}>{ch.appearance}</div>
            </div>
          )}
          {ch.personality && (
            <div className="cv2-detail-section">
              <div className="lbl">Tính cách</div>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: 12, lineHeight: 1.55, color: 'var(--ink-2)' }}>{ch.personality}</div>
            </div>
          )}

          {ch.tags && ch.tags.length > 0 && (
            <div className="cv2-detail-section">
              <div className="lbl">Tags</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {ch.tags.map(t => <span key={t} className="tag">{t}</span>)}
              </div>
            </div>
          )}

          {rels.length > 0 && (
            <div className="cv2-detail-section">
              <div className="lbl">Quan hệ ({rels.length})</div>
              {rels.map((r, i) => {
                const other = r.from === ch.id ? r.to : r.from;
                const oc = characters.find(c => c.id === other);
                if (!oc) return null;
                return (
                  <div key={i} className="cv2-detail-char-row" onClick={() => onJump('character', oc.id)}>
                    <span className="cv2-cluster-avatar" style={{ borderColor: oc.color, color: oc.color }}>{initials(oc.name)}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12 }}>{oc.name}</div>
                      <div className="muted" style={{ fontSize: 10 }}>{r.label}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="cv2-detail-section">
            <div className="lbl">Xuất hiện ({charEvents.length})</div>
            {charEvents.slice(0, 8).map(e => (
              <div key={e.id} className="cv2-detail-char-row" onClick={() => onJump('event', e.id)}>
                <span className="cv2-cluster-evicon" style={{ color: 'var(--accent)' }}>◆</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: 'var(--font-serif)', fontSize: 12 }}>{e.title}</div>
                  <div className="muted" style={{ fontSize: 10 }}>{e.chapter_id}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </aside>
    );
  }

  return null;
}

Object.assign(window, { Canvas });