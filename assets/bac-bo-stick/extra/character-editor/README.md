# Xưởng nhân vật — web 2D

Web local để người dùng chỉnh bộ phận nhân vật áo kem trước khi AI tinh chỉnh trong Blender. Dùng ảnh PNG thật từ `../human-action-trial-v1/`; không cần npm, không gọi dịch vụ AI hay tải font ngoài.

## Mở web

Có thể bấm đúp `Open-Editor.command` trong Finder để chạy. Nếu server đã chạy, chỉ cần mở đường dẫn bên dưới.

Hoặc từ thư mục dự án:

```sh
.venv/bin/python assets/bac-bo-stick/extra/character-editor/serve.py
```

Mở **http://127.0.0.1:8766**. Có thể chọn cổng khác bằng `--port 8767`. Giữ terminal chạy khi sử dụng. Server chỉ lắng nghe localhost, chỉ phục vụ file web và ảnh đã cho phép, chỉ ghi vào thư mục bản lưu.

## Cách chỉnh

1. Chọn bộ phận bằng danh sách bên trái (có ô tìm kiếm) hoặc ô **Bộ phận đang chọn** ngay trên khung hình. Khi chọn bằng danh sách, **Giữ lựa chọn** tự bật: kéo trên khung sẽ di chuyển đúng mảnh đó, kể cả mảnh nhỏ hoặc bị che bởi áo. Bỏ chọn **Giữ lựa chọn** để bấm chọn mảnh khác trực tiếp trên hình. Chấm cam có dấu cộng là tay nắm di chuyển; góc vuông đổi kích thước, chấm trắng phía trên để xoay.
2. Để thay một mảnh bằng ảnh khác trong bộ PNG hiện có, chọn mảnh rồi dùng **Thay ảnh bộ phận** bên phải. Chọn tên trong danh sách hoặc bấm **Chọn bằng hình** để xem hình thu nhỏ. **Ảnh ban đầu** khôi phục ảnh gốc của riêng mảnh đó. Thao tác thay ảnh giữ nguyên mã mảnh, vị trí, kích thước, góc xoay, điểm xoay, trạng thái hiển thị và z-index; không thay các mảnh khác. Có thể hoàn tác, lưu JSON và nhập sang Blender như bình thường. Bộ chọn này dùng 20 ảnh hiện có, chưa hỗ trợ tải ảnh ngoài.

3. Kéo các góc viền cam để thay đổi rộng/cao; kéo chấm tròn phía trên để xoay. Bảng bên phải nhập số chính xác. Thu phóng khi chỉnh chi tiết.
4. Chọn **Điểm xoay**, chọn mảnh bên trái rồi kéo trong mảnh để đặt khớp. Di chuyển điểm xoay giữ nguyên hình vẽ trên khung; góc xoay tiếp theo quay quanh khớp mới.
5. Mỗi hàng trong danh sách hiển thị **z-index**. Kéo hàng bằng dấu ⠿ lên/xuống; vạch cam cho biết vị trí thả. Trên danh sách = nằm phía trước. Có thể nhập số **Z-index** (số lớn nằm trước), dùng nút **Lên / Xuống một lớp**, hoặc **Lên trước / Ra sau** để đưa ra ngoài cùng. Kéo xếp hàng sẽ đánh lại z-index liên tiếp, giữ nguyên vị trí/kích thước/biểu cảm; có thể hoàn tác. Trên điện thoại dùng nút một lớp. Khi hàng được focus, Alt + mũi tên lên/xuống cũng đổi lớp. Bật/tắt mảnh, đổi biểu cảm. Trái/phải tính theo phía người xem.
6. Tư thế **Giơ đèn pin / Giật mình / Đi bộ** là xem thử từ bản đang chỉnh. Nút **Giữ tư thế** chụp tư thế đó vào bản chỉnh; nếu không bấm, lưu/xuất JSON vẫn lấy bản gốc đang chỉnh. Chọn hoặc kéo mảnh sẽ quay về chế độ chỉnh.
7. **Hoàn tác / Làm lại** hoặc ⌘Z / ⌘⇧Z (Windows Ctrl). Phím mũi tên dịch 1 px, Shift dịch 10 px khi không nhập liệu.

### Di chuyển cả cụm

- Tích các ô ở đầu hàng trong danh sách để thêm/bớt mảnh, hoặc Shift/Ctrl/⌘ + bấm hàng. Bấm thường sẽ chọn riêng một mảnh.
- Mục **Chọn cụm** trên khung có sẵn hai tay, hai chân, thân và hai tay, toàn bộ nhân vật. Cụm có thể bao gồm miếng đang ẩn; chúng vẫn được dịch cùng cụm.
- Khi chọn từ hai mảnh trở lên, khung cam bao quanh cụm. Kéo trên khung khi **Giữ lựa chọn** bật để di chuyển cả cụm. Phím mũi tên, Shift + mũi tên và nhập X/Y cũng dịch cả cụm.
- Các mảnh nhận cùng một độ dịch chuyển, giữ khoảng cách, kích thước, góc xoay, khớp, ảnh và z-index. Khi tới giới hạn vị trí, toàn cụm dừng cùng nhau. Một lần hoàn tác khôi phục cả lần kéo.
- **Chọn riêng** quay về chỉnh một mảnh. Trong chế độ cụm, các thông số khác ngoài X/Y vẫn chỉ chỉnh mảnh chính ghi ở bảng bên phải. Muốn xoay hoặc đổi kích thước, chọn riêng mảnh.
- Tập lựa chọn là trạng thái làm việc tạm thời; vị trí kết quả của từng mảnh được lưu trong JSON hiện có, không đổi hợp đồng Blender.

Trình duyệt tự lưu bản nháp theo địa chỉ/cổng. **Lưu vào máy** ghi JSON vào:

```
output/stung_treng/character-editor/layouts/<ten-ban-luu>.json
```

Đổi tên để lưu phiên bản mới. Cùng tên sẽ cập nhật file đó. **Xuất JSON** tải thêm bản sao để chuyển máy/lưu dự phòng. **Nhập JSON** kiểm tra trước khi thay bản hiện tại; có thể hoàn tác. **Tải PNG** xuất hình trong suốt của tư thế đang nhìn, không kèm khớp/nền/thu phóng.

Bản lưu trên máy và bản tự lưu trình duyệt là hai nơi riêng: khi xóa dữ liệu trình duyệt, vẫn mở lại bản JSON đã lưu trên máy. Nên lưu file trước khi đóng trang. Không gửi dữ liệu lên mạng.

## Handoff cho AI / Blender

JSON `character-layout/1` độc lập với `storyvid.scenes/1`. `canvas` tính pixel. Mỗi phần có `asset` thuộc bộ PNG cố định; `x,y` là điểm xoay tuyệt đối, trục Y hướng xuống; `pivotX,pivotY` chuẩn hóa 0–1; `width,height` tính px; `rotation` độ theo chiều kim đồng hồ; `z` lớn hơn nằm trước. Cùng z giữ thứ tự mảng. `visible` quyết định render.

AI đọc JSON được người dùng duyệt làm chuẩn về bố cục, tỷ lệ, khớp và biểu cảm. Nhập một bản tham chiếu có thể chỉnh trực tiếp trong Blender:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python assets/bac-bo-stick/extra/character-editor/import_blender.py -- \
  --layout output/stung_treng/character-editor/layouts/nhan-vat-01.json \
  --out output/stung_treng/character-editor/nhan-vat-01.blend --render
```

Chọn file `--out` mới hoặc thêm `--force` nếu muốn ghi đè. File Blender chứa các mesh PNG riêng, origin đúng điểm xoay, texture đóng gói và bản JSON gốc trong Text Editor. Góc xoay / thứ tự lớp / hiển thị được giữ. 200 px = 1 Blender unit.

Đây là **bố cục tham chiếu có thể chỉnh**, chưa tự sửa xương hoặc retarget chuỗi hành động 12 giây. Bước sau AI tối ưu rig Blender dựa trên cấu hình đã duyệt. Chuyển động web chỉ là mô phỏng hình học 2D để tìm chỗ hở, chưa có IK, giữ chân trên đất, biến dạng áo hay kết quả render Blender. Không thay đổi `storyvid/`, `scenes.json`, `review.json` hoặc bộ rig hiện tại.

## Kiểm tra

```sh
.venv/bin/python -m unittest discover -s assets/bac-bo-stick/extra/character-editor/tests
node assets/bac-bo-stick/extra/character-editor/tests/model.test.mjs
# Cần server đang chạy, Playwright + Google Chrome. Test ghi qa-layout.json và ảnh QA vào output/.
NODE_PATH=/Users/thang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
  node assets/bac-bo-stick/extra/character-editor/tests/browser.cjs
/Applications/Blender.app/Contents/MacOS/Blender --background \
  output/stung_treng/character-editor/nhan-vat-01.blend \
  --python assets/bac-bo-stick/extra/character-editor/tests/verify_blender.py
```

Selection tests: run `node assets/bac-bo-stick/extra/character-editor/tests/selection.cjs` with the same NODE_PATH/server as browser tests. They cover searchable lists, the quick selector, locked selection for thin/overlapped pieces, hidden pieces and mobile selection.

Browser tests cover drag, pivot, undo/redo, expression, import/export, saving/loading/reloading, PNG export, visibility/layer order, malformed input and mobile overflow. Blender verification reopens the saved file and checks all mesh corners against JSON with tolerance 0.001 px plus packed images and visibility. Project unit tests / asset checker are run separately.

Layer UI regression test: `node assets/bac-bo-stick/extra/character-editor/tests/layers.cjs` with the same NODE_PATH/server checks actual drag/drop, numeric z-index, one-step buttons, undo/redo, persisted reload and mobile controls.

Image replacement regression test: `node assets/bac-bo-stick/extra/character-editor/tests/replacement.cjs` with the same NODE_PATH/server checks both image pickers, unchanged transforms, undo/redo, disk persistence, reset and mobile. Blender verification additionally checks each layer texture matches its saved `asset` ID.

Group movement test: `node assets/bac-bo-stick/extra/character-editor/tests/groups.cjs` with the same NODE_PATH/server verifies multi-selection, unchanged relative placement, nonselected pieces, undo/redo, keyboard/numeric translation and mobile presets. Model tests cover common-delta clamping at coordinate bounds.
