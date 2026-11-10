# EP02 — Rà soát kịch bản trước sản xuất

Nguồn: `output/The Preacher's Satchel/source/EPISODES/EP02_FULL.md`. Bản nguồn giữ nguyên; bản sản xuất ở `output/preachers_satchel_ep02/`.

## Kết quả

- Từ 160 shot nguồn còn 136 shot sản xuất, giữ chuỗi sự kiện chính; bỏ 24 shot việc nhà/đoạn kết lặp.
- Khoảng 2.758 từ, lời dẫn khoảng 29%, phần còn lại thành đối thoại có speaker trên hình. Thời lượng phải đo bằng giọng thực tế, không lấy 10 giây/shot làm cam kết.
- Mở bằng ghế bị phá để sưởi lợn, thông báo bán trại, hạn chót và câu hỏi treo; sau đó đánh dấu trở về buổi sáng trước đó.
- Sửa các mâu thuẫn: note người vợ có trước khi mất; ba loại giấy và bản sao tranh chấp không bị nhập làm một; Cheyenne là hồi ức; Rigg được nhờ đối chiếu sổ công chứng rồi quay lại sau ba ngày; huyện ghi ngày hiện tại; phân biệt giấy gốc được trả lại và giấy được lưu; đi/về có nghỉ; học đọc qua nhiều tuần/tháng; ghế dùng chân mới; bếp lạnh cho tới sau khi sửa ống khói.
- Bổ sung clerk, lawyer và vai Hattie thật sự xuất hiện; 7 nhân vật có mô tả cố định.
- 136/136 cảnh khớp storyboard và visual plan. 14 mẫu đã gán cảnh: 6 địa điểm và 8 đồ vật/con vật. Dự toán tối đa 4 ảnh tham chiếu/request. Mẫu còn thiếu ảnh, chưa duyệt.

## Kiểm định

- Muse đánh giá đầy đủ bản sau sửa: 90/100, còn một mâu thuẫn nơi giữ giấy tờ và hai minor. Đã sửa cả ba; Muse kiểm lại các sửa đổi và xác nhận PASS — 98/100. Đây là điểm kiểm lại các mục đã sửa, không giả là chấm lại toàn bộ video.
- Tự soát cuối của Codex: 90/100, pass kịch bản, ghi vào `script_reviews.json` để hiện trên app. Không phải duyệt thay người dùng.
- `storyvid.check scenes.json`: đạt, không thiếu asset catalog.
- `storyvid.check --visuals visuals.json`: đạt, 0/136 clip (chưa tạo hình).
- `storyvid.check --assets`: đạt, 134 assets / 22 extra characters.
- Bộ tests hiện tại: 128 tests đạt. Không sửa code trong bước rà soát nội dung này.

## Cổng tiếp theo

Người thật đọc và bấm **Duyệt kịch bản** cho bản hiện tại trên app. Agent không ghi `approved_script`, `approved_cast` hay duyệt bộ mẫu thay người.

Sau khi có duyệt kịch bản: tạo 4 mẫu nhân vật còn thiếu, dùng lại mẫu Elias/Rigg/Hattie; tạo mẫu địa điểm/đồ vật theo mô tả và đối chiếu kiến trúc ngoài–trong; người thật duyệt mẫu; chạy 3–5 cảnh thử ảnh/clip; kiểm đầu–giữa–cuối và các góc cùng nơi; khi đạt mới chạy các lô còn lại, dựng 1080p, chuẩn hóa âm lượng, kiểm máy và kiểm nội dung.

Chưa có video EP02. Chưa kiểm giọng/nhịp/âm thanh thật hoặc nhóm cảnh thử. Báo cáo chi tiết và bản đọc nằm ở `SCRIPT_REVIEW.md`, `script_readable.md`, `continuity.md`, `source_map.json` trong thư mục EP02.
