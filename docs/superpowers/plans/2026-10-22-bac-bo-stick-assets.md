# Bắc Bộ Stick Assets Implementation Plan

**Goal:** Bàn giao bộ assets hoàn chỉnh theo mẫu 10 đã chọn.

**Architecture:** Thư viện SVG độc lập dùng cùng hợp đồng rig hiện tại;
`Character(..., asset_root=...)` chọn thư viện riêng. Công cụ build xuất
PNG, preview, manifest và ZIP, không ghi đè dữ liệu dự án.

**Tech Stack:** Python, SVG, Pillow, resvg-py, ffmpeg.

## Công việc (thực hiện trực tiếp trong phiên)

- [x] Viết test tải thư viện tùy chọn, chạy xác nhận lỗi trước khi thêm tham số.
- [x] Thêm tham số keyword `asset_root` cho Character; kiểm tra thư viện cũ.
- [x] Viết `tools/build_bac_bo_assets.py`: 8 rig tách mảnh, 9 động vật,
      19 đạo cụ/trang phục, 8 cảnh ngày/đêm, hiệu ứng truyện tranh.
- [x] Viết `tools/export_bac_bo_assets.py`: PNG, SVG ghép, biểu cảm/tư thế,
      contact sheets, HTML và clip mẫu; xuất `output/bac-bo-stick/`.
- [x] Chạy `.venv/bin/python -m unittest discover -s tests -v`, kiểm tra
      XML và alpha PNG, decode MP4 bằng ffmpeg, xem gallery và khung clip.
- [x] Đóng gói ZIP, ghi hướng dẫn và manifest số lượng thực tế.
