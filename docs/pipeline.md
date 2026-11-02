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

**Bước 3, Claude chấm những gì:** truyện (mở đầu có hook, giải thích luật của con ma, cao trào, kết), lời thoại (tự nhiên, đúng vai, đúng ngôn ngữ), dàn cảnh (ai đứng đâu, hướng nhìn, hành động khớp lời), nền và đồ vật (khớp nơi chốn và thời điểm), nhân vật, giọng đọc, phụ đề, nhịp (cảnh quá dài hay quá ngắn) và lỗi dựng hình. Danh sách đầy đủ để đánh dấu: `docs/review-checklist.md`; Codex cũng tự soát danh sách này ở bước 2 trước khi bàn giao.

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
- Âm thanh (tùy chọn): `"music": {"id": ...}` ở cấp video là nhạc nền cả video, tự nhỏ lại khi có lời đọc; `"ambience": "<id>"` trong một cảnh là âm thanh nền lặp suốt cảnh đó; `"sfx": [{"id": ..., "line": 0}]` là hiệu ứng phát lúc bắt đầu câu thứ `line` của cảnh (tối đa 6). Mã âm thanh phải có sẵn trong `assets/audio/manifest.json`, xem danh sách trong `schema/assets.catalog.json` (mục `music`, `ambience`, `sfx`). Agent không tự tạo âm thanh mới.
- Mọi id là chữ thường không dấu: `^[a-z][a-z0-9_]*$`. `bg_id` có đuôi `_day` hoặc `_night`.
- `host` và `narrator` là id dành riêng. `host` là người dẫn chuyện đứng trên sân khấu; `narrator` là giọng kể.
- Mỗi cảnh: 0–3 diễn viên, 0–3 đồ vật, 1–6 câu thoại. Diễn viên là id trong `cast` hoặc `host`, không lặp trong một cảnh.
- `speaker` là `narrator`, hoặc một id trong `cast` **đang đứng trên sân khấu** ở cảnh đó.
- Giá trị cố định (`position`, `pose`, `expression`, `action`, `camera`, `outfit`, `accessory`, `kind`, `lang`) lấy đúng trong schema.
- `camera`: `zoom_in` là cận cảnh, phóng cả sân khấu (nền, đồ vật, nhân vật) quanh nửa trên người các diễn viên trong cảnh, từ 1,12 lên 1,4 lần; `zoom_out` lùi từ 1,3 về 1 lần. `pan_left`/`pan_right` chỉ lia nền. Muốn chủ thể to, rõ (cảnh hook, cảnh dọa) thì dùng `zoom_in` với ít diễn viên.
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
    {"id": "coffin", "label": "Quan tài", "group": "props", "svg": "props/coffin.svg", "height": 0.22},
    {"id": "goat", "label": "Dê", "group": "animals", "svg": "animals/goat.svg", "facing": -1, "height": 0.2}
  ],
  "characters": [
    {"id": "monk", "label": "Sư thầy", "female": false, "age": "elder", "scale": 0.94, "skin": "#c49a7a", "hair": "#2b2a28"}
  ]
}
```

| Nhóm | File | Khung | Ghi chú |
|---|---|---|---|
| `backgrounds` | `extra/backgrounds/<id>.svg` | `viewBox="0 0 1600 900"` | Không người, không chữ. Mặt đất ở y = 500–560. Bản `_night` giữ bố cục bản `_day` |
| `props` | `extra/props/<id>.svg` | `viewBox="0 0 480 360"` | Nền trong suốt, vật đứng trên đáy, ở giữa khung. Bắt buộc `"height"`: chiều cao trên màn hình, tính theo tỉ lệ chiều cao khung (nhân vật là 0.54; ví dụ đèn dầu 0.12, chum nước 0.17, trâu 0.26, quả trứng thần 0.45) |
| `animals` | `extra/animals/<id>.svg` | `viewBox="0 0 480 360"` | Như `props` (có `"height"`), thêm `"facing"`: `-1` nhìn trái, `1` nhìn phải |
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

## Âm thanh: `assets/audio/`

`assets/audio/manifest.json` liệt kê mọi file âm thanh kèm nguồn và giấy phép, để khi bị Content ID claim thì chứng minh được:

```json
{"id": "can_roll", "label": "Rolling can", "kind": "sfx", "file": "sfx/can_roll.wav",
 "license": "CC0", "source": "https://freesound.org/people/cower/sounds/185370/", "author": "cower"}
```

- `kind`: `music`, `ambience` hoặc `sfx`. `license`: `CC0`, `CC-BY-4.0` (bắt buộc kèm `attribution`), `YouTube Audio Library` hoặc `Mixkit Free License`. Có thể thêm `gain_db` để chỉnh to nhỏ riêng một file.
- Tool tự cân âm lượng: nhạc và âm nền theo âm lượng trung bình, hiệu ứng theo đỉnh sóng. Sau đó toàn bộ phần nền bị ép thấp hơn giọng khoảng 9 dB khi có người nói, và không vượt -24 dBFS lúc im lặng, nên giọng đọc luôn nổi rõ.
- Video dùng âm thanh CC-BY thì lệnh dựng ghi dòng ghi công vào `credits.txt` trong thư mục dự án; chép vào mô tả video.
- File âm thanh **không** được đưa vào git (điều khoản YouTube Audio Library cấm phát tán lại file). Chỉ manifest được lưu; tải lại theo `source` khi cần.
- Chỉ người dùng hoặc Claude (khi người dùng đồng ý tải) thêm file mới. `python -m storyvid.check --assets` kiểm tra cả manifest âm thanh.

## Hình AI bằng Muse: `storyvid.visuals/1`

**Flow trên web UI:** 1. Phong cách (chọn kiểu có sẵn, hoặc để Muse vẽ mẫu từng kiểu rồi chọn; chọn khung 16:9/9:16) → 2. Truyện (dán truyện ngôn ngữ nào cũng được; chọn người viết kịch bản: Muse, Claude, API chuẩn OpenAI, Codex, hoặc chỉ chia cảnh để tự viết) → 3. Kịch bản (**người thật đọc và bấm “Duyệt kịch bản”**) → 4. Hình Muse → 5. Video (chọn giọng đọc của dự án, nghe thử, dựng). Ngôn ngữ đầu ra của dự án quyết định ngôn ngữ kịch bản, giọng đọc và phụ đề.

**Vòng đánh giá kịch bản** (`storyvid/script_review.py`, tab Kịch bản → “Đánh giá kịch bản”): AI (Muse, Claude, API chuẩn OpenAI hoặc Codex) chấm 1–10 theo tiêu chí (mở đầu, đúng nguồn và khoa học, dễ hiểu, mạch lạc, dựng hình được, an toàn với Muse) cộng một tiêu chí máy tự đo (thời lượng ước tính so với mục tiêu, cảnh quá dài cho một clip 10 giây), liệt kê lỗi từng cảnh; “AI sửa” viết lại đúng các cảnh bị nêu (có thể tách một cảnh thành nhiều), lưu bản trước thành `scenes.round<N>.json` và bỏ duyệt. Lịch sử ở `script_reviews.json` (`storyvid.script-review/1`). `python -m storyvid.script_review auto output/<id> --rounds 2` chạy đánh giá → sửa → đánh giá đến khi đạt (≥ 80 điểm, không lỗi nặng). Kịch bản dài được viết theo từng phần khoảng 3.500 ký tự, dùng chung dàn nhân vật. Loại nội dung `explainer` (kiến thức) và tùy chọn “Giữ nguyên lời kể” (`--genre`, `--keep-text`) dùng khi văn bản đã là lời kể sẵn.

**Duyệt kịch bản là cổng bắt buộc:** `meta.json` lưu `approved_script` (mã băm của `scenes.json` lúc duyệt). Mọi chỉnh sửa sau đó làm mất duyệt. Khi chưa duyệt, web UI khóa tab Hình Muse, API trả 409 và `python -m storyvid.visuals` dừng (chỉ test mới dùng `--skip-review`). Agent không tự duyệt thay người.

**Phong cách** (`storyvid/styles.py`): `stick` (người que của kênh, gửi kèm `assets/styles/stick/`), `cartoon3d`, `flat2d`, `dark2d`, `cinematic`, hoặc `custom` (tự viết). Lựa chọn nằm trong `meta.json` `style`; bước `prompts` chép chữ mô tả vào `visuals.json` `style` và ảnh tham chiếu vào `muse/style/` (`style_refs`). Ảnh mẫu dùng chung ở `cache/styles/` (`python -m storyvid.styles sample`).

Thay cho sân khấu người que, mỗi cảnh có thể dùng **ảnh và clip do Muse tạo**. Kế hoạch hình nằm ở `output/<id>/visuals.json`, cạnh `scenes.json`. `scenes.json` giữ nguyên chuẩn `storyvid.scenes/1`, nên dự án vẫn dựng được bản người que như cũ.

```
scenes.json (đã đạt check)
  │
[a] python -m storyvid.visuals prompts output/<id> [--provider muse|offline|openai|codex] [--ratio 16:9|9:16]
  │     ─► visuals.json: phong cách chung, ngoại hình cố định của từng nhân vật, prompt ảnh mở cảnh và prompt chuyển động
  │     python -m storyvid.check --visuals output/<id>/visuals.json   (phải 0)
[b] python -m storyvid.visuals cast output/<id>      ─► muse/cast/<id>.png   (ảnh mẫu nhân vật, người dùng duyệt)
[c] python -m storyvid.visuals scenes output/<id> [--images-only | --clips-only]
                                                      ─► muse/scene_NN.png rồi muse/scene_NN.mp4
  │     ảnh mở cảnh đính kèm ảnh mẫu của các diễn viên trong cảnh và ảnh tham chiếu phong cách (tối đa 4);
  │     nên tạo ảnh trước (--images-only), xem, rồi mới tạo clip (--clips-only); clip lấy ảnh đó làm khung đầu
[d] python -m storyvid.cli --script output/<id>/scenes.json --visuals [--short]
        giọng đọc + phụ đề + nhạc như bản thường, hình là clip của từng cảnh
```

- Muse được điều khiển qua **MuseFlow** (`museflow/`, `npm start`): app Electron giữ nhiều tài khoản Muse đã đăng nhập và mở API nội bộ ở `127.0.0.1:8770` (`MUSEFLOW_API` trong `.env`). Mỗi tài khoản sẵn sàng chạy một cảnh; một tài khoản thì các cảnh chạy lần lượt.
- Mở `npm start` trong `museflow/` là đủ: app tự chạy web UI storyvid (`.venv/bin/python -m storyvid.web`, cổng 8765; đổi bằng `STORYVID_PYTHON`, `STORYVID_WEB_PORT`) và hiện nó ở tab **🎬 Dự án video**; tab **🧩 Canvas** là canvas MuseFlow cũ. Nếu web UI đã chạy sẵn (mở từ terminal) thì app dùng lại server đó và không tắt nó khi thoát. Nhật ký server: `storyvid-web.log` trong thư mục dữ liệu của app.
- **Ảnh thật của địa điểm** (`refs/places.json`, chuẩn `storyvid.places/1`, `storyvid/places.py`; panel trên tab Hình Muse): mỗi địa điểm có tên, từ khóa tiếng Anh, ảnh, danh sách cảnh luôn dùng (`scenes`) và cảnh không dùng (`skip`), số cảnh tính từ 1. Cảnh có từ khóa (nguyên từ, cả số nhiều) trong `bg_prompt` hoặc prompt ảnh thì được gửi kèm ảnh đầu tiên của địa điểm, kèm lời dặn Muse vẽ lại theo phong cách của dự án, không chép ảnh. Ảnh báo chí chỉ dùng làm tham khảo, không đưa thẳng vào video; ghi nguồn trong `sources`.
- Muse bị từ chối thì tự thử lại một lần với phiên bản an toàn hơn. Lỗi còn lại ghi vào trường `error` của nhân vật hoặc cảnh; chạy lại bằng `--only <id hoặc số cảnh>` (thêm `--redo` để tạo lại cả file đã có).
- Prompt ảnh chỉ mô tả các nhân vật **đang đứng trên sân khấu** ở cảnh đó (theo `actors` trong `scenes.json`), không dồn cả dàn nhân vật vào mọi prompt.
- Muse luôn trả clip khoảng 10 giây. Khi dựng, độ dài cảnh theo giọng đọc: lời ngắn thì cắt clip; lời dài thì clip chạy chậm lại tối đa 1,35 lần, phần còn lại giữ khung cuối và đẩy máy nhẹ. Cảnh lời quá dài nên tách thành hai cảnh.
- Viết lại prompt (`prompts`) giữ lại ảnh và clip của những cảnh có prompt không đổi.
- **Nối khung cuối** (`continuity` trong `visuals.json`, chọn trên tab Hình Muse): clip của cảnh được nối bắt đầu từ khung cuối clip cảnh trước (gửi kèm 2 ảnh: khung cuối đó và ảnh mở cảnh). `auto` (mặc định) nối hai cảnh liền nhau có cùng `bg_id`, tức cùng nơi và cùng thời điểm; `all` nối mọi cảnh; `off` không nối. Các cảnh nối với nhau tạo clip lần lượt; các chuỗi khác nhau vẫn chạy song song trên các tài khoản. Clip cảnh trước lỗi thì cảnh sau bắt đầu từ ảnh của chính nó. Tạo lại clip một cảnh thì cảnh nối sau nó vẫn dùng khung cuối cũ; tạo lại cả cảnh sau nếu thấy chỗ nối bị lệch.

Quy tắc của `visuals.json`: đủ trường, không trường lạ (tùy chọn: `style_refs` ở cấp gốc, `error` trong nhân vật và cảnh, do tool ghi). `scenes` có đúng số cảnh của `scenes.json`, cùng thứ tự. `cast[].id` là id trong `cast` của `scenes.json` hoặc `host`. Đường dẫn file nằm trong thư mục dự án; `""` là chưa tạo. Schema: `schema/visuals.v1.schema.json`. Tất cả làm được trong web UI, tab **3. Hình Muse**.

## Hoàn thành video (tab 6. Hoàn thành, `storyvid/finish.py`)

Mọi video, người que hay Muse, kết thúc theo đúng 5 bước. Bước sau chỉ làm khi bước trước đạt.

1. **Máy kiểm tra** (`python -m storyvid.finish check output/<id> [--video video_short]`, ghi `finish.json`): video dựng từ đúng bản `scenes.json` đã duyệt (so mã băm trong `render.json`), không dùng `--fallback`, cảnh nào cũng có clip (video Muse), cạnh ngắn ≥ 1080 px, đủ 90 % thời lượng mục tiêu (Short tối đa 60 giây), âm lượng −16 đến −12 LUFS với đỉnh dưới −1 dB, không im lặng quá 3 giây, phụ đề SRT phủ hết video. Âm lượng sai thì `loudnorm` chuẩn hóa về −14 LUFS (chỉ xử lý tiếng, giữ nguyên hình).
2. **Kiểm định nội dung** (`review`): app lấy một khung hình giữa mỗi cảnh (`publish/frames/`), ghép thành bảng 20 cảnh có số; AI (Muse xem được hình; Claude, OpenAI, Codex chỉ xem lời) so từng khung với lời kể và ngoại hình nhân vật, rồi kiểm chứng số liệu và trích dẫn. Kết quả ghi `review.json` (`storyvid.review/1`). `fix` thì tạo lại đúng các cảnh bị nêu ở tab Hình Muse, dựng lại, chạy lại bước 1–2.
3. **Short 9:16** (tùy chọn): `--short` dựng `video_short.mp4` từ `short.scenes` (hoặc khoảng 55 giây đầu); chạy bước 1 với `--video video_short`.
4. **Gói đăng** (`publish`, ghi vào `publish/`): `youtube.md` và `publish.json` gồm 3 tiêu đề, mô tả (2 dòng mở có từ khóa, tóm tắt, chương lấy mốc thời gian thật từ `render.json`, cách nhau ≥ 10 giây và bắt đầu ở 0:00, nguồn và ghi công lấy từ ô “Nguồn và ghi công”, ghi chú hình AI, hashtag), tag, cài đặt; 3 thumbnail 1280×720: Muse vẽ hình (gửi kèm ảnh mẫu nhân vật), app tự in chữ để không sai chính tả.
5. **Đăng**: người dùng đăng lên YouTube (agent không đăng thay), đánh dấu checklist trên tab, dán link và bấm “Đánh dấu đã đăng” (`meta.json` `published`). Sau 48 giờ ghi số liệu vào `docs/research/`.

`render.json` (do lệnh dựng ghi): với mỗi bản (`video`, `video_short`) lưu mã băm kịch bản, có dùng clip Muse và `--fallback` không, độ phân giải, giọng đọc và mốc bắt đầu/kết thúc từng cảnh.

## Thư mục một dự án

```
output/<id>/
  story.txt             truyện gốc
  meta.json             tên, ngôn ngữ, độ dài (web UI)
  scenes.json           kịch bản storyvid.scenes/1
  asset_requests.json   chỉ có khi thiếu asset; tự xóa khi đủ
  review.json           báo cáo kiểm định của Claude
  backgrounds.json      ảnh nền đã raster cho từng bg_id
  audio/, narration.wav giọng đọc (edge-tts lưu từng câu trong cache/edge/, câu treo quá 60 giây được thử lại tối đa 5 lần)
  video.srt             phụ đề để tải lên YouTube (Short: video_short.srt)
  mix.wav               giọng đọc đã trộn nhạc và hiệu ứng (chỉ có khi kịch bản có âm thanh)
  credits.txt           dòng ghi công cho mô tả video (chỉ khi dùng âm thanh CC-BY)
  video.mp4             video 16:9
  short/                giọng đọc riêng của Short
  video_short.mp4       Short 9:16 (1080x1920 với --res 1080), hình phủ kín khung dọc, tiêu đề và phụ đề nằm đè lên hình
  meta.json             còn có: ratio, style (phong cách), voice (giọng đọc riêng của dự án), approved_script
  visuals.json          kế hoạch hình Muse storyvid.visuals/1 (chỉ khi dùng Muse)
  muse/                 ảnh mẫu nhân vật (cast/), ảnh tham chiếu phong cách (style/), mẫu phong cách tự viết
                        (styles/), ảnh mở cảnh và clip của từng cảnh
  refs/                 ảnh thật của địa điểm: places.json và một thư mục ảnh cho mỗi địa điểm
  render.json           bản dựng từ kịch bản nào, mốc thời gian từng cảnh
  finish.json           kết quả máy kiểm tra, kiểm định và gói đăng
  publish/              frames/ (khung hình từng cảnh, bảng kiểm định), youtube.md, publish.json, thumbnail_*.jpg
  log.txt               nhật ký lần chạy gần nhất (web UI)
```

## Đổi chuẩn

Không sửa chuẩn ngầm. Khi cần thêm trường hay đổi quy tắc:
1. Sửa `storyvid/contract.py` (và `script.py` nếu thêm giá trị cố định).
2. Tăng phiên bản (`storyvid.scenes/2`) nếu kịch bản cũ không còn hợp lệ.
3. Chạy `python -m storyvid.check --write-schema`, sửa tài liệu này và `examples/`, chạy test.

## Ma nguyên ảnh và Blender (bộ đã duyệt cho Stung Treng)

Bộ nguồn `assets/bac-bo-stick/extra/whole-ghosts-v1/` dùng một PNG RGBA nguyên nhân vật cho mỗi tư thế, giữ mẫu đã duyệt thay vì cắt khớp tay chân. Mỗi ma có bốn tư thế. Quy cách, điểm đặt, nguồn ảnh và script ở [README bộ ma](../assets/bac-bo-stick/extra/whole-ghosts-v1/README.md). Blender tạo cảnh 2.5D từ manifest riêng, với chuyển động nhẹ và đổi tư thế bằng độ mờ.

Đây là chuẩn nguồn cho bộ dựng Blender riêng, **chưa phải một thay đổi của `storyvid.scenes/1`**. Quy tắc nhân vật SVG của renderer Storyvid hiện tại vẫn giữ nguyên. Không thêm trường hay giá trị pose mới vào scenes.json để dùng tạm PNG; không đăng ký PNG nguyên nhân vật thành props. Khi cần Storyvid đọc bộ này, phải làm một đợt tích hợp được cho phép rõ ràng và kiểm tra lại chuẩn, renderer và video. Bộ nguồn và bản Blender không thay thế review cuối của Claude.
