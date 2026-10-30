# Stung Treng — Codex, vòng kiểm định 1

Không chỉnh review.json; verdict vẫn là fix, chờ Claude kiểm định lại. Không sửa storyvid/ hay asset gốc ngoài extra/.

## Chín mục

1. Cast: đổi đúng 10 preset stung_*; giữ nguyên woman/mother/child và các thuộc tính cast khác.
2. Cảnh gốc 4: tách lời narrator và woman; cảnh lời woman dùng zoom_in. short.scenes đổi thành 0–7. Bảng scene-map.json đối chiếu chỉ số gốc và mới, đếm từ 0.
3. Bảy nền extra ban ngày đang dùng: giảm bão hòa, tối màu, thêm mây xám và mảng bóng vector; giữ mã. Cảnh gốc 16–17 dùng camp_yard_night. Cảnh địa danh sông chuyển river_night vì lời không chỉ thời điểm; không sửa river_day của bộ gốc. Đăng ký/cập nhật manifest và catalog.
4. Cảnh gốc 72–77: Luc trái, Tung xa trái, mother giữa; bỏ prop sleepers_on_mat trùng nhân vật. 75/78/79 dùng zoom_in; 79 chỉ child ở giữa. Mother dùng cower để thấp xuống. Đã dựng ảnh kiểm tra: ma nhỏ và mờ vẫn chưa đạt cận cảnh thật sự, đặc biệt child; yêu cầu phóng lớn đã dùng hết camera chuẩn, không tự đổi code hoặc preset ma đã yêu cầu giữ nguyên. Cần Claude/người dùng kiểm định lại; có thể cần sửa renderer theo owner tool.
5. Điếu thuốc: vẽ lại SVG lớn, đầu đỏ/cam sáng và lõi vàng nhạt, đường khói; height 0.30, giữa khung. Cảnh gốc 36 thêm me trái, bay xa trái, scared. Ảnh preview thấy đỏ và khói; khi không có actors, zoom vẫn có thể cắt phần đá ở mép dưới.
6. Cảnh gốc 68: mr_chan trái, ghost_boy center, cower, không approach. Schema chỉ có center/left/right/far_left/far_right, không có center-right hoặc lớp độ sâu. Đã dùng center là vị trí hợp lệ gần ý review nhất; không thể thể hiện chiều sâu chính xác qua schema hiện tại.
7. Cảnh gốc 112: bỏ prop binoculars nằm dưới đất, giữ reach.
8. Tên riêng: danh sách đầy đủ trong pronunciation.md. Chưa có đánh giá nghe phát âm của người dùng; không tự thay tên bằng phiên âm khi chưa xác nhận đọc sai.
9. Chèn nhịp một từ trước cảnh gốc 44/74/155, ở chỉ số mới 45/76/158. Dùng “Wait.”, “Then…” theo lựa chọn nhịp một từ trong review. Không dùng dòng trống vì chuẩn bắt buộc text không rỗng và 1–6 dòng. Đây là nhịp lời ngắn, chưa phải khoảng im hoàn toàn; đã bỏ sfx khỏi nhịp và không phô chủ thể trước reveal.

## Checklist 1–7

- Validator scenes/assets/review: exit 0. Review vẫn fix với 9 issue nguyên văn.
- Unit tests: 52 tests, OK (tests.log).
- Nhịp đo bằng giọng Edge: không có cảnh >8 giây bắt đầu trong phút đầu; không có cảnh >12 giây. Tổng bản dài 1313.8 giây; Short 34.5 giây, kết hỏi, mở bằng ma, không intro ban ngày trước hook.
- Truyện, lời: giữ tuyến cầu cứu, dấu hiệu lạ, cấm vào khu mìn, đi tìm hài cốt, chôn cất và kết; giữ niềm tin quy về gia đình Chan, không thêm luật ma hoặc khẳng định lịch sử.
- Nền và cast đã xem qua assets-contact.jpg và staging-contact.jpg. Các cảnh ban ngày đã u ám, người dùng cần chấm lại tiêu chí không nhầm hoạt hình thiếu nhi do phong cách SVG được duyệt vốn là nhân vật cách điệu.
- Short: render 1080×1920 không fallback hoàn tất, có video_short.srt; xem khung 16 giây thấy đầy khung và ma lớn. Header bị cắt cuối tiêu đề dài, mất “Ghost Story” trên hình: lỗi trình bày renderer, cần owner tool; không tự đổi title người dùng đã duyệt.
- Chưa nghe toàn bộ giọng/mix hoặc soát từng cue SRT; chưa khẳng định phát âm, mức âm, đồng bộ SFX hay mọi ngắt dòng phụ đề đạt. Các khung preview chẩn đoán dùng timeline im lặng rút gọn, không thay thế video cuối.
- Các mục chưa đạt/chưa xác minh: ma child đủ lớn/rõ, staging chân người và ma, chiều sâu phía sau mr_chan, tiêu đề Short trọn chữ, đánh giá phong cách horror khi tắt tiếng, nghe tên riêng/toàn bộ âm thanh, phụ đề và SFX. Không tuyên bố video sẵn sàng đăng.

## Người dùng

Phần 8–9: quyền/ghi công nguồn, thumbnail riêng, tải 1080p và SRT, Related video, cài đặt đối tượng; xem lại CTR/retention/đề xuất sau 48 giờ.
