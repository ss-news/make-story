# Checklist review video

Bắt buộc cho cả hai agent: Claude soát khi chia cảnh (phần 2–5, 7) và khi kiểm định (phần 1–7); Codex tự soát phần 1–7 trước khi bàn giao `scenes.json` hoặc asset. Phần 8–9 do người dùng làm trước và sau khi đăng. Mỗi mục không đạt ghi thành một issue trong `output/<id>/review.json`, cột "area" là giá trị `area` cần dùng. Mục có dấu ★ rút ra từ số liệu Ma Lon (`docs/research/2026-10-28-ma-lon-analytics.md`): không đạt thì tối thiểu `major`.

## 1. Kiểm tra máy

- [ ] `.venv/bin/python -m storyvid.check output/<id>/scenes.json` ra 0
- [ ] `.venv/bin/python -m storyvid.check --assets` ra 0
- [ ] Dựng được `video.mp4` và `video_short.mp4` không dùng `--fallback`

## 2. Mở đầu (xem 30 giây đầu, tắt tiếng một lần, bật tiếng một lần)

| | Mục | area |
|---|---|---|
| [ ] ★ | Giây đầu tiên đã là cảnh đáng sợ nhất hoặc điều lạ nhất của truyện | story |
| [ ] ★ | Chủ thể đáng sợ to, rõ, nằm giữa khung (không nhỏ ở góc) | staging |
| [ ] ★ | 30 giây đầu không có đoạn tả làng, bối cảnh, cảnh ban ngày trước khi có điều lạ | story |
| [ ] ★ | 30 giây đầu kết bằng một câu hỏi hoặc câu lửng khiến người xem muốn biết tiếp | story |
| [ ] ★ | Trong 60 giây đầu không cảnh nào giữ một hình quá 8 giây | pacing |
| [ ] | Mở đầu khớp đúng điều thumbnail và tiêu đề hứa | story |

## 3. Hình ảnh và không khí

| | Mục | area |
|---|---|---|
| [ ] ★ | Tắt tiếng xem 3 khung hình bất kỳ: nhìn ra ngay là truyện ma, không nhầm với hoạt hình thiếu nhi | render |
| [ ] ★ | Cảnh ma, cảnh đêm có nền tối và bóng đổ | background |
| [ ] ★ | Nhân vật biểu cảm sợ, căng thẳng ở cảnh đáng sợ, không mang vẻ hài | character |
| [ ] | Nền và đồ vật khớp nơi chốn, thời điểm (ngày/đêm) | background / props |
| [ ] | Ai đứng đâu, hướng nhìn, hành động khớp lời thoại | staging |
| [ ] | Không có lỗi dựng hình: chồng chéo, lệch, mất nhân vật, đồ vật trôi | render |

## 4. Truyện và lời

| | Mục | area |
|---|---|---|
| [ ] | Có giải thích luật của con ma hoặc điều kiêng kỵ của làng | story |
| [ ] | Có 3–4 nấc leo thang, cao trào rõ, kết có dư âm | story |
| [ ] | Có đoạn giải thích văn hóa (con ma là gì, vì sao làng kiêng), đúng chi tiết Việt | story |
| [ ] | Lời thoại tự nhiên, đúng vai, đúng ngôn ngữ, không như dịch máy | dialogue |
| [ ] | Khoảng 2–3 phút có một câu kéo người xem lại (re-hook) | story |

## 5. Nhịp

| | Mục | area |
|---|---|---|
| [ ] ★ | Sau phút đầu, không cảnh nào giữ một hình quá 12 giây | pacing |
| [ ] | Không có cảnh quá ngắn đến mức không kịp đọc phụ đề | pacing |
| [ ] | Có khoảng lặng trước cảnh sợ | pacing |

## 6. Âm thanh và phụ đề

| | Mục | area |
|---|---|---|
| [ ] | Đã nghe giọng đọc: rõ, đúng nhịp, không đọc sai tên riêng | audio |
| [ ] | Nhạc và ambience nằm dưới lời đọc, không lấn | audio |
| [ ] | SFX đúng lúc, không lệch với hình | audio |
| [ ] | Phụ đề đúng lời, không ngắt dòng ở từ treo | subtitle |

## 7. Short 9:16

| | Mục | area |
|---|---|---|
| [ ] ★ | Hình đầy khung dọc, chủ thể to, không có dải đen lớn | render |
| [ ] ★ | Giây đầu là cảnh gây sốc, không phải khung cảnh trống | story |
| [ ] | Dài 30–60 giây, kết lửng | pacing |

## 8. Trước khi đăng (người dùng làm, không ghi vào review.json)

- [ ] ★ Thumbnail riêng (2–3 phương án nếu dùng Test & Compare): nền tối, một chủ thể đáng sợ thật to, một màu nhấn, chữ tối đa 3–4 từ
- [ ] ★ Tải bản 1080p gốc, không dùng bản nén
- [ ] ★ Tải phụ đề SRT
- [ ] ★ Không đánh dấu "dành cho trẻ em"
- [ ] Tiêu đề có "Vietnamese" + "ghost/folklore", không nói quá nội dung
- [ ] Mô tả: 2 dòng đầu có từ khóa và hook; chapters; ghi công nhạc và âm thanh
- [ ] Short công khai, gắn Related video về bản dài
- [ ] Thêm vào playlist; end screen trỏ video khác
- [ ] Nếu có: tải bản âm thanh tiếng Việt (multi-language audio)

## 9. Sau 48 giờ

- [ ] Đọc CTR (mục tiêu ≥ 3%), thời lượng xem trung bình và đường giữ chân
- [ ] Xem mục "Nội dung giúp người xem tìm thấy video này": YouTube có ghép đúng nhóm truyện ma không
- [ ] Ghi số liệu và bài học vào `docs/research/`
