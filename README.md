# storyvid — tool demo làm video truyện hoạt hình

## Bộ assets Bắc Bộ — người que mẫu 10

Bộ riêng đã xuất tại [output/bac-bo-stick/index.html](output/bac-bo-stick/index.html):
8 nhân vật có rig SVG tách mảnh, 9 động vật, 19 đạo cụ/trang phục, 16 cảnh
ngày/đêm, 8 hiệu ứng, PNG trong suốt, contact sheets và clip thử 24 giây.
Nguồn ở `assets/bac-bo-stick/`; xem [hướng dẫn sử dụng](output/bac-bo-stick/README.md).
Thư viện này chưa tự chọn trong web UI. `Character` nhận keyword
`asset_root=Path('assets/bac-bo-stick/characters')` để dùng bộ mới, trong khi
các dự án và thư viện cũ giữ nguyên.

Chạy lại bộ mới bằng `tools/build_bac_bo_assets.py`, rồi
`tools/export_bac_bo_assets.py`; kiểm tra bằng `tools/verify_bac_bo_assets.py`.
Các lệnh build ghi đè nguồn của bộ mới, nên sao lưu nếu đã sửa SVG thủ công.

```
truyện (.txt) ─► [1] LLM viết lại kịch bản ─► scenes.json
                 [2] edge-tts đọc từng cảnh ─► narration.wav + phụ đề
                 [3] ảnh nền cho mỗi bg_id ─► cache/backgrounds/
                 [4] dựng khung hình: nền + máy quay + nhân vật chính + banner + phụ đề ─► video.mp4
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
- **2. Kịch bản**: chọn người dẫn chuyện; quản lý **nhân vật trong truyện** (tên, preset, trang phục, phụ kiện, người hay ma); mỗi cảnh sửa **lời thoại** (ai nói câu nào) và **diễn viên trên sân khấu** (vị trí, tư thế, biểu cảm, hành động), ảnh nền và máy quay; thêm, xóa, đổi thứ tự cảnh.
- **3. Video**: chọn độ phân giải, dựng video, xem nhật ký chạy trực tiếp, xem và tải MP4.
- **Cài đặt**: provider AI và key (key được che, để trống thì giữ nguyên key cũ), tên kênh, banner, màu nhân vật (có xem trước), phong cách ảnh nền, giọng đọc.

Mỗi dự án là một thư mục trong `output/<id>/`: `story.txt`, `meta.json`, `scenes.json`, `video.mp4`, `log.txt`.

## Dòng lệnh

```bash
.venv/bin/python -m storyvid.cli examples/ma_da.txt --lang en --minutes 2      # đủ 4 bước
.venv/bin/python -m storyvid.cli examples/ma_da.txt --script-only               # chỉ viết kịch bản
.venv/bin/python -m storyvid.cli --script output/ma_da/scenes.json --lang en    # dựng lại sau khi sửa
```

Tùy chọn: `--provider auto|openai|codex|claude|offline`, `--res 480|720|1080`, `--fps`, `--out`.

## `.env` — AI viết kịch bản và ảnh nền

| Biến | Ý nghĩa |
|---|---|
| `LLM_PROVIDER` | `openai`: mọi API theo chuẩn OpenAI (OpenAI, DeepSeek, Gemini, OpenRouter); `codex`: Codex CLI; `offline`: không dùng AI |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | Dùng cho `openai`. Ví dụ DeepSeek: `https://api.deepseek.com/v1`, model `deepseek-chat` |
| `CODEX_BIN`, `CODEX_MODEL` | Dùng cho `codex` (mặc định lệnh `codex`) |
| `IMAGE_PROVIDER` | `procedural`: vẽ bằng code, miễn phí; `codex`: skill `$imagegen` của Codex; `fal`: FLUX schnell |
| `FAL_KEY` | Dùng cho `fal` |
| `TTS_PROVIDER` | `edge`: giọng Edge miễn phí (không chính thức, giọng đặt theo ngôn ngữ trong `channel.json`); `elevenlabs`: ElevenLabs API |
| `ELEVENLABS_API_KEY` | Dùng cho `elevenlabs` |
| `ELEVENLABS_MODEL` | Tùy chọn. Mặc định `eleven_multilingual_v2`; tiếng Việt dùng `eleven_flash_v2_5` vì v2 không có tiếng Việt |
| `ELEVENLABS_NARRATOR_VOICE` | Tùy chọn. Id hoặc tên giọng người dẫn chuyện; để trống thì chọn một giọng nam trung niên trong tài khoản |

Với ElevenLabs, mỗi nhân vật được chọn một giọng riêng trong tài khoản theo giới tính và tuổi. ElevenLabs không chỉnh được cao độ, nên tuổi và ma chỉ làm chậm tốc độ đọc. Mỗi câu đã đọc được lưu trong `cache/tts/`, nên dựng lại video không tốn thêm ký tự. Gói Free có khoảng 10.000 ký tự/tháng và **không được dùng cho kênh bật kiếm tiền**.

Nếu bước tạo ảnh lỗi (mạng, hết hạn mức), tool tự dùng ảnh vẽ bằng code cho lần chạy đó, không làm hỏng cả video. Ảnh tạo thành công được cache theo prompt, nên chạy lại không tốn thêm.

### Dùng Codex (tính vào gói ChatGPT, không cần API key)

```bash
npm install -g @openai/codex   # bản cài hiện tại trên máy đang hỏng (thiếu file chạy chính)
codex login                    # đăng nhập bằng tài khoản ChatGPT
```

Sau đó đặt `LLM_PROVIDER=codex` và/hoặc `IMAGE_PROVIDER=codex`. Ảnh được tạo bằng `codex exec '$imagegen …'`. Codex lưu ảnh vào `~/.codex/generated_images/` và tool lấy ảnh mới nhất trong đó. Theo tài liệu bên thứ ba, cần gói Plus trở lên, và mỗi lần tạo ảnh dùng hạn mức nhanh hơn chat thường khoảng 3–5 lần.

## Kênh — `channel.json`

Gồm tên kênh, banner, nhân vật chính (tên, tính cách đưa vào prompt, màu tóc, da, áo, viền), phong cách ảnh nền và giọng đọc theo ngôn ngữ. Sửa được trong trang Cài đặt.

## Kịch bản — `scenes.json`

Mẫu đầy đủ: [examples/ma_da_cast.scenes.json](examples/ma_da_cast.scenes.json) (Tư, Bà và Ma da nói chuyện với nhau).

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
| `camera` | `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `static` |

Tự động khi dựng:
- Ai đang nói thì nhép miệng; người nghe quay mặt về phía người nói.
- Nhân vật có mặt ở cảnh trước tự đi bộ sang vị trí mới.
- Phụ đề có tên người nói (màu vàng).

Giọng nhân vật: giới tính lấy theo preset, cao độ và tốc độ chỉnh theo tuổi (trẻ con cao hơn, người già trầm và chậm hơn). Tiếng Việt chỉ có 2 giọng gốc (NamMinh, HoaiMy), nên các nhân vật được phân biệt bằng cao độ.

Kịch bản kiểu cũ (`narration`, `pose`… ở cấp cảnh) vẫn dựng được. Khi mở trong web UI, kịch bản cũ được tự chuyển sang định dạng mới; file chỉ thay đổi khi bạn bấm Lưu.

## Cấu trúc code

- `storyvid/script.py`: prompt, schema, chuẩn hóa kịch bản, chế độ offline
- `storyvid/llm.py`: provider chuẩn OpenAI và Codex CLI
- `storyvid/tts.py`: edge-tts hoặc ElevenLabs, phụ đề có dấu câu
- `storyvid/elevenlabs.py`: gọi ElevenLabs, chọn giọng, cache
- `storyvid/backgrounds.py`: ảnh nền procedural, Codex hoặc fal
- `storyvid/character.py`: nhân vật chính vẽ bằng code
- `storyvid/render.py`: dựng khung hình, ffmpeg
- `storyvid/cli.py`: các bước dòng lệnh, đọc `.env`
- `storyvid/web/`: web UI (Flask + HTML/JS thuần)

## Bộ nhân vật Việt Nam tách mảnh

Tám mẫu có sẵn: `young_man`, `young_woman`, `elder_man`, `elder_woman`, `boy`, `girl`, `middle_man`, `middle_woman`. Trẻ em có đầu lớn hơn tương đối và chiều cao thấp hơn; người già có tóc bạc, nếp nhăn; trang phục đời thường màu đất, chàm, rêu hoặc màu mộc.

Trong tab **Kịch bản → Nhân vật của video**, chọn mẫu, màu trang phục và phụ kiện (túi vải, khăn rằn, đèn pin). Bật tùy chỉnh màu nếu cần, rồi **Lưu kịch bản**. Lựa chọn dùng xuyên suốt video, được giữ khi viết lại kịch bản. Việc chọn nhân vật không tự đổi giọng đọc: giọng vẫn theo ngôn ngữ và cấu hình kênh. Kịch bản đã viết cần viết lại nếu muốn lời kể khớp danh tính mới.

```json
"character": {
  "preset": "elder_woman",
  "outfit": "indigo",
  "accessory": "bag"
}
```

Thêm `skin_color`, `hair_color`, `shirt_color`, `outline_color` dạng `#rrggbb` để ghi đè màu riêng. Kịch bản cũ thiếu `character` dùng `channel.json.host` như trước. Tất cả ảnh/SVG dùng để ghép đều có nền trong suốt. Nhân vật được raster hóa bằng `resvg-py` rồi lưu đệm trong bộ nhớ, không cần dịch vụ AI.

### Sửa và thay mảnh

Nguồn nằm ở `assets/characters/<preset>/`, mỗi mẫu có `rig.json` và các file SVG độc lập: đầu, tóc trước/sau, cổ, thân áo, tay trên, cẳng tay, bàn tay, đùi, cẳng chân, dép, phụ kiện; mắt, mày, miệng có file riêng theo trạng thái.

- Mảnh được vẽ quanh điểm neo cục bộ `(0, 0)`. Giữ điểm neo khi thay bằng hình mới; hoặc cập nhật `parts.<tên>.pivot` trong manifest.
- `anchors` xác định cổ, đầu, thân, vai trái/phải, hông trái/phải. `lengths` xác định khoảng cách khớp; tay và chân trái/phải dùng cùng nguồn mảnh với transform riêng.
- Các biến màu là `{{skin}}`, `{{hair}}`, `{{shirt}}`, `{{pants}}`, `{{ink}}`. Không thay chúng nếu muốn tiếp tục đổi màu trong giao diện.
- SVG gốc có `viewBox="-120 -130 240 300"`, nhưng khi ghép chỉ nội dung bên trong SVG được dùng, không bị giới hạn bởi viewBox của mảnh. Sprite có lề để tay duỗi và phụ kiện không bị cắt.
- Sửa SVG rồi dựng lại video hoặc gọi preview để thấy cập nhật. **Không chạy lại `build_character_assets.py` sau khi sửa thủ công** trừ khi muốn ghi đè toàn bộ bộ nguồn bằng mẫu ban đầu.

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python tools/preview_characters.py
.venv/bin/python tools/render_character_demo.py
.venv/bin/python -m unittest discover -s tests -v
node --check storyvid/web/static/app.js
```

Kết quả tại `output/character-library/`: `cast-gallery.png`, `parts-sheet.png`, `character-motion-demo.mp4`, cùng thư mục từng nhân vật có SVG ghép hoàn chỉnh và PNG từng mảnh. Clip thử dùng âm thanh tổng hợp để kiểm tra chuyển động miệng, không phải giọng kể. Các MP4 cũ không bị ghi đè.
