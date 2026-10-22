# Người que vẽ tay — Làng quê Bắc Bộ / Mẫu 10

Bộ assets theo hướng người dùng chọn ngày 22/10/2026: đầu lớn, mặt trắng,
thân áo nhỏ, tay chân nét đơn, màu phẳng và biểu cảm cường điệu. Hình ảnh
là diễn giải hoạt hình làng quê Bắc Bộ; không phải phục dựng phục trang
lịch sử và không dùng nhân vật/logo có sẵn của kênh tham chiếu.

## Xem nhanh

Mở `index.html` bằng trình duyệt. Có bộ lọc nhóm, liên kết SVG/PNG và clip.
`scene-preview.png` là cảnh ghép thử. `cast-gallery.png` là 8 nhân vật.
Các file `*-sheet.png` là bảng toàn bộ biểu cảm, động vật, đạo cụ, nền, hiệu ứng.
`motion-demo.mp4`: 24 giây, 960×540, 15 fps, H.264; kiểm tra nhép miệng,
chớp mắt, bước chân, tay, lật hình. Clip không có lời kể.

## Nội dung

| Nhóm | Số lượng | Dạng |
|---|---:|---|
| Nhân vật | 8 | Rig tách mảnh; SVG nguồn + PNG mảnh + SVG/PNG ghép |
| Động vật | 9 | SVG + PNG trong suốt |
| Đạo cụ / trang phục | 19 | SVG + PNG trong suốt |
| Cảnh nền | 16 | 8 cảnh × ngày/đêm; SVG 1600×900 + PNG 1920×1080 |
| Hiệu ứng | 8 | SVG + PNG trong suốt |

Mỗi nhân vật có 9 tư thế, 4 trạng thái bước chân, 7 biểu cảm, ảnh chớp mắt
và 3 mức miệng. `sources/characters/<preset>/` chứa 39 mảnh SVG và rig.
`characters/<preset>/` chứa các bản đã xuất (440px chiều cao khung ảnh).
PNG độc lập cho động vật/đạo cụ/hiệu ứng có khung 960×720. Lề trong suốt
được giữ để tiện đặt và xoay hình. Động vật và đạo cụ là hình tĩnh, chưa có
rig chuyển động riêng. Các trang phục rời là asset để ghép, không tự đổi
qua bộ chọn trang phục hiện tại của web UI.

## Nguồn và chỉnh sửa

- `sources/manifest.json`: danh mục nguồn và bảng màu.
- `manifest.json`: danh mục kèm đường dẫn PNG và số lượng.
- `sources/characters/<preset>/rig.json`: pivot, vị trí khớp, chiều dài tay chân.
- SVG nhân vật dùng biến `{{shirt}}`; đặt màu khi raster hóa/ghép bằng loader.
  SVG ghép trong `characters/` đã thay màu và mở được độc lập.
- Mặt giữ màu trắng theo mẫu 10; chỉnh `head.svg` nếu muốn đổi.
- Các nhóm SVG riêng có thể sửa trong Inkscape, Illustrator hoặc trình soạn thảo.
- Hai công cụ build/export ghi đè file của bộ mới khi chạy lại. Nếu sửa tay,
  sao lưu nguồn hoặc sửa công cụ trước khi build. Không chạy lại builder cũ
  để tái tạo bộ này.

## Dùng trong Storyvid

Bộ cũ và các dự án đã lưu được giữ nguyên. Bộ mới được bàn giao như một
thư viện độc lập; chưa tự chọn trong UI hiện tại. Loader `Character` hỗ trợ
đường dẫn thư viện tùy chọn:

```python
from pathlib import Path
from storyvid.character import Character

root = Path('/Users/thang/Documents/video')
character = Character(
    {'preset': 'elder_man', 'outfit': 'earth', 'accessory': 'none'},
    640,
    asset_root=root / 'assets/bac-bo-stick/characters',
)
character.sprite('scared', 'surprised', 0, False, False).save('ong-lao.png')
```

Nguồn dự án: `/Users/thang/Documents/video/assets/bac-bo-stick/`.
Công cụ: `tools/build_bac_bo_assets.py`, `tools/export_bac_bo_assets.py`,
`tools/verify_bac_bo_assets.py`. Chạy từ thư mục dự án:

```sh
.venv/bin/python tools/build_bac_bo_assets.py
.venv/bin/python tools/export_bac_bo_assets.py
.venv/bin/python tools/verify_bac_bo_assets.py
```

Hướng này được vẽ trực tiếp bằng SVG để giữ mảnh và pivot chỉnh sửa được.
Không dùng ImageGen để tạo các file sản xuất. Bảng ImageGen trước đó chỉ
là bản tham chiếu mỹ thuật được người dùng lựa chọn.
