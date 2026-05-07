// Editor 3-column view: chapter list / writing surface / context panel

function Editor({ state, dispatch, onJump }) {
  const [activeChId, setActiveChId] = useState('ch18');
  const [ctxTab, setCtxTab] = useState('events');
  const [selectedAnchor, setSelectedAnchor] = useState('e14');
  const [aiSugg, setAiSugg] = useState(true);

  const chapters = window.SEED.chapters;
  const activeCh = chapters.find(c => c.id === activeChId);

  // Events linked to this chapter
  const linkedEvents = window.SEED.events.filter(e => e.chapter_id === activeChId);
  // Characters present in those events
  const charIdsHere = [...new Set(linkedEvents.flatMap(e => e.characters))];
  const chars = charIdsHere.map(getCharacter).filter(Boolean);

  return (
    <div className="editor-grid">
      {/* Chapter list */}
      <div className="col-chapters">
        <div className="chap-head">
          <span className="ttl">19 chương · 56,340 từ</span>
          <button className="btn ghost" title="Chương mới"><Icon name="plus"/></button>
        </div>
        <div className="chap-search">
          <Icon name="search" size={12}/>
          <input placeholder="Tìm chương…"/>
        </div>
        {chapters.map(c => (
          <div
            key={c.id}
            className={classNames('chap', c.status === 'draft' && 'draft', c.id === activeChId && 'active')}
            onClick={() => setActiveChId(c.id)}
          >
            <span className="num">CH {String(c.order).padStart(2, '0')}</span>
            <span className="title">{c.title.replace(/^Chương \d+:\s*/, '')}</span>
            <span className="meta">
              <span className="dot"/>
              <span>{c.word_count.toLocaleString('vi-VN')} từ</span>
              {c.status === 'draft' && <span style={{ color: 'var(--warn)' }}>· nháp</span>}
            </span>
          </div>
        ))}
        <div className="add-chap"><Icon name="plus" size={10}/> Chương mới</div>
      </div>

      {/* Writing canvas */}
      <div className="col-editor">
        <div className="editor-toolbar">
          <button className="tb"><Icon name="h1"/></button>
          <button className="tb"><Icon name="h2"/></button>
          <span className="sep"/>
          <button className="tb"><Icon name="bold"/></button>
          <button className="tb"><Icon name="italic"/></button>
          <button className="tb"><Icon name="quote"/></button>
          <span className="sep"/>
          <button className="tb" title="Mention character (@)"><Icon name="users"/> @</button>
          <button className="tb" title="Anchor event (◆)"><Icon name="diamond"/> ◆</button>
          <span className="save-status"><span className="dot"/> Đã lưu · 2s trước</span>
          <button className="btn accent" style={{ marginLeft: 12 }}><Icon name="sparkle"/> AI gợi ý</button>
        </div>

        <div className="editor-canvas">
          <div className="doc">
            <h1>{activeCh?.title}</h1>
            <div className="ch-meta">CH 18 · ARC 3 · 3,640 TỪ · NHÁP · BÁM TUYẾN MAIN</div>

            <p>
              Hư Cảnh mở ra trong tiếng đá vỡ vụn. Sương trắng cuộn lên từ những phiến đá cổ ngàn năm,
              quấn quanh chân của <span className="char-mention" data-cid="c-ltv">Lý Thanh Vân</span> như một sinh vật còn sống.
              Trong tay y, thanh kiếm cũ rung khẽ — một nhịp, hai nhịp — như đáp lại điều gì sâu trong lòng đất.
            </p>

            <p>
              "Có người." <span className="char-mention" data-cid="c-tnh">Trần Như Hoa</span> đứng sau y nửa bước,
              giọng thấp đến mức gần như chỉ là hơi thở. Tay nàng đặt lên cán kiếm, nhưng chưa rút ra.
            </p>

            <p>
              Từ trong sương, một bóng áo xanh quan tách ra. <span className="event-anchor" data-eid="e14" onClick={() => setSelectedAnchor('e14')}>
              Lý Thanh Vân nhận ra ngay — đó không phải tu sĩ. Đó là người của triều đình.
              </span>
            </p>

            <p>
              "<span className="char-mention" data-cid="c-tongoc">Tô đại nhân</span>." Lý Thanh Vân chậm rãi cúi đầu, không hạ kiếm.
              "Khâm Thiên Giám đến Hư Cảnh tìm gì?"
            </p>

            <p>
              Tô Ngọc cười khẽ. Trong sương mù, nụ cười ấy lạnh như đá. "Cùng một thứ với cậu thôi — bảo vật trấn cảnh."
              Y dừng lại. "Nhưng tôi đến vì vận nước. Còn cậu, vì cái gì?"
            </p>

            <p style={{ color: 'var(--muted-2)', fontStyle: 'italic' }}>
              [Đoạn sau đang viết — ngắt câu bỏ ngỏ, giữ căng thẳng…]
            </p>

            {aiSugg && (
              <div className="ai-card">
                <div className="ai-head"><Icon name="sparkle"/> AI gợi ý tiếp đoạn · dựa trên Event e14 + tính cách 2 nhân vật</div>
                <div className="ai-body">
                  Lý Thanh Vân không trả lời ngay. Y biết — trong khoảnh khắc này — câu trả lời sai sẽ
                  biến Tô Ngọc từ kẻ đối đầu thành kẻ thù. Mà y chưa đủ mạnh để có thêm một kẻ thù.
                </div>
                <div className="ai-actions">
                  <button className="btn">Chấp nhận</button>
                  <button className="btn">Viết lại</button>
                  <button className="btn ghost" onClick={() => setAiSugg(false)}>Bỏ qua</button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Context panel */}
      <div className="col-context">
        <div className="ctx-tabs">
          <div className={classNames('tab', ctxTab === 'events' && 'active')} onClick={() => setCtxTab('events')}>Events ({linkedEvents.length})</div>
          <div className={classNames('tab', ctxTab === 'chars' && 'active')} onClick={() => setCtxTab('chars')}>Nhân vật ({chars.length})</div>
          <div className={classNames('tab', ctxTab === 'arc' && 'active')} onClick={() => setCtxTab('arc')}>Arc</div>
        </div>

        <div className="ctx-body">
          {ctxTab === 'events' && (
            <>
              <div className="ctx-section">
                <div className="lbl">Events trong chương</div>
                {linkedEvents.map(e => (
                  <div
                    key={e.id}
                    className={classNames('ctx-card', selectedAnchor === e.id && 'current')}
                    onClick={() => setSelectedAnchor(e.id)}
                    style={{ borderLeftColor: getStorylineColor(getArc(e.arc_id)?.storyline_id) }}
                  >
                    <div className="ttl">
                      {e.is_turning && <span style={{ color: 'var(--turning)', marginRight: 4 }}>★</span>}
                      {e.title}
                    </div>
                    <div className="row">
                      <span className="pill">{e.importance === 'major' ? 'Major' : 'Minor'}</span>
                      <span className="pill">{e.type}</span>
                      {e.is_crossover && <span className="pill" style={{ color: 'var(--sl-court)', borderColor: 'var(--sl-court)' }}>crossover</span>}
                    </div>
                    <div className="character-line">
                      {e.characters.slice(0, 4).map(cid => {
                        const c = getCharacter(cid);
                        return c ? <Avatar key={cid} name={c.name} size="xs" color={c.color}/> : null;
                      })}
                      <span style={{ fontSize: 10, color: 'var(--muted)', marginLeft: 4 }}>{e.story_time}</span>
                    </div>
                    {selectedAnchor === e.id && (
                      <div className="quote">"{e.description}"</div>
                    )}
                  </div>
                ))}
              </div>

              <button className="btn ghost" style={{ width: '100%', justifyContent: 'center' }}><Icon name="plus" size={10}/> Tạo Event mới ở vị trí con trỏ</button>

              <div className="ai-card" style={{ marginTop: 16 }}>
                <div className="ai-head"><Icon name="sparkle"/> Phát hiện Event ẩn</div>
                <div className="ai-body">
                  Đoạn vừa viết có thể là một Event mới: <b>"Lý Thanh Vân và Tô Ngọc đối thoại lần đầu"</b>.
                  Đề xuất gắn vào Arc 3 · narrative_order 12.5.
                </div>
                <div className="ai-actions">
                  <button className="btn accent">Xem diff</button>
                  <button className="btn ghost">Bỏ qua</button>
                </div>
              </div>
            </>
          )}

          {ctxTab === 'chars' && (
            <div className="ctx-section">
              <div className="lbl">Nhân vật xuất hiện trong chương</div>
              {chars.map(c => (
                <div key={c.id} className="ctx-card" onClick={() => onJump?.('character', c.id)} style={{ borderLeftColor: c.color, borderLeftWidth: 3 }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 6 }}>
                    <Avatar name={c.name} color={c.color}/>
                    <div style={{ flex: 1 }}>
                      <div className="ttl" style={{ marginBottom: 2 }}>{c.name}</div>
                      <div style={{ fontSize: 10, color: 'var(--muted)' }}>{c.role} · {c.faction}</div>
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--ink-2)', fontStyle: 'italic', fontFamily: 'var(--font-serif)' }}>
                    {c.personality}
                  </div>
                  <div className="row" style={{ marginTop: 8 }}>
                    {c.tags.slice(0, 3).map(t => <span key={t} className="pill">{t}</span>)}
                  </div>
                </div>
              ))}
            </div>
          )}

          {ctxTab === 'arc' && (
            <div className="ctx-section">
              <div className="lbl">Arc hiện tại</div>
              <div className="ctx-card current" style={{ borderLeftColor: 'var(--sl-main)' }}>
                <div className="ttl">Arc 3 — Bí cảnh thượng cổ</div>
                <div className="row" style={{ marginTop: 6 }}>
                  <span className="pill">CH 16–25</span>
                  <span className="pill">drafting</span>
                  <span className="pill">tuyến Main</span>
                </div>
                <div className="quote" style={{ marginTop: 10 }}>
                  Mục tiêu: Tìm bảo vật trấn phái trong Hư Cảnh thượng cổ.
                </div>
                <div style={{ marginTop: 10, fontSize: 11, color: 'var(--muted)' }}>
                  Đã viết 3/10 chương · 9,740/~30,000 từ
                </div>
                <div style={{ marginTop: 8, height: 4, background: 'var(--paper-2)', overflow: 'hidden' }}>
                  <div style={{ width: '32%', height: '100%', background: 'var(--accent)' }}/>
                </div>
              </div>

              <div className="lbl" style={{ marginTop: 20 }}>Arc trước → sau</div>
              <div className="cause-list">
                <div className="cl-row">← Arc 2 — Tông môn tu tiên (CH 6–15) · ✓ hoàn thành</div>
                <div className="cl-row" style={{ borderColor: 'var(--accent)' }}>● Arc 3 — Bí cảnh thượng cổ (CH 16–25)</div>
                <div className="cl-row" style={{ opacity: 0.5 }}>→ Arc 4 — Ma giới khởi loạn (CH 26–40) · planned</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

window.Editor = Editor;
