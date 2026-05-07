// Event list view + Event detail panel

function EventList({ onOpen }) {
  const [filter, setFilter] = useState('all');
  const [groupBy, setGroupBy] = useState('arc'); // arc | storyline | importance | type | order

  let events = window.SEED.events.slice();
  if (filter === 'turning') events = events.filter(e => e.is_turning);
  if (filter === 'major') events = events.filter(e => e.importance === 'major');
  if (filter === 'crossover') events = events.filter(e => e.is_crossover);

  // group
  const groups = {};
  events.forEach(e => {
    let key, label;
    if (groupBy === 'arc') {
      const a = getArc(e.arc_id);
      key = a.id; label = `Arc ${a.order} — ${a.name}`;
    } else if (groupBy === 'storyline') {
      const a = getArc(e.arc_id);
      const sl = getStoryline(a.storyline_id);
      key = sl.id; label = sl.name;
    } else if (groupBy === 'importance') {
      key = e.importance; label = e.importance === 'major' ? 'Major' : 'Minor';
    } else if (groupBy === 'type') {
      key = e.type; label = e.type;
    } else {
      key = 'all'; label = 'Theo thứ tự kể chuyện';
    }
    groups[key] = groups[key] || { label, items: [] };
    groups[key].items.push(e);
  });

  return (
    <div className="page">
      <div className="page-head">
        <h1>Events</h1>
        <span className="crumbs">{events.length} / {window.SEED.events.length}</span>
        <div className="head-actions">
          <button className="btn primary"><Icon name="plus" size={11}/> Event mới</button>
        </div>
      </div>
      <div className="page-body">
        <div className="event-list-page">
          <div className="char-toolbar">
            <span className="uppercase" style={{ color: 'var(--muted)' }}>Lọc</span>
            {[['all', 'Tất cả'], ['turning', '★ Turning'], ['major', 'Major'], ['crossover', 'Crossover']].map(([k, l]) => (
              <button key={k} className={classNames('btn', filter === k && 'accent')} onClick={() => setFilter(k)}>{l}</button>
            ))}
            <span style={{ marginLeft: 24 }} className="uppercase">Nhóm</span>
            {[['arc', 'Arc'], ['storyline', 'Tuyến'], ['importance', 'Quan trọng'], ['type', 'Loại']].map(([k, l]) => (
              <button key={k} className={classNames('btn', groupBy === k && 'accent')} onClick={() => setGroupBy(k)}>{l}</button>
            ))}
          </div>

          {Object.entries(groups).map(([key, g]) => {
            // pick group color
            let groupColor = 'var(--muted)';
            if (groupBy === 'arc') groupColor = getStorylineColor(getArc(key)?.storyline_id);
            else if (groupBy === 'storyline') groupColor = getStoryline(key)?.color;
            return (
              <div key={key}>
                <div className="event-group-h">
                  <span className="marker" style={{ background: groupColor }}/>
                  <span style={{ fontFamily: 'var(--font-serif)' }}>{g.label}</span>
                  <span className="ct">{g.items.length} events</span>
                </div>
                {g.items.sort((a, b) => a.narrative_order - b.narrative_order).map(e => {
                  const a = getArc(e.arc_id);
                  const sl = getStoryline(a.storyline_id);
                  return (
                    <div key={e.id} className={classNames('event-row', e.is_turning && 'turning')} style={{ '--sl-c': sl.color }} onClick={() => onOpen(e.id)}>
                      <div className="left">
                        <div className="ttl">
                          {e.is_turning && <span className="star">★</span>}
                          {e.title}
                        </div>
                        <div className="desc">{e.description}</div>
                        <div className="row">
                          <Tag color={sl.color}>{sl.name}</Tag>
                          <Tag>Arc {a.order}</Tag>
                          <Tag>{e.importance}</Tag>
                          <Tag>{e.type}</Tag>
                          {e.is_crossover && <Tag color="var(--sl-court)">crossover</Tag>}
                          <span style={{ marginLeft: 8, display: 'flex', gap: 3 }}>
                            {e.characters.slice(0, 5).map(cid => {
                              const c = getCharacter(cid);
                              return c ? <Avatar key={cid} name={c.name} size="xs" color={c.color}/> : null;
                            })}
                          </span>
                        </div>
                      </div>
                      <div className="right">
                        <span>CH {getChapter(e.chapter_id)?.order}</span>
                        <span>{e.story_time}</span>
                        <span>narrative #{e.narrative_order}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function EventDetail({ eid, onClose, onJump }) {
  const e = getEvent(eid);
  if (!e) return null;
  const arc = getArc(e.arc_id);
  const sl = getStoryline(arc.storyline_id);
  const chap = getChapter(e.chapter_id);

  const upstream = window.SEED.causality.filter(c => c.to === eid).map(c => getEvent(c.from)).filter(Boolean);
  const downstream = window.SEED.causality.filter(c => c.from === eid).map(c => getEvent(c.to)).filter(Boolean);

  return (
    <>
      <div className="panel-overlay" onClick={onClose}/>
      <div className="panel">
        <div className="ph">
          <div style={{ flex: 1 }}>
            <div className="uppercase" style={{ color: 'var(--muted)' }}>Event · {e.id}</div>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 18, marginTop: 4 }}>
              {e.is_turning && <span style={{ color: 'var(--turning)' }}>★ </span>}
              {e.title}
            </div>
          </div>
          <button className="close" onClick={onClose}><Icon name="x"/></button>
        </div>
        <div className="pb">
          <div className="detail-grid">
            <div className="k">Tuyến</div><div className="v"><Tag color={sl.color}>{sl.name}</Tag></div>
            <div className="k">Arc</div><div className="v"><a style={{ borderBottom: '1px dashed var(--hairline-strong)', cursor: 'pointer' }}>Arc {arc.order} — {arc.name}</a></div>
            <div className="k">Chương</div><div className="v">CH {chap?.order} — {chap?.title.replace(/^Chương \d+:\s*/, '')}</div>
            <div className="k">Thời gian</div><div className="v">{e.story_time}</div>
            <div className="k">Quan trọng</div><div className="v">{e.importance}{e.is_turning && ' · ★ Turning'}</div>
            <div className="k">Loại</div><div className="v">{e.type}{e.is_crossover && ' · crossover'}</div>
            <div className="k">Tự sự</div><div className="v">narrative_order #{e.narrative_order}</div>
          </div>

          <div className="ctx-section" style={{ marginTop: 24 }}>
            <div className="lbl">Mô tả</div>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 14, lineHeight: 1.7 }}>{e.description}</div>
          </div>

          <div className="ctx-section">
            <div className="lbl">Nhân vật ({e.characters.length})</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {e.characters.map(cid => {
                const c = getCharacter(cid);
                if (!c) return null;
                return (
                  <div key={cid} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 8px', border: '1px solid var(--hairline)', cursor: 'pointer' }} onClick={() => onJump('character', cid)}>
                    <Avatar name={c.name} size="xs" color={c.color}/>
                    <span style={{ fontFamily: 'var(--font-serif)', fontSize: 12 }}>{c.name}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {upstream.length > 0 && (
            <div className="ctx-section">
              <div className="lbl">Vì các sự kiện trước ({upstream.length})</div>
              <div className="cause-list">
                {upstream.map(u => (
                  <div key={u.id} className="cl-row" onClick={() => onJump('event', u.id)}>
                    <span style={{ color: 'var(--muted)', marginRight: 8 }}>← E{u.id.slice(1)}</span>
                    {u.title}
                  </div>
                ))}
              </div>
            </div>
          )}

          {downstream.length > 0 && (
            <div className="ctx-section">
              <div className="lbl">Dẫn tới ({downstream.length})</div>
              <div className="cause-list">
                {downstream.map(d => (
                  <div key={d.id} className="cl-row" onClick={() => onJump('event', d.id)}>
                    <span style={{ color: 'var(--muted)', marginRight: 8 }}>→ E{d.id.slice(1)}</span>
                    {d.title}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="ai-card">
            <div className="ai-head"><Icon name="sparkle"/> AI kiểm tra mâu thuẫn</div>
            <div className="ai-body">Không phát hiện mâu thuẫn. Nhân vật {getCharacter(e.characters[0])?.name} có {window.SEED.traits.filter(t => t.character_id === e.characters[0] && getEvent(t.acquired_event)?.narrative_order < e.narrative_order && (!t.lost_event || getEvent(t.lost_event)?.narrative_order > e.narrative_order)).length} trait đang giữ tại thời điểm này.</div>
          </div>
        </div>
      </div>
    </>
  );
}

window.EventList = EventList;
window.EventDetail = EventDetail;
