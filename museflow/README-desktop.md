# MuseFlow Desktop

Bản Electron của [MuseFlow](https://github.com/bynne2602/museflow): một app quản lý nhiều tài khoản Muse.ai đã đăng nhập, chạy các node ảnh/video song song và tự động biến truyện thành video.

## Chạy

```bash
npm install
npm start
```

App mở ở tab **🎬 Dự án video**: web UI storyvid (dự án, kịch bản, duyệt, hình Muse, giọng đọc, dựng, hoàn thành), do app tự chạy bằng `../.venv/bin/python -m storyvid.web`. Tab **🧩 Canvas** là canvas MuseFlow bên dưới, với bảng **Flow dự án** ở trên cùng: tiến độ từng bước của dự án video, bấm một bước để mở nó.

1. Bấm **Accounts** → **＋ Add account**. Một cửa sổ Muse riêng mở ra (cookie riêng cho từng tài khoản). Đăng nhập rồi mở trang chat của Muse.
2. Lặp lại cho các tài khoản khác. Tài khoản xanh = sẵn sàng. Đóng cửa sổ Muse chỉ ẩn nó, app vẫn dùng được.
   - **Tự đăng nhập (email + mã)**: mở mục **Auto sign-in** trong bảng Accounts, điền URL trang hộp thư của domain nhận mã (dùng `{email}`, `{user}`, `{domain}`, ví dụ `https://mail.example.com/inbox/{email}`), dán danh sách email (mỗi dòng một cái) → **＋ Add & sign in**. App tự nhập email trên Muse, mở trang hộp thư trong cửa sổ ẩn, lấy mã *mới* (mã đã có trước đó bị bỏ qua) và nhập vào. Các tài khoản đăng nhập lần lượt; tài khoản bị đăng xuất tự đăng nhập lại (tối đa 1 lần mỗi 10 phút). Trang hộp thư cần đăng nhập thì bấm **Open inbox site** đăng nhập một lần, phiên được lưu ở `persist:otp-inbox`.
3. Bấm **📖 Truyện → Video**, dán truyện, chọn số giây mỗi cảnh, khung hình, phong cách → **▶ Tạo video**.

Luồng tự động: Muse viết kịch bản theo template `templates/museflow-scene-script-template-vi.txt` (truyện dài được chia thành nhiều phần ~3500 ký tự) → tạo node ảnh/video cho từng cảnh → chạy song song, mỗi tài khoản rảnh nhận một node → ghép MP4 bằng FFmpeg WASM → lưu vào `~/Downloads/MuseFlow/`.

- **Chỉ tạo kịch bản**: mở kịch bản trong Script → Nodes để sửa trước khi tạo node.
- **Copy prompt**: lấy prompt để dán vào AI khác (ChatGPT, Claude…), rồi dán kết quả vào Script → Nodes.
- **Nối khung cuối giữa các cảnh**: mượt hơn, nhưng video phải chạy lần lượt từng cái.

## Cấu trúc

| File | Vai trò |
|---|---|
| `electron/main.js` | Chạy và tắt web UI storyvid (`STORYVID_PYTHON`, `STORYVID_WEB_PORT`), protocol `museflow://`, quản lý tài khoản (mỗi tài khoản một `persist:muse-<id>` partition + cửa sổ), hàng đợi chia job cho tài khoản rảnh, tải video về `userData/media`. |
| `electron/autologin.js` | Tự đăng nhập Muse bằng email + mã: điền form trên trang Muse, đọc mã mới từ trang hộp thư (URL mẫu `otpInboxUrl` trong `storage.json`). |
| `electron/muse-preload.js` | Nạp `muse-bridge.js` vào trang Muse, nối `chrome.runtime.onMessage` sang IPC. |
| `electron/app-preload.js`, `desktop-shim.js` | API `museDesktop` + shim `chrome.storage`/`chrome.runtime` cho `app.js`. |
| `muse-bridge.js` | Điều khiển DOM chat Muse (giữ từ extension) + lệnh mới `MUSEFLOW_CHAT` để lấy câu trả lời dạng text. |
| `storyvid-view.js` | Tab Dự án video / Canvas, hiện web UI storyvid trong khung. |
| `app.js` | Canvas/timeline gốc; vòng chạy workflow chạy song song theo phụ thuộc; panel Accounts; luồng Truyện → Video. |

## Test không cần tài khoản thật

```bash
npm run mock-muse        # terminal 1: trang chat Muse giả ở 127.0.0.1:4777
npm run start:mock       # terminal 2: app trỏ các tài khoản vào trang giả
```

Trang giả trả kịch bản mẫu cho yêu cầu viết kịch bản, ảnh PNG cho yêu cầu ảnh và video WebM ngắn cho yêu cầu video.

## Phiên đăng nhập và debug

Phiên đăng nhập của mỗi tài khoản nằm trong `~/Library/Application Support/museflow-desktop/Partitions/muse-<id>` (danh sách tài khoản: `profiles.json` cùng thư mục) và còn nguyên sau khi tắt app. Không cần và không nên chép cookie/token ra ngoài.

Để điều khiển/kiểm tra app bằng DevTools Protocol khi test:

```bash
npx electron . --remote-debugging-port=9333
```

## API cho storyvid

Khi app chạy, MuseFlow mở API ở `http://127.0.0.1:8770` (đổi bằng `MUSEFLOW_API_PORT`). API chỉ nhận request từ máy này và từ chối mọi request có header `Origin`, nên trang web không gọi được.

| Lệnh | Việc |
|---|---|
| `GET /api/status` | Danh sách tài khoản và số tài khoản sẵn sàng |
| `POST /api/generate` | `{mediaType: "image"\|"video", prompt, size, duration, negative, references: [đường dẫn ảnh], saveTo: đường dẫn tuyệt đối}` → tạo trên một tài khoản rảnh, lưu file, trả `{ok, file}`. Bị từ chối thì tự thử lại một lần với phiên bản an toàn hơn. |
| `POST /api/chat` | `{prompt}` → câu trả lời dạng chữ của Muse |
| `POST /api/stop` | Dừng mọi việc đang chạy và đang chờ |

storyvid dùng API này qua `python -m storyvid.visuals` và tab **Hình Muse** của web UI (xem `../docs/pipeline.md`).
