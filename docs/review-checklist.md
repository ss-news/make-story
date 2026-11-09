# Checklist review video

Bắt buộc cho cả hai agent: Claude soát khi chia cảnh (phần 2–5, 7) và khi kiểm định (phần 1–7); Codex tự soát phần 1–7 trước khi bàn giao `scenes.json` hoặc asset. Phần 8–9 do người dùng làm trước và sau khi đăng. Mỗi mục không đạt ghi thành một issue trong `output/<id>/review.json`, cột "area" là giá trị `area` cần dùng. Mục có dấu ★ rút ra từ số liệu Ma Lon (`docs/research/2026-10-28-ma-lon-analytics.md`): không đạt thì tối thiểu `major`. Mục ghi *(truyện ma)*, *(đời thường)* hay *(kiến thức)* chỉ áp cho loại video đó (`meta.json` `genre`); mục không ghi áp cho mọi loại.

## 1. Kiểm tra máy

- [ ] `.venv/bin/python -m storyvid.check output/<id>/scenes.json` ra 0
- [ ] `.venv/bin/python -m storyvid.check --assets` ra 0
- [ ] Dựng được `video.mp4` và `video_short.mp4` không dùng `--fallback`

## 2. Mở đầu (xem 30 giây đầu, tắt tiếng một lần, bật tiếng một lần)

| | Mục | area |
|---|---|---|
| [ ] ★ | Giây đầu tiên đã là khoảnh khắc mạnh nhất: *(truyện ma)* cảnh đáng sợ hoặc lạ nhất; *(đời thường)* lúc mâu thuẫn lên đỉnh; *(kiến thức)* câu hỏi hoặc điều bất ngờ | story |
| [ ] ★ | Chủ thể chính to, rõ, nằm giữa khung (không nhỏ ở góc) | staging |
| [ ] ★ | 30 giây đầu không có đoạn tả bối cảnh dài trước khi có chuyện; *(truyện ma)* không tả làng, cảnh ban ngày trước khi có điều lạ | story |
| [ ] ★ | 30 giây đầu kết bằng một câu hỏi hoặc câu lửng khiến người xem muốn biết tiếp | story |
| [ ] ★ | Trong 60 giây đầu không cảnh nào giữ một hình quá 8 giây | pacing |
| [ ] | Mở đầu khớp đúng điều thumbnail và tiêu đề hứa | story |

## 3. Hình ảnh và không khí

| | Mục | area |
|---|---|---|
| [ ] ★ | Tắt tiếng xem 3 khung hình bất kỳ: nhìn ra ngay đúng loại video (truyện ma, đời thường hay kiến thức), không nhầm với hoạt hình thiếu nhi | render |
| [ ] ★ | *(truyện ma)* Cảnh ma, cảnh đêm có nền tối và bóng đổ | background |
| [ ] ★ | Biểu cảm nhân vật khớp cảm xúc cảnh: *(truyện ma)* sợ, căng thẳng, không mang vẻ hài; *(đời thường)* cảm xúc thật, không sến | character |
| [ ] | Nền và đồ vật khớp nơi chốn, thời điểm (ngày/đêm) | background / props |
| [ ] | Ai đứng đâu, hướng nhìn, hành động khớp lời thoại | staging |
| [ ] | Không có lỗi dựng hình: chồng chéo, lệch, mất nhân vật, đồ vật trôi | render |

## 4. Truyện và lời

| | Mục | area |
|---|---|---|
| [ ] | *(truyện ma)* Có giải thích luật của con ma hoặc điều kiêng kỵ của làng | story |
| [ ] | Có 3–4 nấc leo thang, cao trào rõ, kết có dư âm | story |
| [ ] | *(truyện ma)* Có đoạn giải thích văn hóa (con ma là gì, vì sao làng kiêng), đúng chi tiết Việt | story |
| [ ] | *(đời thường)* Có bước ngoặt nhân vật phải chọn, kết thúc cho thấy hệ quả của lựa chọn đó; không giảng đạo | story |
| [ ] | Có nhân vật chính với mục tiêu và trở ngại rõ; mỗi cảnh phim có xung đột và kết bằng bước ngoặt | story |
| [ ] | Cho xem thay vì kể: điều thấy được nằm trên hình, lời dẫn không quá khoảng 40% số chữ, không 3 cảnh liền chỉ có lời dẫn trên nền trống | story |
| [ ] | Cỡ cảnh thay đổi (không ba shot cùng cỡ liền nhau), đỉnh cảm xúc ở cận cảnh, có shot phản ứng sau cú sốc | staging |
| [ ] | Các cảnh nối liền như một bộ phim: cảnh mới có câu nối (thời gian, âm thanh, hành động mang sang), shot sau bắt đầu từ khung cuối shot trước, giữ hướng màn hình và hướng nhìn | staging |
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
| [ ] ★ | Không mất hình: clip 16:9 hiện trọn (không bị cắt mép), không có dải đen lớn, chủ thể to nhất có thể | render |
| [ ] ★ | Logo, tiêu đề, phụ đề và nút cuối nằm trong vùng an toàn: dưới thanh trên của app, trên 80 % chiều cao, cách mép phải 12 % | render |
| [ ] ★ | Giây đầu là cảnh gây sốc, không phải khung cảnh trống | story |
| [ ] | Dài 30–60 giây, kết lửng | pacing |

## 7b. Video hình AI (Muse) và video kiến thức

Bước 1 và 2 của tab Hoàn thành (`docs/pipeline.md`, mục “Hoàn thành video”) tự làm phần lớn các mục này; agent kiểm định đọc lại kết quả và bổ sung.

| | Mục | area |
|---|---|---|
| [ ] | `python -m storyvid.finish check output/<id>` đạt hết (bản kịch bản đã duyệt, đủ clip, 1080p, âm lượng, khoảng lặng, phụ đề) | render |
| [ ] | Khung hình từng cảnh khớp lời kể; nhân vật chính giữ đúng ngoại hình ảnh mẫu | character |
| [ ] | Không có chữ méo, logo, tay chân dị dạng trong hình | render |
| [ ] | Ẩn dụ hình không lặp quá nhiều (một kiểu hình không quá 1/10 số cảnh) | staging |
| [ ] | Video kiến thức: mọi số liệu, kết quả nghiên cứu và trích dẫn đã đối chiếu nguồn; câu chưa chắc nói rõ là “theo X kể lại” | story |
| [ ] | Nội dung sức khỏe có câu lưu ý không thay thế lời khuyên chuyên môn | story |

## 8. Trước khi đăng (người dùng làm, không ghi vào review.json)

- [ ] ★ Thumbnail riêng (2–3 phương án nếu dùng Test & Compare): một chủ thể thật to, cảm xúc rõ, một màu nhấn, chữ tối đa 3–4 từ; *(truyện ma)* nền tối, chủ thể đáng sợ; *(đời thường)* gương mặt nhân vật chính với cảm xúc mạnh
- [ ] ★ Tải bản 1080p gốc, không dùng bản nén
- [ ] ★ Tải phụ đề SRT
- [ ] ★ Không đánh dấu "dành cho trẻ em"
- [ ] Tiêu đề có từ khóa đúng loại video (*(truyện ma)* "Vietnamese" + "ghost/folklore"), không nói quá nội dung
- [ ] Mô tả: 2 dòng đầu có từ khóa và hook; chapters; ghi công nhạc và âm thanh (gói đăng ở tab Hoàn thành đã soạn sẵn, sửa lại nếu cần)
- [ ] Video hình AI: giữ ghi chú hình AI trong mô tả; chỉ bật nhãn “nội dung đã thay đổi hoặc tổng hợp” khi hình trông như người hoặc sự kiện thật
- [ ] Đánh dấu “Đã đăng” và dán link ở tab Hoàn thành
- [ ] Short công khai, gắn Related video về bản dài
- [ ] Thêm vào playlist; end screen trỏ video khác
- [ ] Nếu có: tải bản âm thanh tiếng Việt (multi-language audio)

## 9. Sau 48 giờ

- [ ] Đọc CTR (mục tiêu ≥ 3%), thời lượng xem trung bình và đường giữ chân
- [ ] Xem mục "Nội dung giúp người xem tìm thấy video này": YouTube có ghép đúng nhóm video cùng loại không
- [ ] Ghi số liệu và bài học vào `docs/research/`
