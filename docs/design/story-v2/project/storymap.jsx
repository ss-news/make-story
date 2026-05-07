// Story Map — three views: Arc Map (flagship), Storyline Grid, Arc Detail

function StoryMap({ subview, setSubview, onOpenArc }) {
  return (
    <div className="page" style={{ height: '100%' }}>
      <div className="smap-tabs">
        <div className={classNames('tb', subview === 'canvas' && 'active')} onClick={() => setSubview('canvas')}>Canvas</div>
        <div className={classNames('tb', subview === 'arc-map' && 'active')} onClick={() => setSubview('arc-map')}>Arc Map</div>
        <div className={classNames('tb', subview === 'storyline-grid' && 'active')} onClick={() => setSubview('storyline-grid')}>Storyline Grid</div>
        <div className={classNames('tb', subview === 'arc-detail' && 'active')} onClick={() => setSubview('arc-detail')}>Arc Detail</div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8, padding: '6px 32px' }}>
          <span className="uppercase" style={{ color: 'var(--muted)' }}>Lý Thanh Vân — Thanh Đế</span>
          <button className="btn"><Icon name="filter" size={11}/> Lọc tuyến</button>
          <button className="btn accent"><Icon name="sparkle" size={11}/> AI tóm tắt</button>
        </div>
      </div>

      {subview === 'canvas' && <Canvas/>}
      {subview === 'arc-map' && <ArcMap onOpenArc={onOpenArc}/>}
      {subview === 'storyline-grid' && <StorylineGrid onOpenArc={onOpenArc}/>}
      {subview === 'arc-detail' && <ArcDetail/>}
    </div>
  );
}

function ArcMap({ onOpenArc }) {
  const storylines = window.SEED.storylines;
  return (
    <div className="arc-map">
      {storylines.map(sl => {
        const arcs = window.SEED.arcs.filter(a => a.storyline_id === sl.id).sort((a, b) => a.order - b.order);
        const totalEvents = window.SEED.events.filter(e => arcs.some(a => a.id === e.arc_id)).length;
        return (
          <div key={sl.id} className="sl-row">
            <div className="sl-head">
              <span className="marker" style={{ background: sl.color }}/>
              <span className="name">
                {sl.name}
                {sl.is_main && <Tag color={sl.color}>Tuyến chính</Tag>}
                <span className="pov">POV: {getCharacter(sl.pov)?.name}</span>
              </span>
              <span className="stats">{arcs.length} ARC · {totalEvents} EVENT</span>
            </div>
            <div className="scroll-x">
              <div className="sl-track">
                {arcs.map((arc, idx) => {
                  const closing = arc.closing_event_id ? getEvent(arc.closing_event_id) : null;
                  const next = arcs[idx + 1];
                  return (
                    <React.Fragment key={arc.id}>
                      <div
                        className={classNames('arc-card', arc.status)}
                        style={{ '--sl-c': sl.color }}
                        onClick={() => onOpenArc(arc.id)}
                      >
                        <div className="num">ARC {String(arc.order).padStart(2, '0')}</div>
                        <div className="ttl">{arc.name}</div>
                        <div className="row"><span className="k">CH</span> <span>{arc.chapter_start}–{arc.chapter_end}</span></div>
                        <div className="row"><span className="k">@</span> <span>{arc.setting}</span></div>
                        <div className="row"><span className="k">▸</span> <span>{arc.status}</span></div>
                        <div className="goal">"{arc.goal}"</div>
                      </div>
                      {next && closing && (
                        <div className="turning-conn">
                          <div className="star" title="Turning point">★</div>
                          <div className="lbl">{closing.title}</div>
                        </div>
                      )}
                      {next && !closing && (
                        <div className="turning-conn">
                          <div className="star" style={{ borderColor: 'var(--hairline-strong)', color: 'var(--muted-2)' }}>·</div>
                        </div>
                      )}
                    </React.Fragment>
                  );
                })}
                <div className="add-arc"><Icon name="plus"/></div>
              </div>
            </div>
          </div>
        );
      })}

      <div className="ai-card" style={{ maxWidth: 720, marginTop: 24 }}>
        <div className="ai-head"><Icon name="sparkle"/> AI phát hiện</div>
        <div className="ai-body">
          Tuyến <b>Ma giáo</b> (Huyết Tổ) chỉ có 1 arc trong khi đã hé lộ ở chương 18. Bạn có muốn AI gợi ý
          arc tiếp theo (Arc 2: Huyết Tổ thu thập huyết lệnh)?
        </div>
        <div className="ai-actions">
          <button className="btn accent">Tạo arc gợi ý</button>
          <button className="btn ghost">Bỏ qua</button>
        </div>
      </div>
    </div>
  );
}

function StorylineGrid({ onOpenArc }) {
  const storylines = window.SEED.storylines;
  const minCh = 1, maxCh = 40;
  const tickStep = 5;
  const ticks = [];
  for (let c = minCh; c <= maxCh; c += tickStep) ticks.push(c);

  const colWidth = 40; // px per chapter
  const trackWidth = (maxCh - minCh + 1) * colWidth;

  return (
    <div className="sgrid-wrap">
      <div className="sgrid" style={{ gridTemplateColumns: `160px ${trackWidth}px` }}>
        <div className="corner"/>
        <div className="axis-x" style={{ gridTemplateColumns: `repeat(${ticks.length}, ${tickStep * colWidth}px)` }}>
          {ticks.map(t => <div key={t} className="tick">CH {t}</div>)}
        </div>

        {storylines.map(sl => {
          const arcs = window.SEED.arcs.filter(a => a.storyline_id === sl.id);
          return (
            <React.Fragment key={sl.id}>
              <div className="sl-label">
                <span className="marker" style={{ background: sl.color }}/>
                <span>{sl.name}</span>
                {sl.is_main && <span style={{ marginLeft: 'auto', fontSize: 9, color: 'var(--muted)', letterSpacing: 0.1, textTransform: 'uppercase' }}>main</span>}
              </div>
              <div className="row">
                {arcs.map(arc => {
                  const left = (arc.chapter_start - minCh) * colWidth;
                  const w = (arc.chapter_end - arc.chapter_start + 1) * colWidth;
                  return (
                    <div
                      key={arc.id}
                      className={classNames('arc-bar', arc.status === 'planned' && 'planned')}
                      style={{ left, width: w - 4, '--sl-c': sl.color, color: 'var(--ink)' }}
                      onClick={() => onOpenArc(arc.id)}
                    >
                      <span className="ttl">Arc {arc.order}: {arc.name}</span>
                      <span className="meta">{arc.status}</span>
                    </div>
                  );
                })}
                {arcs.filter(a => a.closing_event_id).map(arc => {
                  const closing = getEvent(arc.closing_event_id);
                  const ch = getChapter(closing.chapter_id);
                  if (!ch) return null;
                  const left = (ch.order - minCh + 0.5) * colWidth;
                  return (
                    <div key={arc.id + '-tp'} className="turning-mark" style={{ left }} title={closing.title}>★</div>
                  );
                })}
              </div>
            </React.Fragment>
          );
        })}
      </div>

      <div style={{ marginTop: 24, display: 'flex', gap: 24, fontSize: 11, color: 'var(--muted)', flexWrap: 'wrap' }}>
        <div className="flex gap-8" style={{ alignItems: 'center' }}><span style={{ width: 16, height: 12, border: '1px solid var(--ink)', background: 'var(--paper-2)' }}/> Arc đã viết</div>
        <div className="flex gap-8" style={{ alignItems: 'center' }}><span style={{ width: 16, height: 12, border: '1px dashed var(--ink)', opacity: 0.6 }}/> Arc dự kiến</div>
        <div className="flex gap-8" style={{ alignItems: 'center' }}><span style={{ width: 12, height: 12, borderRadius: '50%', border: '1px solid var(--turning)', color: 'var(--turning)', fontSize: 8, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>★</span> Turning point</div>
        <div className="flex gap-8" style={{ alignItems: 'center' }}><span style={{ display: 'inline-block', width: 16, height: 0, borderTop: '2px dashed var(--sl-court)' }}/> Crossover</div>
      </div>
    </div>
  );
}

function ArcDetail() {
  const arc = getArc('a3');
  const arcEvents = window.SEED.events.filter(e => e.arc_id === arc.id);
  const presenceChars = ['c-ltv', 'c-tnh', 'c-tongoc', 'c-suphu', 'c-shA', 'c-huyetto', 'c-suphu', 'c-killer'].slice(0, 6).map(getCharacter);

  // Synthesize a wider chapter range for demo (Arc 3 = CH 16–25, but show full arc range densely)
  const chaps = [];
  for (let i = arc.chapter_start; i <= arc.chapter_end; i++) {
    const real = window.SEED.chapters.find(c => c.order === i);
    chaps.push(real || { id: 'syn-' + i, order: i, title: 'Chương ' + i });
  }

  // Build a deterministic presence map for chars × chapters (so the grid looks dense & varied)
  const presenceMap = {};
  presenceChars.forEach((c, ci) => {
    presenceMap[c.id] = {};
    chaps.forEach((ch, chi) => {
      // hash-ish: protagonists appear often, supporters episodic
      const seed = (ci * 7 + chi * 3 + ch.order) % 11;
      const major = ci === 0 ? seed > 1 : seed > 5;
      const minor = ci === 0 ? false : seed > 2 && seed <= 5;
      const cross = (ci >= 2 && ch.order % 4 === 0);
      // overlay real arcEvents
      const realEvs = arcEvents.filter(e => e.chapter_id === ch.id && e.characters.includes(c.id));
      if (realEvs.length) {
        presenceMap[c.id][ch.id] = {
          major: realEvs.some(e => e.importance === 'major'),
          minor: !realEvs.some(e => e.importance === 'major'),
          cross: realEvs.some(e => e.is_crossover),
          titles: realEvs.map(e => e.title),
        };
      } else if (major || minor) {
        presenceMap[c.id][ch.id] = { major, minor: !major && minor, cross, titles: [] };
      }
    });
  });

  // For DAG, position events by narrative_order in columns
  // Use arcEvents + their direct upstream/downstream that fall in arc range
  const allEvents = window.SEED.events;
  const causality = window.SEED.causality;

  // include arc events + their direct neighbors (upstream/downstream) for context
  const neighborIds = new Set(arcEvents.map(e => e.id));
  causality.forEach(c => {
    if (neighborIds.has(c.to)) neighborIds.add(c.from);
    if (neighborIds.has(c.from) && arcEvents.some(e => e.id === c.from)) neighborIds.add(c.to);
  });
  const dagEvents = [...neighborIds].map(id => getEvent(id)).filter(Boolean).sort((a, b) => a.narrative_order - b.narrative_order);

  // simple layout — assign x based on narrative_order, y based on storyline
  const layout = {};
  const slOrder = ['s-main', 's-court', 's-demon'];
  dagEvents.forEach((e, i) => {
    const slIdx = slOrder.indexOf(getArc(e.arc_id).storyline_id);
    layout[e.id] = {
      x: 20 + (e.narrative_order - dagEvents[0].narrative_order) * 200,
      y: 30 + slIdx * 100,
    };
  });

  return (
    <div className="arc-detail">
      <div className="ad-head">
        <h1>Arc 3 — {arc.name}</h1>
        <div className="meta">
          <span><span className="k">Tuyến</span> Main</span>
          <span><span className="k">Chương</span> {arc.chapter_start}–{arc.chapter_end}</span>
          <span><span className="k">Bối cảnh</span> {arc.setting}</span>
          <span><span className="k">Trạng thái</span> {arc.status}</span>
          <span><span className="k">Mục tiêu</span> "{arc.goal}"</span>
        </div>
      </div>

      <div className="ad-section">
        <h2>Presence Grid · ai xuất hiện chương nào</h2>
        <div className="presence-grid">
          <table>
            <thead>
              <tr>
                <th>Nhân vật</th>
                {chaps.map(c => <th key={c.id} title={c.title}>CH {c.order}</th>)}
              </tr>
            </thead>
            <tbody>
              {presenceChars.map(c => (
                <tr key={c.id}>
                  <td>
                    <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
                      <Avatar name={c.name} size="xs" color={c.color}/>
                      {c.name}
                    </span>
                  </td>
                  {chaps.map(ch => {
                    const p = presenceMap[c.id][ch.id];
                    if (!p) return <td key={ch.id}/>;
                    const titles = p.titles && p.titles.length ? p.titles.join('\n') : `CH ${ch.order}`;
                    return (
                      <td key={ch.id} title={titles}>
                        <span className={classNames('pdot', p.minor && 'minor', p.cross && 'crossover')}/>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ marginTop: 8, fontSize: 10, color: 'var(--muted)', display: 'flex', gap: 16 }}>
          <span><span className="pdot" style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: 'var(--ink)' }}/> Major</span>
          <span><span className="pdot" style={{ display: 'inline-block', width: 5, height: 5, borderRadius: '50%', background: 'var(--ink)', opacity: 0.5 }}/> Minor</span>
          <span><span className="pdot" style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: 'var(--sl-court)' }}/> Crossover</span>
        </div>
      </div>

      <div className="ad-section">
        <h2>Causality DAG · vì sao xảy ra</h2>
        <div className="causality-dag" style={{ height: 360, overflow: 'auto' }}>
          <svg viewBox={`0 0 ${20 + dagEvents.length * 200} 360`} preserveAspectRatio="none">
            <defs>
              <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                <path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"/>
              </marker>
            </defs>
            {causality.map((c, i) => {
              const a = layout[c.from], b = layout[c.to];
              if (!a || !b) return null;
              const x1 = a.x + 180, y1 = a.y + 20;
              const x2 = b.x, y2 = b.y + 20;
              const cx = (x1 + x2) / 2;
              return (
                <path key={i} d={`M${x1},${y1} C${cx},${y1} ${cx},${y2} ${x2},${y2}`} stroke="var(--muted)" strokeWidth="1" fill="none" markerEnd="url(#arr)"/>
              );
            })}
          </svg>
          {dagEvents.map(e => {
            const arcOf = getArc(e.arc_id);
            const sl = getStoryline(arcOf.storyline_id);
            return (
              <div
                key={e.id}
                className={classNames('ev-node', e.is_turning && 'turning')}
                style={{ left: layout[e.id].x, top: layout[e.id].y, borderLeftColor: sl.color, borderLeftWidth: 3, borderLeftStyle: 'solid' }}
              >
                <div className="ev-num">E{e.id.slice(1)} · CH{getChapter(e.chapter_id)?.order}</div>
                <div className="ev-ttl">
                  {e.is_turning && <span style={{ color: 'var(--turning)' }}>★ </span>}
                  {e.title}
                </div>
                <div className="ev-meta">
                  {e.characters.slice(0, 3).map(cid => {
                    const c = getCharacter(cid);
                    return c ? <Avatar key={cid} name={c.name} size="xs" color={c.color}/> : null;
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="ad-section">
        <h2>Events trong arc · {arcEvents.length}</h2>
        <div className="cause-list">
          {arcEvents.map(e => (
            <div key={e.id} className="cl-row" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ color: 'var(--muted)', fontSize: 10, width: 60 }}>E{e.id.slice(1)} · CH{getChapter(e.chapter_id)?.order}</span>
              {e.is_turning && <span style={{ color: 'var(--turning)' }}>★</span>}
              <span style={{ fontFamily: 'var(--font-serif)', fontSize: 13 }}>{e.title}</span>
              <span style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                {e.characters.slice(0, 3).map(cid => {
                  const c = getCharacter(cid);
                  return c ? <Avatar key={cid} name={c.name} size="xs" color={c.color}/> : null;
                })}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

window.StoryMap = StoryMap;
