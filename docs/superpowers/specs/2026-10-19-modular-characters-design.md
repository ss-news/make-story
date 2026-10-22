# Nhân vật Việt Nam tách mảnh

Đã duyệt trong chat: nhân vật chàng trai làng Việt, SVG tách mảnh, biến thể theo video. Mở rộng theo yêu cầu: nữ trẻ, ông bà, trẻ em, người trung niên.

## Phạm vi
Tám mẫu: nam trẻ, nữ trẻ, ông, bà, bé trai, bé gái, nam trung niên, nữ trung niên. Phong cách hoạt hình 2D với da nâu ấm, tóc tự nhiên, trang phục đời thường. Mỗi mẫu có SVG riêng cho đầu, tóc sau/trước, cổ, thân áo, tay trên/dưới, bàn tay, chân trên/dưới, giày dép và phụ kiện. Mắt, mày, miệng động được ghép riêng khi chạy.

Mảnh dùng tọa độ cục bộ và điểm neo trong manifest; renderer đặt và xoay tại khớp. Sáu tư thế, bảy biểu cảm, ba trạng thái miệng và chớp mắt phải còn hoạt động. Chiều cao trẻ em và người già khác người lớn nhưng cùng mặt đất.

## Dữ liệu
`channel.host` giữ cấu hình mặc định. `scenes.json.character` lưu lựa chọn cho từng video: preset, outfit, accessory và màu tùy chọn. Thiếu trường mới dùng mặc định tương thích dữ liệu cũ. Lưu và chuẩn hóa không được làm mất lựa chọn. Không thay nhân vật giữa các cảnh.

## Giao diện
Bộ chọn nhân vật, trang phục, phụ kiện trên tab Kịch bản; xem trước cập nhật và lưu cùng kịch bản. API options cung cấp danh mục. Preview chấp nhận character riêng bên cạnh host. Có bảng ảnh cả tám mẫu và bộ mảnh xuất ra để kiểm tra.

## Kiểm chứng
Kiểm thử bảo toàn dữ liệu, lựa chọn sai, cách ly biến thể, tám mẫu và mọi tư thế, PNG trong suốt, điểm neo và preview API. Dựng video ngắn offline với âm thanh tổng hợp, xem ảnh và kiểm tra giao diện trình duyệt. Không ghi đè MP4 cũ. Thư mục không có Git nên không tạo commit.
