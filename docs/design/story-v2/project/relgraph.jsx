// Relationship Graph — info cards laid out radially with SVG edges underneath

function RelGraph({ onOpen }) {
  const [filter, setFilter] = useState({ family: true, romance: true, mentor: true, ally: true, rival: true, enemy: true });
  const [selected, setSelected] = useState('c-ltv');

  const chars = window.SEED.characters;
  const rels = window.SEED.relationships.filter(r => filter[r.type]);

  // Layout: protagonist center, others ring around
  const W = 980, H = 640, cx = W / 2, cy = H / 2;
  const positions = {};
  positions['c-ltv'] = { x: cx, y: cy };
  const rest = chars.filter(c => c.id !== 'c-ltv');
  rest.forEach((c, i) => {
    const angle = (i / rest.length) * Math.PI * 2 - Math.PI / 2;
    const r = 250;
    positions[c.id] = {
      x: cx + Math.cos(angle) * r,
      y: cy + Math.sin(angle) * r,
    };
  });

  const sel = getCharacter(selected);
  const selRels = window.SEED.relationships.filter(r => r.from === selected || r.to === selected);
  const neighborSet = new Set([selected, ...selRels.map(r => r.from === selected ? r.to : r.from)]);

  return (
    <div className="page">
      <div className="page-head">
        <h1>Relationship Graph</h1>
        <span className="crumbs">{chars.length} nhân vật · {rels.length} quan hệ</span>
        <div className="head-actions">
          <button className="btn"><Icon name="filter" size={11}/> Lọc</button>
          <button className="btn"><Icon name="save" size={11}/> Xuất PNG</button>
        </div>
      </div>
      <div className="page-body" style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="rg-wrap" style={{ flex: 1 }}>
          <div className="rg-canvas">
            <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
              <defs>
                <marker id="arr2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
                  <path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"/>
                </marker>
              </defs>
              {rels.map((r, i) => {
                const p1 = positions[r.from], p2 = positions[r.to];
                if (!p1 || !p2) return null;
                const dx = p2.x - p1.x, dy = p2.y - p1.y;
                const len = Math.sqrt(dx * dx + dy * dy);
                const ux = dx / len, uy = dy / len;
                const off = 80;
                const x1 = p1.x + ux * off, y1 = p1.y + uy * off;
                const x2 = p2.x - ux * off, y2 = p2.y - uy * off;
                const isHi = selected === r.from || selected === r.to;
                return (
                  <g key={i} opacity={isHi ? 1 : 0.22}>
                    <line className={'rg-edge ' + r.type} x1={x1} y1={y1} x2={x2} y2={y2} strokeWidth={isHi ? 1.6 : 1}/>
                    <text className="rg-edge-label" x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 4} textAnchor="middle">{r.label}</text>
                  </g>
                );
              })}
            </svg>
            <div className="rg-card-layer" style={{ position: 'absolute', inset: 0 }}>
              {chars.map(c => {
                const p = positions[c.id];
                // convert SVG coords to %
                const left = (p.x / W) * 100;
                const top = (p.y / H) * 100;
                const isSel = c.id === selected;
                const isNeighbor = neighborSet.has(c.id);
                const isProtag = c.id === 'c-ltv';
                return (
                  <div
                    key={c.id}
                    className={classNames('rg-card', isProtag && 'protag', isSel && 'selected', !isNeighbor && 'dim', c.life_status === 'deceased' && 'deceased')}
                    style={{ left: left + '%', top: top + '%', '--sl-c': c.color }}
                    onClick={() => setSelected(c.id)}
                    onDoubleClick={() => onOpen(c.id)}
                  >
                    <div className="rgc-head">
                      <Avatar name={c.name} color={c.color} size={isProtag ? 'md' : 'md'}/>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="rgc-name">{c.name}{c.life_status === 'deceased' && <span style={{ color: 'var(--muted-2)', marginLeft: 4 }}>†</span>}</div>
                        <div className="rgc-role">{c.role} · {c.faction}</div>
                      </div>
                    </div>
                    {c.aliases[0] && (
                      <div style={{ fontSize: 10, color: 'var(--muted)', fontStyle: 'italic', fontFamily: 'var(--font-serif)', lineHeight: 1.3, marginBottom: 4 }}>
                        aka {c.aliases.slice(0, 2).join(' · ')}
                      </div>
                    )}
                    <div className="rgc-row">
                      {c.tags.slice(0, 3).map(t => <span key={t} className="pill">{t}</span>)}
                    </div>
                    <div className="rgc-foot">
                      <span>CH {c.first_chap}–{c.last_chap}</span>
                      <span>{c.appearance_count} xh</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rg-side">
            <h3>Lọc loại quan hệ</h3>
            <div className="filter-row">
              {[
                ['family', 'Gia đình', 'var(--sl-court)'],
                ['romance', 'Tình cảm', 'var(--sl-demon)'],
                ['mentor', 'Sư đồ', 'var(--turning)'],
                ['ally', 'Đồng minh', 'var(--ok)'],
                ['rival', 'Cạnh tranh', 'var(--muted-2)'],
                ['enemy', 'Kẻ thù', 'oklch(55% 0.16 25)'],
              ].map(([k, l, col]) => (
                <button
                  key={k}
                  className="btn"
                  style={{ borderColor: filter[k] ? col : 'var(--hairline)', color: filter[k] ? col : 'var(--muted)' }}
                  onClick={() => setFilter(f => ({ ...f, [k]: !f[k] }))}
                >
                  <span style={{ width: 10, height: 1, background: col, display: 'inline-block', marginRight: 4 }}/>{l}
                </button>
              ))}
            </div>

            <h3>Đang chọn</h3>
            {sel && (
              <div className="ctx-card current" style={{ borderLeftColor: sel.color }}>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 6 }}>
                  <Avatar name={sel.name} color={sel.color}/>
                  <div>
                    <div className="ttl">{sel.name}</div>
                    <div style={{ fontSize: 10, color: 'var(--muted)' }}>{sel.role} · {sel.faction}</div>
                  </div>
                </div>
                <div style={{ fontSize: 11, fontFamily: 'var(--font-serif)', color: 'var(--ink-2)', fontStyle: 'italic', marginTop: 6 }}>
                  {sel.personality}
                </div>
                <button className="btn ghost" style={{ width: '100%', justifyContent: 'center', marginTop: 8 }} onClick={() => onOpen(sel.id)}>Mở chi tiết →</button>
              </div>
            )}

            <h3>{selRels.length} quan hệ</h3>
            {selRels.map((r, i) => {
              const otherId = r.from === selected ? r.to : r.from;
              const o = getCharacter(otherId);
              if (!o) return null;
              return (
                <div key={i} style={{ display: 'flex', gap: 8, padding: '6px 0', alignItems: 'center', borderBottom: '1px dotted var(--hairline)', cursor: 'pointer' }} onClick={() => setSelected(otherId)}>
                  <Avatar name={o.name} size="xs" color={o.color}/>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: 'var(--font-serif)', fontSize: 12 }}>{o.name}</div>
                    <div style={{ fontSize: 10, color: 'var(--muted)' }}>{r.label}</div>
                  </div>
                  <span className="tag" style={{ fontSize: 9 }}>{r.type}</span>
                </div>
              );
            })}

            <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 16, lineHeight: 1.6 }}>
              <span className="kbd">Click</span> chọn · <span className="kbd">DblClick</span> mở chi tiết
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

window.RelGraph = RelGraph;
