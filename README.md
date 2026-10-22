# storyvid — tool demo làm video truyện hoạt hình

## Bộ assets Bắc Bộ — người que mẫu 10

Tool dùng bộ `assets/bac-bo-stick/` cho mọi video: 8 nhân vật rig SVG tách mảnh, 16 cảnh nền (8 nơi × ngày/đêm), 9 con vật, 19 đạo cụ và 8 hiệu ứng. Danh mục trực quan ở [output/bac-bo-stick/index.html](output/bac-bo-stick/index.html), hướng dẫn ở [output/bac-bo-stick/README.md](output/bac-bo-stick/README.md). Clip mẫu chuẩn: [examples/ma_da_bac_bo.scenes.json](examples/ma_da_bac_bo.scenes.json).

Chạy lại bộ bằng `tools/build_bac_bo_assets.py`, rồi `tools/export_bac_bo_assets.py`; kiểm tra bằng `tools/verify_bac_bo_assets.py`. Các lệnh build ghi đè nguồn của bộ, nên sao lưu nếu đã sửa SVG thủ công.

```
truyện (.txt) ─► [1] LLM viết lại kịch bản ─► scenes.json
                 [2] edge-tts đọc từng cảnh ─► narration.wav + phụ đề
                 [3] cảnh nền của bộ assets cho mỗi bg_id ─► cache/backgrounds/
                 [4] dựng khung hình: nền + máy quay + đồ vật + nhân vật + hiệu ứng + banner + phụ đề ─► video.mp4
```

## Cài đặt

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env      # rồi điền key (hoặc điền trong trang Cài đặt của web UI)
```

Tool tự tìm ffmpeg dùng được. Bản ffmpeg Homebrew trên máy này đang lỗi (thiếu thư viện x265), nên tool dùng bản đóng gói sẵn trong `imageio-ffmpeg`.

## Web UI (quản lý dự án)

```bash
.venv/bin/python -m storyvid.web
```

Mở http://127.0.0.1:8765. Server chỉ nghe trên máy bạn, không mở ra mạng ngoài.

- **Dự án**: tạo, đổi tên, đổi ngôn ngữ và độ dài, xóa.
- **1. Truyện**: dán truyện gốc, chọn AI viết kịch bản (hoặc theo `.env`).
- **2. Kịch bản**: chọn người dẫn chuyện; quản lý **nhân vật trong truyện** (tên, preset, trang phục, phụ kiện, người hay ma); mỗi cảnh sửa **lời thoại** (ai nói câu nào) và **diễn viên trên sân khấu** (vị trí, tư thế, biểu cảm, hành động), **đồ vật, con vật**, cảnh nền và máy quay; thêm, xóa, đổi thứ tự cảnh.
- **3. Video**: chọn độ phân giải, dựng video, xem nhật ký chạy trực tiếp, xem và tải MP4.
- **Cài đặt**: provider AI và key (key được che, để trống thì giữ nguyên key cũ), tên kênh, banner, màu nhân vật (có xem trước), giọng đọc.

Mỗi dự án là một thư mục trong `output/<id>/`: `story.txt`, `meta.json`, `scenes.json`, `video.mp4`, `log.txt`.

## Dòng lệnh

```bash
.venv/bin/python -m storyvid.cli examples/ma_da.txt --lang en --minutes 2      # đủ 4 bước
.venv/bin/python -m storyvid.cli examples/ma_da.txt --script-only               # chỉ viết kịch bản
.venv/bin/python -m storyvid.cli --script output/ma_da/scenes.json --lang en    # dựng lại sau khi sửa
```

Tùy chọn: `--provider auto|openai|codex|claude|offline`, `--res 480|720|1080`, `--fps`, `--out`.

## `.env` — AI viết kịch bản và giọng đọc

| Biến | Ý nghĩa |
|---|---|
| `LLM_PROVIDER` | `openai`: mọi API theo chuẩn OpenAI (OpenAI, DeepSeek, Gemini, OpenRouter); `codex`: Codex CLI; `offline`: không dùng AI |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | Dùng cho `openai`. Ví dụ DeepSeek: `https://api.deepseek.com/v1`, model `deepseek-chat` |
| `CODEX_BIN`, `CODEX_MODEL` | Dùng cho `codex` (mặc định lệnh `codex`) |
| `TTS_PROVIDER` | `edge`: giọng Edge miễn phí (không chính thức, giọng đặt theo ngôn ngữ trong `channel.json`); `elevenlabs`: ElevenLabs API |
| `ELEVENLABS_API_KEY` | Dùng cho `elevenlabs` |
| `ELEVENLABS_MODEL` | Tùy chọn. Mặc định `eleven_multilingual_v2`; tiếng Việt dùng `eleven_flash_v2_5` vì v2 không có tiếng Việt |
| `ELEVENLABS_NARRATOR_VOICE` | Tùy chọn. Id hoặc tên giọng người dẫn chuyện; để trống thì chọn một giọng nam trung niên trong tài khoản |

Với ElevenLabs, mỗi nhân vật được chọn một giọng riêng trong tài khoản theo giới tính và tuổi. ElevenLabs không chỉnh được cao độ, nên tuổi và ma chỉ làm chậm tốc độ đọc. Mỗi câu đã đọc được lưu trong `cache/tts/`, nên dựng lại video không tốn thêm ký tự. Gói Free có khoảng 10.000 ký tự/tháng và **không được dùng cho kênh bật kiếm tiền**.

### Dùng Codex (tính vào gói ChatGPT, không cần API key)

```bash
npm install -g @openai/codex   # bản cài hiện tại trên máy đang hỏng (thiếu file chạy chính)
codex login                    # đăng nhập bằng tài khoản ChatGPT
```

Sau đó đặt `LLM_PROVIDER=codex`.

## Kênh — `channel.json`

Gồm tên kênh, banner, nhân vật chính (tên, tính cách đưa vào prompt, màu tóc, da, áo, viền) và giọng đọc theo ngôn ngữ. Sửa được trong trang Cài đặt.

## Kịch bản — `scenes.json`

Mẫu đầy đủ: [examples/ma_da_bac_bo.scenes.json](examples/ma_da_bac_bo.scenes.json) (Tư, Bà và Ma da nói chuyện với nhau, có con vật và đồ vật).

```json
{
  "title": "Tiếng gọi từ sông",
  "character": {"preset": "young_man"},
  "cast": [{"id": "ba", "name": "Bà", "preset": "elder_woman", "outfit": "earth", "accessory": "scarf", "kind": "human"},
           {"id": "ma_da", "name": "Ma da", "preset": "middle_woman", "outfit": "cream", "accessory": "none", "kind": "ghost"}],
  "scenes": [{
    "bg_id": "river_night", "bg_prompt": "dark river at night", "camera": "zoom_in",
    "actors": [{"id": "ba", "position": "left", "pose": "point", "expression": "angry", "action": "enter"},
               {"id": "ma_da", "position": "right", "pose": "cower", "expression": "angry", "action": "exit"}],
    "props": [{"id": "oil_lamp", "position": "far_left"}],
    "lines": [{"speaker": "ba", "text": "Buông cháu tao ra!"},
              {"speaker": "narrator", "text": "Bàn tay lạnh buốt buông ra."}]
  }]
}
```

| Trường | Giá trị |
|---|---|
| `character` | diện mạo người dẫn chuyện (host), id diễn viên là `host` |
| `cast[]` | nhân vật trong truyện: `preset` (8 nhân vật), `outfit`, `accessory`, `kind`: `human` hoặc `ghost` (vẽ mờ, trôi lơ lửng, giọng trầm chậm) |
| `lines[]` | lời thoại theo thứ tự; `speaker` = `narrator` (giọng kênh) hoặc id trong `cast` |
| `actors[]` | ai đứng trên sân khấu trong cảnh (0–3 người) |
| `position` | `far_left`, `left`, `center`, `right`, `far_right` |
| `pose` | `idle`, `talk`, `point`, `scared`, `think`, `shrug`, `reach`, `wave`, `cower` |
| `expression` | `neutral`, `happy`, `scared`, `surprised`, `sad`, `angry`, `smirk` |
| `action` | `none`, `enter` (đi vào từ mép), `exit` (đi ra cuối cảnh), `approach` (tiến lại gần người khác), `jump` (giật mình), `shake` (run rẩy) |
| `props[]` | con vật hoặc đồ vật đứng trên mặt đất (0–3), `id` trong danh mục của bộ (`buffalo`, `hen`, `oil_lamp`, `water_jar`…) và `position` |
| `bg_id` | một trong 16 cảnh của bộ: `courtyard`, `pond`, `rice_fields`, `village_path`, `communal_house`, `market`, `river`, `interior`, kèm `_day` hoặc `_night`. Mã khác được tự ghép vào cảnh gần nhất theo từ khóa trong `bg_id` và `bg_prompt` |
| `camera` | `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `static` |

Tự động khi dựng:
- Ai đang nói thì nhép miệng; người nghe quay mặt về phía người nói.
- Nhân vật có mặt ở cảnh trước tự đi bộ sang vị trí mới.
- Phụ đề có tên người nói (màu vàng).
- Ký hiệu truyện tranh quanh đầu theo biểu cảm: giật mình (`surprised` hoặc `jump`), giận (`angry`), giọt mồ hôi (`scared`); bụi dưới chân khi đi vào, đi ra, tiến lại gần.
- Con vật quay mặt vào giữa khung hình.

Giọng nhân vật: giới tính lấy theo preset, cao độ và tốc độ chỉnh theo tuổi (trẻ con cao hơn, người già trầm và chậm hơn). Tiếng Việt chỉ có 2 giọng gốc (NamMinh, HoaiMy), nên các nhân vật được phân biệt bằng cao độ.

## Cấu trúc code

- `storyvid/script.py`: prompt, schema, chuẩn hóa kịch bản, chế độ offline
- `storyvid/llm.py`: provider chuẩn OpenAI và Codex CLI
- `storyvid/tts.py`: edge-tts hoặc ElevenLabs, phụ đề có dấu câu
- `storyvid/elevenlabs.py`: gọi ElevenLabs, chọn giọng, cache
- `storyvid/pack.py`: đọc bộ assets Bắc Bộ, chọn cảnh nền, raster SVG
- `storyvid/backgrounds.py`: raster cảnh nền của bộ, có cache
- `storyvid/character.py`: ghép nhân vật từ mảnh SVG
- `storyvid/render.py`: dựng khung hình, ffmpeg
- `storyvid/cli.py`: các bước dòng lệnh, đọc `.env`
- `storyvid/web/`: web UI (Flask + HTML/JS thuần)

## Nhân vật

Tám mẫu: `young_man`, `young_woman`, `elder_man`, `elder_woman`, `boy`, `girl`, `middle_man`, `middle_woman`. Trong tab **Kịch bản → Nhân vật của video**, chọn mẫu, màu áo và phụ kiện (túi vải, khăn, đèn pin), rồi **Lưu kịch bản**.

Thêm `skin_color`, `hair_color`, `shirt_color`, `outline_color` dạng `#rrggbb` để ghi đè màu riêng. Mặt nhân vật giữ màu trắng theo mẫu 10.

Nguồn ở `assets/bac-bo-stick/characters/<preset>/`: `rig.json` (pivot, khớp, chiều dài tay chân) và các mảnh SVG riêng cho đầu, tóc, thân, tay, chân, mắt, mày, miệng theo từng trạng thái. Giữ các biến màu `{{skin}}`, `{{hair}}`, `{{shirt}}`, `{{pants}}`, `{{ink}}` nếu muốn tiếp tục đổi màu trong giao diện.

```bash
.venv/bin/python tools/verify_bac_bo_assets.py
.venv/bin/python -m unittest discover -s tests -v
node --check storyvid/web/static/app.js
```
