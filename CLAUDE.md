# Project Rules
- Git: làm và commit trực tiếp trên nhánh `main`, không tạo nhánh mới trừ khi tôi yêu cầu.
- Rule của dự án nằm ở cả `CLAUDE.md` và `AGENTS.md`. Khi thêm hoặc sửa rule, cập nhật cả hai file cho giống nhau.

## Flow nhiều agent (chi tiết: `docs/pipeline.md`)
- Mọi kịch bản theo chuẩn `storyvid.scenes/1` (`storyvid/contract.py`, schema ở `schema/scenes.v1.schema.json`). Không thêm trường, không đổi giá trị cố định. Mã nền, đồ vật, nhân vật ưu tiên lấy trong `schema/assets.catalog.json`; mã mới chỉ dùng khi thật cần và sẽ thành yêu cầu asset cho Codex.
- Claude: viết và sửa `scenes.json`, chạy kiểm tra, dựng video, sửa code tool. Không vẽ asset.
- Codex: chỉ vẽ asset được yêu cầu trong `output/<id>/asset_requests.json`, đặt vào `assets/bac-bo-stick/extra/` và đăng ký trong `extra/manifest.json`. Không sửa `scenes.json`, code `storyvid/` hay bộ gốc ngoài `extra/`.
- Trước khi bàn giao:
  - Kịch bản: `.venv/bin/python -m storyvid.check output/<id>/scenes.json` (0 = đạt, 1 = sai chuẩn, 2 = thiếu asset).
  - Asset: `.venv/bin/python -m storyvid.check --assets` phải ra 0.
  - Code: `.venv/bin/python -m unittest discover -s tests` phải qua hết.
- Dựng video: `.venv/bin/python -m storyvid.cli --script output/<id>/scenes.json`. Chỉ dùng `--fallback` để xem nháp.
- Đổi chuẩn: sửa `storyvid/contract.py`, chạy `.venv/bin/python -m storyvid.check --write-schema`, cập nhật `docs/pipeline.md` và `examples/`.
