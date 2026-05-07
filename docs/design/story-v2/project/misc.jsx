// World Bible (markdown stub) + Settings page

function WorldBible() {
  const [active, setActive] = useState('overview');
  const sections = [
    { id: 'overview', label: 'Tổng quan thế giới' },
    { id: 'realms', label: 'Tu vi cảnh giới' },
    { id: 'factions', label: 'Môn phái' },
    { id: 'places', label: 'Địa danh' },
    { id: 'items', label: 'Bảo vật' },
    { id: 'lore', label: 'Truyền thuyết' },
  ];

  return (
    <div className="page">
      <div className="page-head">
        <h1>World Bible</h1>
        <span className="crumbs">Markdown · 6 mục</span>
        <div className="head-actions">
          <button className="btn"><Icon name="plus" size={11}/> Mục mới</button>
        </div>
      </div>
      <div className="page-body" style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="world-page">
          <div className="world-side">
            {sections.map(s => (
              <div key={s.id} className={classNames('ws-item', active === s.id && 'active')} onClick={() => setActive(s.id)}>{s.label}</div>
            ))}
          </div>
          <div className="world-body">
            <h1>Tổng quan thế giới</h1>
            <p>Thế giới Cửu Châu chia làm ba cõi: <b>Nhân giới</b>, <b>Tiên giới</b> và <b>Ma giới</b>. Loài người sống ở Nhân giới, tu sĩ tu luyện để tiến lên Tiên giới, còn Ma giới bị phong ấn bởi tiền nhân từ ngàn năm trước.</p>
            <h2>Tu vi cảnh giới</h2>
            <p>Có chín cảnh giới chính: Luyện Khí — Trúc Cơ — Kim Đan — Nguyên Anh — Hóa Thần — Phản Hư — Hợp Thể — Đại Thừa — Độ Kiếp. Mỗi cảnh giới có chín tầng nhỏ.</p>
            <h2>Phong ấn ngàn năm</h2>
            <p>Năm 0, mười hai vị Thượng Cổ Tiên Đế đã hợp lực phong ấn Ma giới. <span style={{ background: 'var(--accent-soft)', padding: '0 3px' }}>Tới hôm nay (chương 18) phong ấn đã bị phá.</span></p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Settings({ theme, setTheme, aiOn, setAiOn }) {
  return (
    <div className="page">
      <div className="page-head"><h1>Cài đặt</h1></div>
      <div className="page-body">
        <div className="set-page">
          <div className="set-section">
            <h2>Hiển thị</h2>
            <div className="set-row">
              <div className="lbl">Giao diện<span className="desc">Sáng / Tối</span></div>
              <div className="ctl">
                <button className={classNames('btn', theme === 'light' && 'accent')} onClick={() => setTheme('light')}><Icon name="sun" size={11}/> Sáng</button>
                <button className={classNames('btn', theme === 'dark' && 'accent')} onClick={() => setTheme('dark')} style={{ marginLeft: 6 }}><Icon name="moon" size={11}/> Tối</button>
              </div>
            </div>
            <div className="set-row">
              <div className="lbl">Font editor<span className="desc">Font phần soạn thảo</span></div>
              <div className="ctl"><select className="btn" style={{ width: '100%' }}><option>Lora (mặc định)</option><option>Iowan Old Style</option><option>Georgia</option></select></div>
            </div>
          </div>

          <div className="set-section">
            <h2>AI</h2>
            <div className="set-row">
              <div className="lbl">Bật AI gợi ý<span className="desc">Phát hiện Event ẩn, gợi ý tiếp đoạn, kiểm tra mâu thuẫn</span></div>
              <div className="ctl"><Toggle on={aiOn} onChange={setAiOn} label={aiOn ? 'BẬT' : 'TẮT'}/></div>
            </div>
            <div className="set-row">
              <div className="lbl">Provider<span className="desc">Local Ollama hoặc API ngoài</span></div>
              <div className="ctl"><select className="btn" style={{ width: '100%' }}><option>Local · Ollama (qwen2.5:14b)</option><option>OpenAI · GPT-4o</option><option>Anthropic · Claude</option></select></div>
            </div>
            <div className="set-row">
              <div className="lbl">Auto-suggest<span className="desc">Tự gợi ý Event mới khi viết</span></div>
              <div className="ctl"><Toggle on={true} onChange={()=>{}}/></div>
            </div>
          </div>

          <div className="set-section">
            <h2>Local-first</h2>
            <div className="set-row">
              <div className="lbl">Vị trí lưu trữ<span className="desc">SQLite local · không upload server</span></div>
              <div className="ctl" style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--muted)' }}>~/Library/.../web-story.db</div>
            </div>
            <div className="set-row">
              <div className="lbl">Sao lưu tự động<span className="desc">Mỗi 5 phút khi đang viết</span></div>
              <div className="ctl"><Toggle on={true} onChange={()=>{}}/></div>
            </div>
            <div className="set-row">
              <div className="lbl">Phím tắt<span className="desc">Quick search</span></div>
              <div className="ctl"><span className="kbd">⌘</span> <span className="kbd">K</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

window.WorldBible = WorldBible;
window.Settings = Settings;
