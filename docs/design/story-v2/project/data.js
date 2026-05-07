// Sample data — Lý Thanh Vân (tiên hiệp)
window.SEED = (function () {
  const storylines = [
    { id: 's-main', name: 'Main', is_main: true, color: 'oklch(58% 0.12 30)', pov: 'c-ltv', description: 'Tuyến chính — Lý Thanh Vân từ thôn nhỏ tới đỉnh tiên giới' },
    { id: 's-court', name: 'Triều đình', is_main: false, color: 'oklch(48% 0.10 250)', pov: 'c-tongoc', description: 'Tô Ngọc và âm mưu trong triều' },
    { id: 's-demon', name: 'Ma giáo', is_main: false, color: 'oklch(45% 0.13 340)', pov: 'c-huyetto', description: 'Huyết Tổ trỗi dậy sau ngàn năm' },
  ];

  const arcs = [
    { id: 'a1', storyline_id: 's-main', order: 1, name: 'Làng tân thủ', goal: 'Sống sót, rời thôn Thanh Khê', setting: 'Thôn Thanh Khê', chapter_start: 1, chapter_end: 5, status: 'completed', closing_event_id: 'e4' },
    { id: 'a2', storyline_id: 's-main', order: 2, name: 'Tông môn tu tiên', goal: 'Bái sư thành công, đột phá Trúc Cơ', setting: 'Thanh Vân Sơn', chapter_start: 6, chapter_end: 15, status: 'completed', closing_event_id: 'e12' },
    { id: 'a3', storyline_id: 's-main', order: 3, name: 'Bí cảnh thượng cổ', goal: 'Tìm bảo vật trấn phái', setting: 'Hư Cảnh', chapter_start: 16, chapter_end: 25, status: 'drafting', closing_event_id: null },
    { id: 'a4', storyline_id: 's-main', order: 4, name: 'Ma giới khởi loạn', goal: 'Đối đầu Huyết Tổ', setting: 'Ma Giới', chapter_start: 26, chapter_end: 40, status: 'planned', closing_event_id: null },

    { id: 'a5', storyline_id: 's-court', order: 1, name: 'Đại lễ đăng cơ', goal: 'Tô Ngọc nhậm chức Khâm Thiên Giám', setting: 'Hoàng cung', chapter_start: 10, chapter_end: 14, status: 'completed', closing_event_id: 'e15' },
    { id: 'a6', storyline_id: 's-court', order: 2, name: 'Âm mưu phế đế', goal: 'Vạch trần phe nghịch', setting: 'Hoàng cung', chapter_start: 15, chapter_end: 22, status: 'drafting', closing_event_id: null },

    { id: 'a7', storyline_id: 's-demon', order: 1, name: 'Huyết Tổ trỗi dậy', goal: 'Phá phong ấn', setting: 'Huyết Mộ', chapter_start: 18, chapter_end: 30, status: 'drafting', closing_event_id: null },
  ];

  const characters = [
    { id: 'c-ltv', name: 'Lý Thanh Vân', aliases: ['tiểu tử', 'Lý công tử', 'Vân nhi'], role: 'Nam chính', faction: 'Thanh Vân Phái', tags: ['kiếm sĩ', 'protagonist', 'có dị năng'], color: 'oklch(58% 0.12 30)', home_storyline_id: 's-main', appearance: 'Tóc đen, mắt sáng, 16 tuổi, vết sẹo bên má trái', personality: 'Trầm tĩnh, kiên cường, trọng nghĩa', life_status: 'alive', appearance_count: 47, first_chap: 1, last_chap: 30 },
    { id: 'c-suphu', name: 'Lão nhân áo trắng', aliases: ['Sư phụ', 'Bạch Hạc lão tổ'], role: 'Hỗ trợ', faction: 'Thanh Vân Phái', tags: ['sư đồ', 'kiếm tiên'], color: 'oklch(70% 0.04 80)', home_storyline_id: 's-main', appearance: 'Râu bạc, áo trắng, ánh mắt trầm tĩnh', personality: 'Bao dung, nghiêm khắc khi cần', life_status: 'alive', appearance_count: 18, first_chap: 5, last_chap: 25 },
    { id: 'c-tnh', name: 'Trần Như Hoa', aliases: ['Hoa nhi', 'Trần tiểu thư'], role: 'Nữ chính', faction: 'Trần gia', tags: ['kiếm sĩ', 'tiểu thư'], color: 'oklch(70% 0.10 350)', home_storyline_id: 's-main', appearance: 'Tóc dài đen, áo hồng, đôi mắt sắc', personality: 'Lạnh lùng bên ngoài, nội tâm sâu sắc', life_status: 'alive', appearance_count: 22, first_chap: 8, last_chap: 30 },
    { id: 'c-tongoc', name: 'Tô Ngọc', aliases: ['Tô đại nhân', 'Khâm Thiên Giám'], role: 'Hỗ trợ', faction: 'Triều đình', tags: ['quan lại', 'mưu sĩ'], color: 'oklch(48% 0.10 250)', home_storyline_id: 's-court', appearance: 'Áo xanh quan, dáng mảnh khảnh', personality: 'Lý tính, tính toán', life_status: 'alive', appearance_count: 15, first_chap: 10, last_chap: 22 },
    { id: 'c-huyetto', name: 'Huyết Tổ', aliases: ['Tổ', 'Huyết ma'], role: 'Phản diện chính', faction: 'Ma giáo', tags: ['ma đạo', 'cường giả'], color: 'oklch(45% 0.13 340)', home_storyline_id: 's-demon', appearance: 'Áo đen, mắt đỏ, da trắng nhợt', personality: 'Tàn nhẫn, kiêu ngạo', life_status: 'alive', appearance_count: 8, first_chap: 18, last_chap: 30 },
    { id: 'c-shA', name: 'Sư huynh A (Lưu Chí)', aliases: ['Lưu sư huynh'], role: 'Nam phụ', faction: 'Thanh Vân Phái', tags: ['đồng môn'], color: 'oklch(60% 0.06 200)', home_storyline_id: 's-main', appearance: 'Cao gầy, áo lam', personality: 'Ngạo mạn ban đầu, dần thân thiện', life_status: 'alive', appearance_count: 12, first_chap: 7, last_chap: 22 },
    { id: 'c-mother', name: 'Lý mẫu', aliases: ['Mẹ', 'Vương thị'], role: 'Hỗ trợ', faction: 'Lý gia', tags: ['gia đình'], color: 'oklch(72% 0.05 60)', home_storyline_id: 's-main', appearance: 'Trung niên, hiền hậu', personality: 'Yêu thương con vô điều kiện', life_status: 'deceased', appearance_count: 4, first_chap: 1, last_chap: 5 },
    { id: 'c-killer', name: 'Sát thủ áo đen', aliases: ['Hắc y nhân'], role: 'Phản diện phụ', faction: 'Hắc Hổ Đường', tags: ['sát thủ'], color: 'oklch(40% 0.04 30)', home_storyline_id: 's-main', appearance: 'Mặt nạ đen', personality: 'Lạnh lùng, chuyên nghiệp', life_status: 'deceased', appearance_count: 3, first_chap: 2, last_chap: 5 },
  ];

  const events = [
    { id: 'e1', arc_id: 'a1', chapter_id: 'ch1', title: 'Lý Thanh Vân rời thôn Thanh Khê', description: 'Sau khi mẹ qua đời, LTV rời thôn lên đường, mang theo thanh kiếm cũ của cha.', characters: ['c-ltv', 'c-mother'], importance: 'major', type: 'plot', is_turning: false, is_crossover: false, narrative_order: 1, story_time: 'Năm 1, đầu xuân' },
    { id: 'e2', arc_id: 'a1', chapter_id: 'ch2', title: 'Bị truy sát trên đường', description: 'Sát thủ áo đen chặn LTV ở rừng Thanh Khê. LTV bị thương nặng.', characters: ['c-ltv', 'c-killer'], importance: 'major', type: 'plot', is_turning: false, is_crossover: false, narrative_order: 2, story_time: 'Năm 1, ngày 3' },
    { id: 'e3', arc_id: 'a1', chapter_id: 'ch3', title: 'Lão nhân áo trắng xuất hiện', description: 'Lão nhân áo trắng đột nhiên xuất hiện, đánh đuổi sát thủ, mang LTV về núi.', characters: ['c-ltv', 'c-suphu', 'c-killer'], importance: 'major', type: 'plot', is_turning: false, is_crossover: false, narrative_order: 3, story_time: 'Năm 1, ngày 3' },
    { id: 'e4', arc_id: 'a1', chapter_id: 'ch5', title: 'Đánh boss Sói Trắng', description: 'LTV cùng sư phụ hạ Sói Trắng — sinh vật bảo hộ thôn. Mở đường lên Thanh Vân Sơn.', characters: ['c-ltv', 'c-suphu'], importance: 'major', type: 'plot', is_turning: true, is_crossover: false, narrative_order: 4, story_time: 'Năm 1, ngày 5' },

    { id: 'e5', arc_id: 'a2', chapter_id: 'ch6', title: 'Bái sư thành công', description: 'LTV chính thức trở thành đệ tử của Bạch Hạc lão tổ tại Thanh Vân Sơn.', characters: ['c-ltv', 'c-suphu'], importance: 'major', type: 'character', is_turning: false, is_crossover: false, narrative_order: 5, story_time: 'Năm 1, ngày 7' },
    { id: 'e6', arc_id: 'a2', chapter_id: 'ch7', title: 'Học kiếm cơ bản', description: 'LTV bắt đầu luyện Thanh Vân kiếm pháp.', characters: ['c-ltv', 'c-suphu', 'c-shA'], importance: 'minor', type: 'character', is_turning: false, is_crossover: false, narrative_order: 6, story_time: 'Năm 1, tháng 1' },
    { id: 'e7', arc_id: 'a2', chapter_id: 'ch8', title: 'Mâu thuẫn với Lưu sư huynh', description: 'LTV bị sư huynh Lưu Chí thử thách, bị chèn ép.', characters: ['c-ltv', 'c-shA'], importance: 'minor', type: 'character', is_turning: false, is_crossover: false, narrative_order: 7, story_time: 'Năm 1, tháng 2' },
    { id: 'e8', arc_id: 'a2', chapter_id: 'ch10', title: 'Tỉ thí nội môn', description: 'LTV đánh bại sư huynh Lưu Chí trong tỉ thí, gây kinh ngạc cho toàn phái.', characters: ['c-ltv', 'c-shA', 'c-suphu'], importance: 'major', type: 'plot', is_turning: false, is_crossover: false, narrative_order: 8, story_time: 'Năm 1, tháng 6' },
    { id: 'e11', arc_id: 'a2', chapter_id: 'ch15', title: 'Gặp Trần Như Hoa', description: 'Trần Như Hoa đến Thanh Vân Sơn cầu kiếm pháp, gặp LTV.', characters: ['c-ltv', 'c-tnh'], importance: 'major', type: 'character', is_turning: false, is_crossover: false, narrative_order: 9, story_time: 'Năm 2, đầu xuân' },
    { id: 'e12', arc_id: 'a2', chapter_id: 'ch15', title: 'Đột phá Trúc Cơ', description: 'LTV đột phá tới cảnh giới Trúc Cơ, mở khóa thiên phú ẩn giấu.', characters: ['c-ltv', 'c-suphu', 'c-tnh'], importance: 'major', type: 'plot', is_turning: true, is_crossover: false, narrative_order: 10, story_time: 'Năm 2, tháng 2' },

    { id: 'e13', arc_id: 'a3', chapter_id: 'ch16', title: 'Phát hiện bí cảnh', description: 'LTV vô tình tìm ra cửa vào Hư Cảnh thượng cổ.', characters: ['c-ltv', 'c-tnh'], importance: 'major', type: 'plot', is_turning: false, is_crossover: false, narrative_order: 11, story_time: 'Năm 2, tháng 3' },
    { id: 'e14', arc_id: 'a3', chapter_id: 'ch18', title: 'Gặp Tô Ngọc trong bí cảnh', description: 'LTV và Tô Ngọc giáp mặt — Tô Ngọc cũng vào tìm bảo vật.', characters: ['c-ltv', 'c-tongoc', 'c-tnh'], importance: 'major', type: 'plot', is_turning: false, is_crossover: true, narrative_order: 12, story_time: 'Năm 2, tháng 4' },

    { id: 'e15', arc_id: 'a5', chapter_id: 'ch14', title: 'Tô Ngọc được phong Khâm Thiên Giám', description: 'Hoàng đế phong Tô Ngọc làm Khâm Thiên Giám. Bắt đầu nắm thiên cơ.', characters: ['c-tongoc'], importance: 'major', type: 'plot', is_turning: true, is_crossover: false, narrative_order: 13, story_time: 'Năm 2, tháng 1' },
    { id: 'e16', arc_id: 'a6', chapter_id: 'ch15', title: 'Phát hiện âm mưu phế đế', description: 'Tô Ngọc đọc thiên cơ, biết có người muốn phế đế.', characters: ['c-tongoc'], importance: 'major', type: 'plot', is_turning: false, is_crossover: false, narrative_order: 14, story_time: 'Năm 2, tháng 2' },
    { id: 'e17', arc_id: 'a7', chapter_id: 'ch18', title: 'Huyết Tổ tỉnh giấc', description: 'Phong ấn ngàn năm bị phá. Huyết Tổ thoát ra.', characters: ['c-huyetto'], importance: 'major', type: 'world', is_turning: false, is_crossover: false, narrative_order: 15, story_time: 'Năm 2, tháng 4' },
  ];

  // causality
  const causality = [
    { from: 'e1', to: 'e2' },
    { from: 'e2', to: 'e3' },
    { from: 'e3', to: 'e4' },
    { from: 'e4', to: 'e5' },
    { from: 'e5', to: 'e6' },
    { from: 'e6', to: 'e7' },
    { from: 'e7', to: 'e8' },
    { from: 'e8', to: 'e12' },
    { from: 'e6', to: 'e12' },
    { from: 'e11', to: 'e12' },
    { from: 'e12', to: 'e13' },
    { from: 'e13', to: 'e14' },
    { from: 'e15', to: 'e16' },
    { from: 'e16', to: 'e17' },
  ];

  const chapters = [
    { id: 'ch1', order: 1, title: 'Chương 1: Rời thôn', word_count: 3210, status: 'finalized', summary: 'LTV chôn cất mẹ, rời thôn Thanh Khê.' },
    { id: 'ch2', order: 2, title: 'Chương 2: Truy sát', word_count: 2890, status: 'finalized', summary: 'LTV bị sát thủ áo đen tấn công.' },
    { id: 'ch3', order: 3, title: 'Chương 3: Lão nhân', word_count: 3104, status: 'finalized', summary: 'Lão nhân áo trắng cứu LTV.' },
    { id: 'ch4', order: 4, title: 'Chương 4: Thanh Vân Sơn', word_count: 2750, status: 'finalized' },
    { id: 'ch5', order: 5, title: 'Chương 5: Sói Trắng', word_count: 3402, status: 'finalized' },
    { id: 'ch6', order: 6, title: 'Chương 6: Bái sư', word_count: 2980, status: 'finalized' },
    { id: 'ch7', order: 7, title: 'Chương 7: Kiếm pháp', word_count: 3120, status: 'finalized' },
    { id: 'ch8', order: 8, title: 'Chương 8: Lưu sư huynh', word_count: 2840, status: 'finalized' },
    { id: 'ch9', order: 9, title: 'Chương 9: Khổ luyện', word_count: 2900, status: 'finalized' },
    { id: 'ch10', order: 10, title: 'Chương 10: Tỉ thí', word_count: 3500, status: 'finalized' },
    { id: 'ch11', order: 11, title: 'Chương 11: Vinh dự', word_count: 2700, status: 'finalized' },
    { id: 'ch12', order: 12, title: 'Chương 12: Tu vi tăng tiến', word_count: 2860, status: 'finalized' },
    { id: 'ch13', order: 13, title: 'Chương 13: Bí ẩn núi', word_count: 3050, status: 'finalized' },
    { id: 'ch14', order: 14, title: 'Chương 14: Triều đình động', word_count: 2950, status: 'finalized' },
    { id: 'ch15', order: 15, title: 'Chương 15: Đột phá', word_count: 4120, status: 'finalized' },
    { id: 'ch16', order: 16, title: 'Chương 16: Bí cảnh hé lộ', word_count: 3210, status: 'finalized' },
    { id: 'ch17', order: 17, title: 'Chương 17: Vào Hư Cảnh', word_count: 2890, status: 'finalized' },
    { id: 'ch18', order: 18, title: 'Chương 18: Đối mặt Tô Ngọc', word_count: 3640, status: 'draft' },
    { id: 'ch19', order: 19, title: 'Chương 19: Liên minh tạm thời', word_count: 1240, status: 'draft' },
  ];

  const traits = [
    { id: 't1', character_id: 'c-ltv', kind: 'item', name: 'Thanh Vân kiếm cũ', acquired_event: 'e1', lost_event: null, description: 'Thanh kiếm di vật của cha' },
    { id: 't2', character_id: 'c-ltv', kind: 'skill', name: 'Thanh Vân kiếm pháp', acquired_event: 'e6', lost_event: null, description: 'Kiếm pháp trấn phái', version: 'Cấp 3' },
    { id: 't3', character_id: 'c-ltv', kind: 'ability', name: 'Thiên phú ẩn — Thanh Đế thể', acquired_event: 'e12', lost_event: null, description: 'Bộc lộ khi đột phá Trúc Cơ' },
    { id: 't4', character_id: 'c-ltv', kind: 'status', name: 'Vết thương cũ ở vai', acquired_event: 'e2', lost_event: 'e5', description: 'Bị sát thủ đả thương' },
    { id: 't5', character_id: 'c-tongoc', kind: 'ability', name: 'Đọc thiên cơ', acquired_event: 'e15', lost_event: null, description: 'Khả năng quan sát mệnh trời' },
  ];

  const relationships = [
    { from: 'c-ltv', to: 'c-suphu', type: 'mentor', label: 'Sư đồ', started_at: 'e5', progressions: [{ event: 'e5', status: 'sư đồ' }] },
    { from: 'c-ltv', to: 'c-mother', type: 'family', label: 'Mẹ con', started_at: null, progressions: [] },
    { from: 'c-ltv', to: 'c-tnh', type: 'romance', label: 'Bạn → Người yêu', started_at: 'e11', progressions: [{ event: 'e11', status: 'gặp lần đầu' }, { event: 'e13', status: 'đồng hành' }] },
    { from: 'c-ltv', to: 'c-shA', type: 'rival', label: 'Đồng môn (cạnh tranh)', started_at: 'e7', progressions: [{ event: 'e7', status: 'mâu thuẫn' }, { event: 'e8', status: 'tôn trọng' }] },
    { from: 'c-ltv', to: 'c-tongoc', type: 'ally', label: 'Liên minh tạm', started_at: 'e14', progressions: [{ event: 'e14', status: 'gặp lần đầu' }] },
    { from: 'c-ltv', to: 'c-killer', type: 'enemy', label: 'Kẻ thù', started_at: 'e2', progressions: [{ event: 'e2', status: 'truy sát' }] },
    { from: 'c-suphu', to: 'c-shA', type: 'mentor', label: 'Sư đồ', started_at: null, progressions: [] },
  ];

  return { storylines, arcs, characters, events, causality, chapters, traits, relationships };
})();
