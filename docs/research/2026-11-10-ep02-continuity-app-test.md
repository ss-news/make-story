# Kiểm thử khóa mẫu trên app với nguồn EP02 — 2026-11-10

Nguồn riêng của dự án: `output/The Preacher's Satchel/source/EPISODES/EP02_FULL.md`.
Không sửa nguồn, không duyệt kịch bản/nhân vật/bộ mẫu cho EP02 thật, không gọi Muse hoặc TTS.

## Kết quả ánh xạ nguồn

160 shot, 160 dòng Voice; đủ số cảnh 1–160, mỗi cảnh gán đúng một set theo Bối cảnh của nguồn.
Nguồn khai báo 6 set nhưng chỉ dùng 5: VOSS YARD 40 cảnh, VOSS HOUSE 45, COURTHOUSE 42, ROAD 24, VOSS GRAVE 9. COTTONWOOD STORE không có cảnh sử dụng; không tự gán hoặc tạo hình set thừa.

## Kiểm thử backend trên bản sao dùng một lần

`tests/test_continuity_ep02.py` chuyển shot list nguồn thành dữ liệu test đúng schema. Ảnh mẫu là bảng ghi TEST ONLY, đầu ra tạo hình/clip được giả lập; không phải asset hoặc video sản xuất.

- Cảnh 1 và 2 nhận cùng ảnh tham chiếu VOSS YARD.
- Thử các cảnh 1, 2, 27, 43, 53, 57, phủ cả 5 set đang dùng và bếp gang là prop lặp lại.
- Ảnh mẫu và mô tả khóa đi vào cả yêu cầu ảnh và clip, không quá 4 ảnh mỗi yêu cầu.
- API trả 409 khi chưa duyệt bộ mẫu; auto dừng trước tạo cảnh.
- Duyệt bộ mẫu mở luồng tạo; API hỗ trợ chọn nhiều cảnh, từ chối số cảnh sai hoặc chuỗi không hợp lệ thay vì chạy cả video.
- Đổi mô tả VOSS YARD làm mất duyệt và đánh dấu các kết quả liên quan cũ; kết quả set độc lập không bị đánh dấu cũ.
- Test tổng quát bổ sung: ảnh đổi cùng dung lượng; ảnh thiếu/đường dẫn sai; quá ngân sách ảnh; thay ảnh mở làm clip cũ; mẫu đổi trong lúc sinh ảnh; panel địa điểm cũ cũng gửi ảnh vào clip.

## Kiểm thử giao diện

Trong dự án TEST EP02 tạm: mở tab Hình Muse, xem mẫu và cách gán cảnh, bấm Duyệt bộ mẫu. Xác nhận nút tạo ảnh được mở. Đổi mô tả nhà: nút ảnh/clip/auto khóa ngay. Lưu và tải lại: trạng thái chưa duyệt vẫn giữ. Không thấy lỗi JavaScript trong luồng này.

## Xác minh

- `.venv/bin/python -m unittest discover -s tests`: 128 tests, OK.
- `node --check storyvid/web/static/app.js`: đạt.
- `git diff --check`: đạt.
- AGENTS.md và CLAUDE.md giống nhau.

## Giới hạn

Đây là kiểm thử quy trình, tham chiếu, dữ liệu và cổng duyệt; chưa đo khả năng Muse thực sự giữ kiến trúc/mặt/đồ vật. EP02 thật vẫn cần người duyệt kịch bản, mẫu nhân vật và ảnh địa điểm/đồ vật; sau đó chạy nhóm thử bằng ảnh thật, xem đầu–giữa–cuối clip rồi mới chạy hàng loạt. Cổng duyệt nhóm thử và chấm hình vẫn thủ công.

Dự án/video cũ không bị xóa. Do chuyển từ kiểm dung lượng sang băm nội dung ảnh, ảnh nhân vật cũ cần duyệt lại trước lần tạo cảnh mới; các đầu ra chưa có dấu vết được hiển thị là cũ/chưa kiểm chứng, không tự được xác nhận đạt.
