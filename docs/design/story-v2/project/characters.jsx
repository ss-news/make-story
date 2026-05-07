// Character grid + Character detail with tabs (AttributeHistory, Trait, Relationships, Appearances)

function CharacterGrid({ onOpen }) {
  const [q, setQ] = useState('');
  const [filter, setFilter] = useState('all');
  const chars = window.SEED.characters.filter(c => {
    if (filter === 'alive' && c.life_status !== 'alive') return false;
    if (filter === 'deceased' && c.life_status !== 'deceased') return false;
    if (q && !c.name.toLowerCase().includes(q.toLowerCase()) && !c.aliases.some(a => a.toLowerCase().includes(q.toLowerCase()))) return false;
    return true;
  });

  return (
    <div className="page">
      <div className="page-head">
        <h1>Nhân vật</h1>
        <span className="crumbs">{chars.length} / {window.SEED.characters.length}</span>
        <div className="head-actions">
          <button className="btn"><Icon name="filter" size={11}/> Lọc</button>
          <button className="btn primary"><Icon name="plus" size={11}/> Nhân vật mới</button>
        </div>
      </div>
      <div className="page-body">
        <div className="char-grid-page">
          <div className="char-toolbar">
            <input placeholder="Tìm theo tên, biệt danh, tag…" value={q} onChange={e => setQ(e.target.value)}/>
            <button className={classNames('btn', filter === 'all' && 'accent')} onClick={() => setFilter('all')}>Tất cả</button>
            <button className={classNames('btn', filter === 'alive' && 'accent')} onClick={() => setFilter('alive')}>Còn sống</button>
            <button className={classNames('btn', filter === 'deceased' && 'accent')} onClick={() => setFilter('deceased')}>Đã chết</button>
            <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--muted)', letterSpacing: 0.06 }}>NHÓM THEO TUYẾN ▾</span>
          </div>

          {window.SEED.storylines.map(sl => {
            const slChars = chars.filter(c => c.home_storyline_id === sl.id);
            if (!slChars.length) return null;
            return (
              <div key={sl.id} style={{ marginBottom: 32 }}>
                <div className="event-group-h">
                  <span className="marker" style={{ background: sl.color }}/>
                  Tuyến {sl.name}
                  <span className="ct">{slChars.length} nhân vật</span>
                </div>
                <div className="char-grid">
                  {slChars.map(c => (
                    <div
                      key={c.id}
                      className={classNames('char-card', c.life_status === 'deceased' && 'deceased')}
                      style={{ '--sl-c': c.color }}
                      onClick={() => onOpen(c.id)}
                    >
                      <div className="av"><Avatar name={c.name} size="lg" color={c.color}/></div>
                      <div className="nm">{c.name}</div>
                      <div className="role">{c.role}</div>
                      {c.aliases.length > 0 && <div className="alias">{c.aliases.slice(0, 2).join(' · ')}</div>}
                      <div className="stat">
                        <span>CH {c.first_chap}–{c.last_chap}</span>
                        <span>{c.appearance_count} xh</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function CharacterDetail({ cid, onBack, onOpenEvent }) {
  const [tab, setTab] = useState('overview');
  const c = getCharacter(cid);
  if (!c) return null;

  const traits = window.SEED.traits.filter(t => t.character_id === cid);
  const events = window.SEED.events.filter(e => e.characters.includes(cid)).sort((a, b) => a.narrative_order - b.narrative_order);
  const rels = window.SEED.relationships.filter(r => r.from === cid || r.to === cid);

  return (
    <div className="page">
      <div className="page-head">
        <span className="crumbs"><a onClick={onBack} style={{ cursor: 'pointer' }}>Nhân vật</a> / </span>
        <h1>{c.name}</h1>
        <div className="head-actions">
          <button className="btn"><Icon name="eye" size={11}/> Xem trên Story Map</button>
          <button className="btn accent"><Icon name="sparkle" size={11}/> AI: Sinh tóm tắt</button>
        </div>
      </div>
      <div className="page-body">
        <div className="char-detail">
          <div className="cd-head" style={{ '--sl-c': c.color }}>
            <div className="av-lg" style={{ borderLeftColor: c.color }}>{initials(c.name)}</div>
            <div>
              <h1 style={{ fontFamily: 'var(--font-serif)', margin: 0 }}>{c.name}</h1>
              {c.aliases.length > 0 && <div className="alias">aka {c.aliases.join(' · ')}</div>}
              <div className="row" style={{ marginTop: 6 }}>
                <Tag color={c.color}>{c.role}</Tag>
                <Tag>{c.faction}</Tag>
                {c.life_status === 'deceased' && <Tag color="var(--muted)">† Đã mất</Tag>}
                {c.tags.map(t => <Tag key={t}>{t}</Tag>)}
              </div>
            </div>
            <div style={{ textAlign: 'right', fontSize: 11, color: 'var(--muted)', lineHeight: 1.6 }}>
              <div><span style={{ color: 'var(--muted-2)' }}>XUẤT HIỆN</span> {c.appearance_count} lần</div>
              <div><span style={{ color: 'var(--muted-2)' }}>CHƯƠNG</span> {c.first_chap}–{c.last_chap}</div>
              <div><span style={{ color: 'var(--muted-2)' }}>TUYẾN GỐC</span> {getStoryline(c.home_storyline_id)?.name}</div>
            </div>
          </div>

          <div className="cd-tabs">
            {[
              ['overview', 'Tổng quan'],
              ['history', `Attribute History (${traits.length + events.length})`],
              ['traits', `Trait (${traits.length})`],
              ['rels', `Quan hệ (${rels.length})`],
              ['appearances', `Xuất hiện (${events.length})`],
            ].map(([k, l]) => (
              <div key={k} className={classNames('t', tab === k && 'active')} onClick={() => setTab(k)}>{l}</div>
            ))}
          </div>

          {tab === 'overview' && (
            <>
              <div className="cd-section">
                <h2>Ngoại hình</h2>
                <div style={{ fontFamily: 'var(--font-serif)', fontSize: 14, lineHeight: 1.7, maxWidth: 600 }}>{c.appearance}</div>
              </div>
              <div className="cd-section">
                <h2>Tính cách</h2>
                <div style={{ fontFamily: 'var(--font-serif)', fontSize: 14, lineHeight: 1.7, maxWidth: 600 }}>{c.personality}</div>
              </div>
              <div className="cd-section">
                <h2>Tóm tắt hành trình</h2>
                <div style={{ fontFamily: 'var(--font-serif)', fontSize: 14, lineHeight: 1.8, maxWidth: 700, fontStyle: 'italic', color: 'var(--ink-2)' }}>
                  Sau khi mẹ qua đời, Lý Thanh Vân rời thôn Thanh Khê, bị truy sát, được Bạch Hạc lão tổ cứu mạng và đưa lên Thanh Vân Sơn.
                  Y bái sư thành công, khổ luyện kiếm pháp, đánh bại sư huynh Lưu Chí, gặp Trần Như Hoa và đột phá Trúc Cơ.
                  Hiện tại y đang khám phá Hư Cảnh thượng cổ — nơi y vừa giáp mặt Tô Ngọc của triều đình.
                </div>
                <div className="ai-card" style={{ marginTop: 12, maxWidth: 700 }}>
                  <div className="ai-head"><Icon name="sparkle"/> AI tóm tắt từ {events.length} events</div>
                  <div className="ai-actions">
                    <button className="btn">Sinh lại</button>
                    <button className="btn ghost">Sao chép</button>
                  </div>
                </div>
              </div>
            </>
          )}

          {tab === 'history' && (
            <div className="cd-section">
              <h2>Dòng thời gian thuộc tính</h2>
              {[...traits.map(t => ({ kind: 'trait', t })), ...events.map(e => ({ kind: 'event', e }))]
                .map(item => {
                  if (item.kind === 'trait') {
                    const ev = getEvent(item.t.acquired_event);
                    return { ...item, order: ev?.narrative_order || 0, ch: ev ? getChapter(ev.chapter_id)?.order : '?' };
                  }
                  return { ...item, order: item.e.narrative_order, ch: getChapter(item.e.chapter_id)?.order };
                })
                .sort((a, b) => a.order - b.order)
                .map((item, i) => {
                  if (item.kind === 'trait') {
                    return (
                      <div key={'t' + i} className="history-row">
                        <span className="when">CH {item.ch} · trait</span>
                        <span className="what">+ {item.t.name}</span>
                        <span className="why">{item.t.description}</span>
                      </div>
                    );
                  }
                  const e = item.e;
                  return (
                    <div key={'e' + i} className="history-row">
                      <span className="when">CH {item.ch} · event</span>
                      <span className="what">
                        {e.is_turning && <span style={{ color: 'var(--turning)' }}>★ </span>}
                        <a onClick={() => onOpenEvent(e.id)} style={{ cursor: 'pointer', borderBottom: '1px dashed var(--hairline-strong)' }}>{e.title}</a>
                      </span>
                      <span className="why">{e.description.slice(0, 80)}{e.description.length > 80 ? '…' : ''}</span>
                    </div>
                  );
                })}
            </div>
          )}

          {tab === 'traits' && (
            <>
              <div className="cd-section">
                <h2>Trait đang giữ</h2>
                {traits.filter(t => !t.lost_event).map(t => {
                  const acq = getEvent(t.acquired_event);
                  const icon = { item: '⚔', skill: '✦', ability: '◈', status: '◐' }[t.kind] || '·';
                  return (
                    <div key={t.id} className="trait-card">
                      <div className="icon">{icon}</div>
                      <div>
                        <div className="nm">{t.name}{t.version && <span style={{ color: 'var(--muted)', fontSize: 11, marginLeft: 8 }}>· {t.version}</span>}</div>
                        <div className="desc">{t.description}</div>
                      </div>
                      <div className="meta">
                        <div>{t.kind}</div>
                        <div>từ CH {acq ? getChapter(acq.chapter_id)?.order : '?'}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="cd-section">
                <h2>Trait đã mất</h2>
                {traits.filter(t => t.lost_event).map(t => {
                  const acq = getEvent(t.acquired_event);
                  const lost = getEvent(t.lost_event);
                  return (
                    <div key={t.id} className="trait-card lost">
                      <div className="icon">·</div>
                      <div>
                        <div className="nm">{t.name}</div>
                        <div className="desc">{t.description}</div>
                      </div>
                      <div className="meta">
                        <div>CH {acq ? getChapter(acq.chapter_id)?.order : '?'} → CH {lost ? getChapter(lost.chapter_id)?.order : '?'}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}

          {tab === 'rels' && (
            <div className="cd-section">
              <h2>Quan hệ</h2>
              {rels.map((r, i) => {
                const otherId = r.from === cid ? r.to : r.from;
                const o = getCharacter(otherId);
                if (!o) return null;
                return (
                  <div key={i} className="trait-card">
                    <div><Avatar name={o.name} color={o.color}/></div>
                    <div>
                      <div className="nm">{o.name}</div>
                      <div className="desc">{r.label} · {r.type}</div>
                    </div>
                    <div className="meta">
                      {r.progressions.length > 0 && (
                        <div style={{ fontSize: 10, color: 'var(--muted)' }}>
                          {r.progressions.length} bước tiến triển
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {tab === 'appearances' && (
            <div className="cd-section">
              <h2>Xuất hiện qua các chương</h2>
              {events.map(e => {
                const sl = getStoryline(getArc(e.arc_id).storyline_id);
                return (
                  <div key={e.id} className="event-row" style={{ '--sl-c': sl.color }} onClick={() => onOpenEvent(e.id)}>
                    <div className="left">
                      <div className="ttl">
                        {e.is_turning && <span className="star">★</span>}
                        {e.title}
                      </div>
                      <div className="desc">{e.description}</div>
                    </div>
                    <div className="right">
                      <span>CH {getChapter(e.chapter_id)?.order}</span>
                      <span>{e.story_time}</span>
                      <span>{e.importance} · {e.type}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

window.CharacterGrid = CharacterGrid;
window.CharacterDetail = CharacterDetail;
