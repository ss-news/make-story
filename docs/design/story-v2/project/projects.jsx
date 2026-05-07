// Project list / dashboard

function ProjectList({ onOpen, onCreate }) {
  const projects = [
    { id: 'p-ltv', cat: 'Tiên hiệp', title: 'Lý Thanh Vân — Thanh Đế', premise: 'Một thiếu niên thôn dã, cô đơn sau cái chết của mẹ, dấn thân lên Thanh Vân Sơn tu tiên. Sau lưng anh là một mưu đồ ngàn năm.', words: 56340, chapters: 19, characters: 8, arcs: 7, last: 'Hôm nay, 14:32', wip: true },
    { id: 'p-2', cat: 'Sci-fi', title: 'Mặt trời thứ hai', premise: 'Năm 2089, mặt trời thứ hai mọc trên Đông Á. Một kỹ sư Việt Nam phải chọn giữa gia đình và sự sống còn của loài người.', words: 12400, chapters: 6, characters: 4, arcs: 2, last: '3 ngày trước' },
    { id: 'p-3', cat: 'Đô thị', title: 'Quán cafe ngày mưa', premise: 'Tập truyện ngắn về những người gặp nhau trong một quán cafe nhỏ ở Hà Nội.', words: 8900, chapters: 12, characters: 14, arcs: 0, last: '2 tuần trước' },
  ];

  return (
    <div className="proj-page">
      <div className="pp-head">
        <h1>Web Story</h1>
        <span className="sub">3 dự án · local-first</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button className="btn"><Icon name="filter"/> Lọc</button>
          <button className="btn primary" onClick={onCreate}><Icon name="plus"/> Dự án mới</button>
        </div>
      </div>

      <div className="proj-grid">
        {projects.map(p => (
          <div key={p.id} className="proj-card" onClick={() => onOpen(p)}>
            <div className="pcat">{p.cat}{p.wip && <span style={{ marginLeft: 8, color: 'var(--accent)' }}>● đang viết</span>}</div>
            <div className="ptitle">{p.title}</div>
            <div className="ppremise">"{p.premise}"</div>
            <div className="pmeta">
              <span>{p.words.toLocaleString('vi-VN')} từ · {p.chapters} ch · {p.characters} nv</span>
              <span>{p.last}</span>
            </div>
          </div>
        ))}
        <div className="proj-card new" onClick={onCreate}>
          <Icon name="plus" size={24}/>
          <div style={{ marginTop: 8, fontSize: 11, letterSpacing: 0.1, textTransform: 'uppercase' }}>Dự án mới</div>
        </div>
      </div>

      <div style={{ marginTop: 60 }}>
        <div className="uppercase" style={{ color: 'var(--muted)', marginBottom: 12 }}>Hoạt động gần đây</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0, borderTop: '1px solid var(--hairline)' }}>
          {[
            { t: 'Hôm nay, 14:32', a: 'Sửa', ch: 'Chương 18: Đối mặt Tô Ngọc', proj: 'Lý Thanh Vân' },
            { t: 'Hôm nay, 11:08', a: 'AI gợi ý', ch: 'Tạo Event "Đột phá Trúc Cơ"', proj: 'Lý Thanh Vân' },
            { t: 'Hôm qua, 22:14', a: 'Sửa', ch: 'Chương 17: Vào Hư Cảnh', proj: 'Lý Thanh Vân' },
            { t: '2 ngày trước', a: 'Tạo', ch: 'Character: Tô Ngọc', proj: 'Lý Thanh Vân' },
          ].map((x, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '140px 80px 1fr 200px', padding: '10px 0', borderBottom: '1px solid var(--hairline)', fontSize: 12, alignItems: 'baseline' }}>
              <span style={{ color: 'var(--muted)', fontSize: 11 }}>{x.t}</span>
              <span className="tag">{x.a}</span>
              <span style={{ fontFamily: 'var(--font-serif)', fontSize: 13 }}>{x.ch}</span>
              <span style={{ color: 'var(--muted)', textAlign: 'right', fontSize: 11 }}>{x.proj}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

window.ProjectList = ProjectList;
