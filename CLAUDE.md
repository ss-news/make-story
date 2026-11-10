# Project Rules
- Git: làm và commit trực tiếp trên nhánh `main`, không tạo nhánh mới trừ khi tôi yêu cầu.
- Rule của dự án nằm ở cả `CLAUDE.md` và `AGENTS.md`. Khi thêm hoặc sửa rule, cập nhật cả hai file cho giống nhau.

## Flow nhiều agent (chi tiết: `docs/pipeline.md`)
- Mọi kịch bản theo chuẩn `storyvid.scenes/1` (`storyvid/contract.py`, schema ở `schema/scenes.v1.schema.json`). Không thêm trường, không đổi giá trị cố định. Mã nền, đồ vật, nhân vật ưu tiên lấy trong `schema/assets.catalog.json`; mã mới chỉ dùng khi thật cần và sẽ thành yêu cầu asset.
- **Claude** (phân tích và kiểm định):
  - Phân tích truyện, chia cảnh, viết bản đầu tiên của `output/<id>/scenes.json`, chọn `short.scenes` cho Short 9:16.
  - Sau bản đầu tiên, không sửa `scenes.json` và không vẽ asset. Mọi chỗ cần sửa ghi vào `output/<id>/review.json` (chuẩn `storyvid.review/1`, schema ở `schema/review.v1.schema.json`).
  - Kiểm định: chạy kiểm tra, dựng video, xem và chấm kịch bản lẫn video, ghi `review.json` với `verdict` là `pass` hoặc `fix`.
- **Codex** (sửa kịch bản và vẽ asset):
  - Sửa và hoàn thiện `output/<id>/scenes.json`: lời thoại, diễn xuất, đồ vật, âm thanh (`music`, `ambience`, `sfx`, chỉ chọn mã có trong `schema/assets.catalog.json`), và các mục `owner: "codex"` trong `review.json`.
  - Vẽ asset được yêu cầu trong `output/<id>/asset_requests.json`, đặt vào `assets/bac-bo-stick/extra/` và đăng ký trong `extra/manifest.json`.
  - Không sửa code `storyvid/`, bộ asset gốc ngoài `extra/`, hay `review.json`.
- **Checklist review `docs/review-checklist.md` bắt buộc cho cả Claude và Codex:**
  - Claude: khi chia cảnh (bản đầu) tự soát phần 2–5 và 7; khi kiểm định đi hết phần 1–7, mục ★ không đạt ghi tối thiểu `major` vào `review.json`.
  - Codex: trước khi bàn giao `scenes.json` hoặc asset, tự soát phần 1–7 (những mục thuộc kịch bản và asset) và sửa hết mục ★ chưa đạt; mục không tự sửa được thì nêu rõ khi bàn giao.
  - Khi bàn giao, cả hai báo mục nào chưa đạt. Phần 8–9 do người dùng làm, agent chỉ nhắc.
- Mục `owner: "tool"` trong `review.json` là lỗi code: báo cho người dùng, không agent nào tự sửa.
- Trước khi bàn giao:
  - Kịch bản: `.venv/bin/python -m storyvid.check output/<id>/scenes.json` (0 = đạt, 1 = sai chuẩn, 2 = thiếu asset).
  - Asset: `.venv/bin/python -m storyvid.check --assets` phải ra 0.
  - Báo cáo kiểm định: `.venv/bin/python -m storyvid.check --review output/<id>/review.json` phải ra 0.
  - Code: `.venv/bin/python -m unittest discover -s tests` phải qua hết.
- Dựng video: `.venv/bin/python -m storyvid.cli --script output/<id>/scenes.json`; thêm `--short` để dựng Short 9:16. Chỉ dùng `--fallback` để xem nháp.
- Đổi chuẩn: sửa `storyvid/contract.py`, chạy `.venv/bin/python -m storyvid.check --write-schema`, cập nhật `docs/pipeline.md` và `examples/`.

- Storyboard (`storyvid/storyboard.py`, chi tiết `docs/pipeline.md` mục “Storyboard”): tool viết kịch bản như làm phim, treatment (logline, nhân vật chính muốn gì, trở ngại, cold open, beat sheet) rồi shot list (cỡ cảnh, góc máy, chuyển động, hành động, chuyển cảnh); mỗi shot là một cảnh của `scenes.json`, phần còn lại ở `output/<id>/storyboard.json`. Khi chia cảnh tay, Claude cũng theo các quy tắc nghề trong đó: cảnh nào cũng có xung đột và bước ngoặt, cho xem thay vì kể, đổi cỡ cảnh.
- Hình AI bằng Muse: kế hoạch ở `output/<id>/visuals.json` (chuẩn `storyvid.visuals/1`, schema `schema/visuals.v1.schema.json`), tạo bằng `python -m storyvid.visuals prompts|cast|scenes output/<id>` qua MuseFlow (`museflow/`), dựng bằng `--visuals`. Kiểm tra: `.venv/bin/python -m storyvid.check --visuals output/<id>/visuals.json` phải ra 0. Không dồn mô tả cả dàn nhân vật vào mọi prompt: prompt cảnh chỉ nói về người đang có mặt. Sau khi tạo ảnh mẫu nhân vật, dừng cho người dùng duyệt trước khi tạo cảnh hàng loạt: bước `scenes` chỉ chạy khi `meta.json` `approved_cast` khớp ảnh mẫu hiện tại (nút “Duyệt nhân vật”); agent không tự ghi `approved_cast`. `python -m storyvid.auto output/<id>` (nút “▶ Chạy tự động đến video”) chạy nối các bước còn lại và dừng ở hai cổng duyệt đó. Cảnh có địa điểm thật thì thêm ảnh vào `refs/places.json` (`storyvid/places.py`); ảnh báo chí chỉ để Muse tham khảo, không đưa thẳng vào video.
- Nhất quán hình/clip Muse: bắt buộc theo `docs/visual-continuity.md`: khóa ảnh và mô tả nhân vật–địa điểm–đồ vật, lập `output/<id>/continuity.md` ánh xạ từng cảnh với tham chiếu/trạng thái, dùng `refs/places.json` cho bối cảnh lặp lại; kiểm nhóm thử 3–5 shot (toàn, đổi góc, cận, quay lại) trước khi tạo theo lô tối đa 10 cảnh. Cùng series tái dùng đúng mẫu đã chốt. `continuity` chỉ nối chuyển động, không thay ảnh tham chiếu kiến trúc; không dùng `all` để chữa đổi nhà. App có mục **Khóa hình ảnh** và cổng **Duyệt bộ mẫu** (`refs/continuity.json`): thay ảnh/mô tả/gán cảnh/prompt phải duyệt lại; backend, CLI và `auto` chặn tạo cảnh khi chưa duyệt. App truyền mẫu địa điểm/đồ vật vào cả ảnh và clip, báo cảnh cũ qua `refs/generated.json`; ô **Cảnh chạy thử** tạo nhóm tối đa 10 cảnh. Đánh giá nhóm thử vẫn do người/agent xem, không chạy hàng loạt trước khi đạt. Không thêm trường schema hoặc tự ghi bất kỳ trạng thái duyệt nào ngoài test.
- Cổng duyệt: các bước AI tạo hình chỉ chạy khi người thật đã duyệt đúng bản `scenes.json` hiện tại (`meta.json` `approved_script`, nút “Duyệt kịch bản” trên web UI). Agent không tự ghi `approved_script` và không dùng `--skip-review` ngoài test. Phong cách lấy từ `meta.json` `style` (`storyvid/styles.py`), không tự đổi khi người dùng đã chọn.
- Hoàn thành video: mọi video kết thúc qua tab **6. Hoàn thành** (`storyvid/finish.py`, chi tiết `docs/pipeline.md` mục “Hoàn thành video”): máy kiểm tra (`python -m storyvid.finish check`) phải đạt hết, kể cả âm lượng (`loudnorm` khi cần) → kiểm định nội dung ghi `review.json` (`fix` thì tạo lại cảnh, dựng lại, kiểm lại) → Short (tùy chọn) → gói đăng (`publish/`) → người dùng tự đăng và dán link. Agent không đăng lên YouTube thay người dùng.
- App Electron `museflow/` (`npm start`) tự chạy web UI storyvid và hiện nó ở tab “Dự án video”; sửa web UI thì vẫn sửa trong `storyvid/web/`.
- `museflow/` là code GPL-2.0 (gốc bynne2602/museflow); giữ `museflow/LICENSE` và ghi chú bản quyền khi sửa.
- Bộ ma nguyên ảnh dùng Blender: chuẩn nguồn ở `assets/bac-bo-stick/extra/whole-ghosts-v1/` (PNG RGBA theo tư thế, manifest riêng, không cắt khớp tay chân). Đây là chuẩn nguồn cho Blender, chưa thay đổi hợp đồng `storyvid.scenes/1`; không tự đưa pose mới vào scenes.json hoặc đăng ký nhân vật PNG thành props.

## Lưu ý nội dung từ số liệu YouTube (chi tiết: `docs/research/2026-10-28-ma-lon-analytics.md`)
- Tool làm nhiều loại video (`meta.json` `genre`, `storyvid/script.py` `GENRE_INFO`): `story` truyện ma, dân gian; `drama` truyện đời thường, kịch tính; `comedy` hoạt hình vui nhộn (nhân vật con vật biết nói, gag nối nhau, 30 giây đầu là cảnh buồn cười nhất); `build` xây dựng, làm thủ công (không lời: cảnh dài theo clip, giữ tiếng của clip, dòng `narrator` thành chữ báo công đoạn); `explainer` kiến thức. Dự án nào cũng tắt được lời đọc (`meta.json` `no_voice`, ô “Không lời đọc, chỉ tiếng clip”): video dùng tiếng của clip Muse, lời thoại thành chữ, cảnh vẫn cắt như thường. Loại nào cũng phải trông đúng loại đó; không áp quy tắc riêng của loại này cho loại khác.
- Ma Lon: CTR 1,1%, xem trung bình 43 giây trên 10 phút, bị YouTube đề xuất cạnh Mr Bean và hoạt hình thiếu nhi. Bài học chung cho mọi loại:
- 30 giây đầu: khoảnh khắc mạnh nhất của video (truyện ma: cảnh đáng sợ nhất; đời thường: lúc mâu thuẫn lên đỉnh; kiến thức: câu hỏi hoặc điều bất ngờ), chủ thể to và rõ giữa khung, kết bằng câu hỏi. Không tả bối cảnh dài trước khi có chuyện. Claude kiểm tra điều này khi chia cảnh và khi chấm.
- Mỗi video có thumbnail riêng: một chủ thể thật to, cảm xúc rõ, một màu nhấn, chữ tối đa 3–4 từ. Không dùng khung hình tự cắt.
- Riêng truyện ma: nền tối, bóng đổ, nhân vật biểu cảm sợ chứ không hài, tránh khung hình dễ nhầm với hoạt hình thiếu nhi; 30 giây đầu không tả làng hay cảnh ban ngày trước khi có điều lạ; thumbnail nền tối, chủ thể đáng sợ.
- Riêng hoạt hình vui nhộn: nhân vật con vật giữ thân con vật (không vẽ thành người), màu tươi, nét mặt cường điệu; tiếng cười đến từ tính cách nhân vật, không giảng đạo; thumbnail là hai nhân vật chính với nét mặt buồn cười giữa tình huống.
- Riêng truyện đời thường: cảm xúc thật qua nét mặt và hành động, không sến, không giảng đạo; thumbnail là gương mặt nhân vật chính với cảm xúc mạnh.
- Short: dựng thẳng ở khung dọc, không cắt mất hình từ bản 16:9 (clip ngang hiện trọn trên nền mờ), chủ thể to nhất có thể, không để dải đen lớn, chữ nằm trong vùng an toàn của TikTok/Reels/Shorts (README, mục “Short 9:16”).
- Khi đăng: bản 1080p (không dùng bản nén), tải phụ đề SRT, không đánh dấu dành cho trẻ em. Sau 48 giờ đọc lại CTR, đường giữ chân và các video YouTube đề xuất cạnh.
