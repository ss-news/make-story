# Flow sản xuất video và hợp đồng giữa các agent

Mục tiêu: model nào viết hay sửa kịch bản (Claude, Codex, DeepSeek, Gemini…) và agent nào vẽ asset thì đầu ra cũng theo **một chuẩn**. Mọi thứ được kiểm tra bằng máy trước khi chuyển sang bước sau.

## Vai trò

| Ai | Làm | Không làm |
|---|---|---|
| **Claude** (đọc `CLAUDE.md`) | Phân tích truyện, chia cảnh, viết **bản đầu tiên** của `scenes.json`. Kiểm định: chạy kiểm tra, dựng video, chấm kịch bản và video, ghi `review.json` | Không sửa `scenes.json` sau bản đầu tiên, không vẽ asset |
| **Codex** (đọc `AGENTS.md`) | Sửa và hoàn thiện `scenes.json` (lời thoại, diễn xuất, đồ vật, các mục trong `review.json`). Vẽ asset theo `asset_requests.json` vào `assets/bac-bo-stick/extra/` | Không sửa code `storyvid/`, bộ asset gốc ngoài `extra/`, hay `review.json` |
| Người dùng | Duyệt bản `pass`, xử lý các mục `owner: "tool"` (lỗi code) | |

Mỗi file chỉ có một bên được ghi tại một thời điểm: `scenes.json` của Claude ở bản đầu, sau đó của Codex; `asset_requests.json` do máy sinh; asset trong `extra/` của Codex; `review.json` của Claude.

## Flow

```
truyện
  │
[1] Claude: phân tích, chia cảnh ─► output/<id>/scenes.json (bản đầu)
  │        python -m storyvid.check output/<id>/scenes.json   (0 hoặc 2)
  ▼
[2] Codex: hoàn thiện scenes.json
  │        nếu check ra 2: vẽ asset theo asset_requests.json vào assets/bac-bo-stick/extra/
  │        python -m storyvid.check --assets                  (phải 0)
  │        python -m storyvid.check output/<id>/scenes.json   (phải 0)
  ▼
[3] Claude: kiểm định
  │        python -m storyvid.cli --script output/<id>/scenes.json ─► video.mp4
  │        python -m storyvid.cli --script output/<id>/scenes.json --short ─► video_short.mp4 (9:16)
  │        xem kịch bản và video, ghi output/<id>/review.json
  │        python -m storyvid.check --review output/<id>/review.json   (phải 0)
  ▼
verdict "fix" ─► quay lại [2], Codex sửa các mục owner "codex"
verdict "pass" ─► người dùng duyệt và đăng
```

Lệnh dựng video tự kiểm tra kịch bản và dừng nếu chưa đạt. `--fallback` chỉ dùng để xem nháp: nền thiếu được thay bằng cảnh gần nhất, đồ vật thiếu bị bỏ.

**Bước 1, chia cảnh:** Claude viết thẳng file theo `schema/scenes.v1.schema.json`, lấy mã asset trong `schema/assets.catalog.json`. Bản đầu cần đủ cảnh, nơi chốn, ai trên sân khấu, lời thoại và `short.scenes` (các cảnh đưa vào Short); Codex sẽ trau chuốt sau. Cũng có thể để tool gọi model viết nháp (`python -m storyvid.cli story.txt --lang en --provider claude|openai|codex --script-only --out output/<id>`); đầu ra được chuẩn hóa (cắt giá trị lạ, gắn `format`, `lang`) rồi kiểm tra như mọi kịch bản khác.

**Bước 3, Claude chấm những gì:** truyện (mở đầu có hook, giải thích luật của con ma, cao trào, kết), lời thoại (tự nhiên, đúng vai, đúng ngôn ngữ), dàn cảnh (ai đứng đâu, hướng nhìn, hành động khớp lời), nền và đồ vật (khớp nơi chốn và thời điểm), nhân vật, giọng đọc, phụ đề, nhịp (cảnh quá dài hay quá ngắn) và lỗi dựng hình.

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
- Đủ các trường, **không thêm trường lạ**. Chỉ `character` và `short` là tùy chọn.
- `short.scenes`: chỉ số các cảnh (đếm từ 0, tăng dần) cắt vào Short 9:16. Nên mở bằng cảnh hook, tổng 30–60 giây, kết lửng. Không có trường này thì Short lấy các cảnh đầu truyện tới khoảng 55 giây.
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

## Báo cáo kiểm định: `storyvid.review/1`

`output/<id>/review.json`, do Claude viết sau khi xem video. Schema: `schema/review.v1.schema.json`. Mẫu: `examples/ma_da_bac_bo.review.json`.

```json
{
  "format": "storyvid.review/1",
  "scenes_file": "output/<id>/scenes.json",
  "verdict": "fix",
  "issues": [{
    "scene": 0, "area": "story", "severity": "major", "owner": "codex",
    "problem": "Câu mở đầu chưa nói ma da là gì.",
    "fix": "Thêm một câu narrator giải thích ma da là hồn người chết đuối."
  }]
}
```

| Trường | Giá trị |
|---|---|
| `verdict` | `pass`: đăng được, chỉ còn lỗi `minor`. `fix`: trả lại, phải có ít nhất một mục |
| `scene` | chỉ số cảnh, đếm từ 0; `null` nếu là lỗi cả video |
| `area` | `story`, `dialogue`, `staging`, `background`, `props`, `character`, `audio`, `subtitle`, `pacing`, `render` |
| `severity` | `blocker` (không đăng được), `major` (phải sửa), `minor` (nên sửa) |
| `owner` | `codex`: sửa `scenes.json` hoặc asset. `tool`: lỗi code, báo người dùng |
| `problem`, `fix` | mô tả lỗi và cách sửa cụ thể, đủ để Codex làm mà không cần hỏi lại |

## Thư mục một dự án

```
output/<id>/
  story.txt             truyện gốc
  meta.json             tên, ngôn ngữ, độ dài (web UI)
  scenes.json           kịch bản storyvid.scenes/1
  asset_requests.json   chỉ có khi thiếu asset; tự xóa khi đủ
  review.json           báo cáo kiểm định của Claude
  backgrounds.json      ảnh nền đã raster cho từng bg_id
  audio/, narration.wav giọng đọc
  video.mp4             video 16:9
  short/                giọng đọc riêng của Short
  video_short.mp4       Short 9:16 (1080x1920 với --res 1080)
  log.txt               nhật ký lần chạy gần nhất (web UI)
```

## Đổi chuẩn

Không sửa chuẩn ngầm. Khi cần thêm trường hay đổi quy tắc:
1. Sửa `storyvid/contract.py` (và `script.py` nếu thêm giá trị cố định).
2. Tăng phiên bản (`storyvid.scenes/2`) nếu kịch bản cũ không còn hợp lệ.
3. Chạy `python -m storyvid.check --write-schema`, sửa tài liệu này và `examples/`, chạy test.
