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

- Hình AI bằng Muse: kế hoạch ở `output/<id>/visuals.json` (chuẩn `storyvid.visuals/1`, schema `schema/visuals.v1.schema.json`), tạo bằng `python -m storyvid.visuals prompts|cast|scenes output/<id>` qua MuseFlow (`museflow/`), dựng bằng `--visuals`. Kiểm tra: `.venv/bin/python -m storyvid.check --visuals output/<id>/visuals.json` phải ra 0. Không dồn mô tả cả dàn nhân vật vào mọi prompt: prompt cảnh chỉ nói về người đang có mặt. Sau khi tạo ảnh mẫu nhân vật, dừng cho người dùng duyệt trước khi tạo cảnh hàng loạt.
- Cổng duyệt: các bước AI tạo hình chỉ chạy khi người thật đã duyệt đúng bản `scenes.json` hiện tại (`meta.json` `approved_script`, nút “Duyệt kịch bản” trên web UI). Agent không tự ghi `approved_script` và không dùng `--skip-review` ngoài test. Phong cách lấy từ `meta.json` `style` (`storyvid/styles.py`), không tự đổi khi người dùng đã chọn.
- Hoàn thành video: mọi video kết thúc qua tab **6. Hoàn thành** (`storyvid/finish.py`, chi tiết `docs/pipeline.md` mục “Hoàn thành video”): máy kiểm tra (`python -m storyvid.finish check`) phải đạt hết, kể cả âm lượng (`loudnorm` khi cần) → kiểm định nội dung ghi `review.json` (`fix` thì tạo lại cảnh, dựng lại, kiểm lại) → Short (tùy chọn) → gói đăng (`publish/`) → người dùng tự đăng và dán link. Agent không đăng lên YouTube thay người dùng.
- `museflow/` là code GPL-2.0 (gốc bynne2602/museflow); giữ `museflow/LICENSE` và ghi chú bản quyền khi sửa.
- Bộ ma nguyên ảnh dùng Blender: chuẩn nguồn ở `assets/bac-bo-stick/extra/whole-ghosts-v1/` (PNG RGBA theo tư thế, manifest riêng, không cắt khớp tay chân). Đây là chuẩn nguồn cho Blender, chưa thay đổi hợp đồng `storyvid.scenes/1`; không tự đưa pose mới vào scenes.json hoặc đăng ký nhân vật PNG thành props.

## Lưu ý nội dung từ số liệu YouTube (chi tiết: `docs/research/2026-10-28-ma-lon-analytics.md`)
- Ma Lon: CTR 1,1%, xem trung bình 43 giây trên 10 phút, bị YouTube đề xuất cạnh Mr Bean và hoạt hình thiếu nhi. Áp dụng cho mọi clip sau:
- 30 giây đầu: cảnh đáng sợ nhất, chủ thể to và rõ giữa khung, kết bằng câu hỏi. Không tả làng, bối cảnh hay cảnh ban ngày trước khi có điều lạ. Claude kiểm tra điều này khi chia cảnh và khi chấm.
- Truyện ma phải trông như truyện ma: nền tối, bóng đổ, nhân vật biểu cảm sợ chứ không hài, tránh khung hình dễ nhầm với hoạt hình thiếu nhi.
- Mỗi video có thumbnail riêng: nền tối, một chủ thể đáng sợ thật to, một màu nhấn, chữ tối đa 3–4 từ. Không dùng khung hình tự cắt.
- Short: hình đầy khung dọc, chủ thể to, không để dải đen lớn.
- Khi đăng: bản 1080p (không dùng bản nén), tải phụ đề SRT, không đánh dấu dành cho trẻ em. Sau 48 giờ đọc lại CTR, đường giữ chân và các video YouTube đề xuất cạnh.
