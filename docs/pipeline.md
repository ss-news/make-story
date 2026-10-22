# Flow sản xuất video và hợp đồng giữa các agent

Mục tiêu: model nào viết kịch bản (Claude, Codex, DeepSeek, Gemini…) và agent nào vẽ asset thì đầu ra cũng theo **một chuẩn**. Mọi thứ được kiểm tra bằng máy trước khi chuyển sang bước sau.

## Vai trò

| Ai | Làm | Không làm |
|---|---|---|
| **Claude** (đọc `CLAUDE.md`) | Viết và sửa `scenes.json`, chạy kiểm tra, dựng video, sửa code tool | Không vẽ asset trong `assets/` |
| **Codex** (đọc `AGENTS.md`) | Vẽ asset thiếu theo `asset_requests.json`, đặt vào `assets/bac-bo-stick/extra/` | Không sửa `scenes.json`, code trong `storyvid/` hay bộ gốc `assets/bac-bo-stick/*` ngoài `extra/` |
| Model khác (qua `--provider`) | Viết kịch bản | Đầu ra luôn được chuẩn hóa rồi kiểm tra như mọi kịch bản khác |

## Flow

```
truyện ─► [1] viết kịch bản ─► output/<id>/scenes.json
              │
          [2] python -m storyvid.check output/<id>/scenes.json
              ├─ exit 1: kịch bản sai chuẩn ─► người viết sửa lại, quay về [2]
              ├─ exit 2: thiếu asset ─► output/<id>/asset_requests.json
              │            │
              │        [3] Codex vẽ asset vào assets/bac-bo-stick/extra/
              │            python -m storyvid.check --assets   (phải exit 0)
              │            rồi quay về [2]
              └─ exit 0 ─► [4] python -m storyvid.cli --script output/<id>/scenes.json ─► video.mp4
```

Lệnh dựng video tự chạy bước [2] và dừng nếu chưa đạt. `--fallback` chỉ dùng để xem nháp: nền thiếu được thay bằng cảnh gần nhất, đồ vật thiếu bị bỏ.

**Bước 1, hai cách viết kịch bản:**
- Để tool gọi model: `python -m storyvid.cli story.txt --lang en --provider claude|openai|codex --script-only --out output/<id>`. Đầu ra của model được chuẩn hóa (cắt giá trị lạ về giá trị hợp lệ, gắn `format`, `lang`) rồi kiểm tra.
- Agent viết thẳng file: theo `schema/scenes.v1.schema.json`. Mã asset dùng được nằm trong `schema/assets.catalog.json`.

## Hợp đồng kịch bản: `storyvid.scenes/1`

Nguồn chuẩn duy nhất là `storyvid/contract.py`. File `schema/scenes.v1.schema.json` được sinh ra từ đó. Mẫu đầy đủ: `examples/ma_da_bac_bo.scenes.json`.

```json
{
  "format": "storyvid.scenes/1",
  "title": "Tiếng gọi từ sông",
  "lang": "vi",
  "character": {"preset": "young_man", "outfit": "earth", "accessory": "none"},
  "cast": [{"id": "ba", "name": "Bà", "preset": "elder_woman", "outfit": "earth", "accessory": "scarf", "kind": "human"}],
  "scenes": [{
    "bg_id": "river_night", "bg_prompt": "dark river at night", "camera": "zoom_in",
    "actors": [{"id": "ba", "position": "left", "pose": "point", "expression": "angry", "action": "enter"}],
    "props": [{"id": "oil_lamp", "position": "far_left"}],
    "lines": [{"speaker": "ba", "text": "Buông cháu tao ra!"}]
  }]
}
```

Quy tắc (bộ kiểm tra báo lỗi kèm đường dẫn, ví dụ `$.scenes[2].actors[0].pose`):
- Đủ các trường, **không thêm trường lạ**. Chỉ `character` là tùy chọn.
- Mọi id là chữ thường không dấu: `^[a-z][a-z0-9_]*$`. `bg_id` có đuôi `_day` hoặc `_night`.
- `host` và `narrator` là id dành riêng. `host` là người dẫn chuyện đứng trên sân khấu; `narrator` là giọng kể.
- Mỗi cảnh: 0–3 diễn viên, 0–3 đồ vật, 1–6 câu thoại. Diễn viên là id trong `cast` hoặc `host`, không lặp trong một cảnh.
- `speaker` là `narrator`, hoặc một id trong `cast` **đang đứng trên sân khấu** ở cảnh đó.
- Giá trị cố định (`position`, `pose`, `expression`, `action`, `camera`, `outfit`, `accessory`, `kind`, `lang`) lấy đúng trong schema.
- `bg_id`, `props[].id` và `cast[].preset` chưa có trong bộ **không phải lỗi**: chúng thành yêu cầu asset.

## Yêu cầu asset: `storyvid.asset-requests/1`

`output/<id>/asset_requests.json` do bộ kiểm tra sinh ra. Codex chỉ đọc file này, không đoán từ kịch bản.

```json
{
  "format": "storyvid.asset-requests/1",
  "scenes_file": "output/<id>/scenes.json",
  "requests": [{
    "group": "backgrounds", "id": "bamboo_forest_night", "description": "dense bamboo forest at night",
    "scenes": [3, 4],
    "spec": {"file": "assets/bac-bo-stick/extra/backgrounds/bamboo_forest_night.svg", "viewBox": "0 0 1600 900",
             "png_alternative": "...", "rules": "..."}
  }]
}
```

## Hợp đồng asset

Asset mới **chỉ** nằm trong `assets/bac-bo-stick/extra/`. Lệnh build bộ gốc (`tools/build_bac_bo_assets.py`) ghi đè cả bộ gốc nhưng không đụng tới `extra/`.

**Đăng ký trong `assets/bac-bo-stick/extra/manifest.json`:**

```json
{
  "format": "storyvid.extra-assets/1",
  "assets": [
    {"id": "bamboo_forest_night", "label": "Rừng tre · đêm", "group": "backgrounds", "svg": "backgrounds/bamboo_forest_night.svg"},
    {"id": "coffin", "label": "Quan tài", "group": "props", "svg": "props/coffin.svg"},
    {"id": "goat", "label": "Dê", "group": "animals", "svg": "animals/goat.svg", "facing": -1}
  ],
  "characters": [
    {"id": "monk", "label": "Sư thầy", "female": false, "age": "elder", "scale": 0.94, "skin": "#c49a7a", "hair": "#2b2a28"}
  ]
}
```

| Nhóm | File | Khung | Ghi chú |
|---|---|---|---|
| `backgrounds` | `extra/backgrounds/<id>.svg` | `viewBox="0 0 1600 900"` | Không người, không chữ. Mặt đất ở y = 500–560. Bản `_night` giữ bố cục bản `_day` |
| `props` | `extra/props/<id>.svg` | `viewBox="0 0 480 360"` | Nền trong suốt, vật đứng trên đáy, ở giữa khung |
| `animals` | `extra/animals/<id>.svg` | `viewBox="0 0 480 360"` | Như `props`, thêm `"facing"`: `-1` nhìn trái, `1` nhìn phải |
| `effects` | `extra/effects/<id>.svg` | `viewBox="0 0 480 360"` | Ký hiệu truyện tranh, nền trong suốt |
| `characters` | `extra/characters/<id>/rig.json` + mảnh SVG | như bộ gốc | Chép thư mục nhân vật gốc gần nhất, giữ tên mọi file mảnh và các điểm neo trong `rig.json`, rồi vẽ lại |

**Phong cách bắt buộc (mẫu 10, Bắc Bộ):**
- Vector phẳng, không gradient, không bóng đổ, không chữ.
- Nét `#24211f`, dày 4, `stroke-linecap="round"`, `stroke-linejoin="round"`.
- Bảng màu: giấy `#fffdf7`, đất `#88624a`, đỏ yếm `#b65a45`, chàm `#485f6a`, lá `#afbf8c`. Có thể dùng các màu trung tính gần đó.
- So với bảng mẫu ở `output/bac-bo-stick/*-sheet.png` trước khi bàn giao.

**PNG thay cho SVG:** chỉ khi vẽ vector không làm được (ví dụ ảnh tạo bằng `$imagegen`). Nền là 1920×1080 RGB; đồ vật, con vật, hiệu ứng là 960×720 RGBA nền trong suốt. Khai `"png": "..."` thay cho `"svg"`. Nhân vật luôn là SVG tách mảnh.

**Bàn giao:** `python -m storyvid.check --assets` phải exit 0. Lệnh này cũng cập nhật `schema/assets.catalog.json`. Sau đó chạy lại `python -m storyvid.check output/<id>/scenes.json`.

## Thư mục một dự án

```
output/<id>/
  story.txt             truyện gốc
  meta.json             tên, ngôn ngữ, độ dài (web UI)
  scenes.json           kịch bản storyvid.scenes/1
  asset_requests.json   chỉ có khi thiếu asset; tự xóa khi đủ
  backgrounds.json      ảnh nền đã raster cho từng bg_id
  audio/, narration.wav giọng đọc
  video.mp4             video
  log.txt               nhật ký lần chạy gần nhất (web UI)
```

## Đổi chuẩn

Không sửa chuẩn ngầm. Khi cần thêm trường hay đổi quy tắc:
1. Sửa `storyvid/contract.py` (và `script.py` nếu thêm giá trị cố định).
2. Tăng phiên bản (`storyvid.scenes/2`) nếu kịch bản cũ không còn hợp lệ.
3. Chạy `python -m storyvid.check --write-schema`, sửa tài liệu này và `examples/`, chạy test.
