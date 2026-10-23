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
- Mục `owner: "tool"` trong `review.json` là lỗi code: báo cho người dùng, không agent nào tự sửa.
- Trước khi bàn giao:
  - Kịch bản: `.venv/bin/python -m storyvid.check output/<id>/scenes.json` (0 = đạt, 1 = sai chuẩn, 2 = thiếu asset).
  - Asset: `.venv/bin/python -m storyvid.check --assets` phải ra 0.
  - Báo cáo kiểm định: `.venv/bin/python -m storyvid.check --review output/<id>/review.json` phải ra 0.
  - Code: `.venv/bin/python -m unittest discover -s tests` phải qua hết.
- Dựng video: `.venv/bin/python -m storyvid.cli --script output/<id>/scenes.json`; thêm `--short` để dựng Short 9:16. Chỉ dùng `--fallback` để xem nháp.
- Đổi chuẩn: sửa `storyvid/contract.py`, chạy `.venv/bin/python -m storyvid.check --write-schema`, cập nhật `docs/pipeline.md` và `examples/`.
