# Quy trình giữ nhất quán hình và clip

Áp dụng cho mọi dự án dùng Muse, kể cả các tập trong cùng series. App đã có mục **Khóa hình ảnh**, cổng **Duyệt bộ mẫu** bắt buộc trước khi tạo cảnh và CLI/auto cũng kiểm cùng cổng. Việc đánh giá hình có thực sự giống nhau vẫn cần người xem; app chưa tự nhận diện sai kiến trúc. Các cổng duyệt kịch bản và nhân vật vẫn bắt buộc. Không thêm trường vào scenes.json, visuals.json hay storyboard.json ngoài schema.

## 1. Khóa thiết kế trước khi viết prompt từng cảnh

Tạo output/<id>/continuity.md theo mẫu bên dưới. Nhân vật, địa điểm và đồ vật xuất hiện lại phải có mô tả chuẩn duy nhất, ảnh tham chiếu và phiên bản. Cùng series dùng lại đúng file ảnh đã chốt, không viết lại ngoại hình hoặc tạo lại ảnh mẫu mỗi tập. Địa điểm khác dùng mẫu khác dù cùng là nhà, sân hay rừng.

- Nhân vật: khuôn mặt, tuổi, vóc dáng, tóc, trang phục, phụ kiện; tay xuất hiện trong cận cảnh cũng phải xác định là tay của ai và có actor tương ứng.
- Địa điểm: hình khối nhà, vật liệu, độ dốc mái, cửa/cửa sổ, ống khói; vị trí nhà–chuồng–cổng–hàng rào–suối. Ghi hướng theo sơ đồ mặt bằng, không ghi trái/phải khung hình như một thuộc tính cố định của địa điểm.
- Đồ vật: kích thước, màu, vật liệu, dấu hỏng riêng và người cầm. Đồ vật quan trọng dùng ảnh chi tiết tham chiếu; không đăng ký ảnh nhân vật thành prop.
- Trạng thái: ngày/đêm, thời tiết, tuyết, mức hư hỏng/sửa chữa, trang phục ướt/bẩn, vị trí người và vật. Mỗi thay đổi phải có nguyên nhân trong truyện; khi quay lại địa điểm phải dùng đúng trạng thái tại thời điểm đó.

Ảnh mẫu địa điểm cần góc rộng thấy rõ bố cục và ít nhất một góc kiểm chứng mặt nhà. Chốt ảnh chuẩn trước khi sinh cảnh; không lấy một ảnh ngẫu nhiên chưa kiểm tra làm chuẩn. Ảnh chuẩn là thiết kế của địa điểm, không buộc mọi shot có cùng góc máy. Không dùng ảnh có người không liên quan làm chuẩn trang phục/nhân vật.

## 2. Lập bảng cảnh → tham chiếu và trạng thái

Trong continuity.md, mỗi cảnh ghi số 1-based, địa điểm/phiên bản, thời điểm, người xuất hiện, vật quan trọng, trạng thái đầu/cuối, kiểu nối và cảnh phụ thuộc. Đối chiếu với cảnh 0-based trong visuals.json và review.json để tránh sửa lệch một cảnh.

Trong app, dùng **Khóa hình ảnh → Nhà / địa điểm hoặc Đồ vật**: tải ảnh, nhập mô tả bất biến và số cảnh 1-based, lưu rồi duyệt bộ mẫu. Dữ liệu nằm trong `refs/continuity.json`, không đổi schema kịch bản/hình. `refs/places.json` (storyvid.places/1) cũ vẫn được hỗ trợ và được tính vào mã duyệt; ảnh của panel cũ cũng được gửi vào ảnh mở và clip. Dùng danh sách scenes rõ ràng; không chỉ dựa từ khóa chung house/yard để gán nhầm địa điểm. sources ghi nguồn thực khi có, không tạo URL giả. Ảnh chuẩn phải nằm trong thư mục dự án.

Mỗi mẫu khóa dùng một ảnh; địa điểm trong panel cũ chỉ lấy ảnh đầu tiên. Tối đa 4 ảnh tham chiếu tổng cộng, tối đa 3 ảnh nhân vật. App từ chối duyệt nếu có cảnh vượt giới hạn ở bước ảnh hoặc clip; clip còn cần 1 ảnh mở, hoặc 2 ảnh nếu nối khung cuối. Nếu cần nhiều góc, gộp các góc nhất quán vào một bảng ảnh địa điểm rõ ràng. Kiểm tra ngân sách tham chiếu từng cảnh: ảnh nhân vật + ảnh địa điểm + ảnh phong cách. Nếu vượt giới hạn, thiết kế lại shot hoặc bảng ảnh; không âm thầm bỏ ảnh địa điểm. Không dùng style_refs làm nơi chứa nhà/đồ vật để gửi nhầm vào mọi cảnh.

## 3. Viết prompt từ mô tả chuẩn

Prompt ảnh = góc máy và hành động của shot + mô tả địa điểm chuẩn + trạng thái hiện tại + chi tiết riêng thật sự có mặt. Prompt clip lặp lại các đặc điểm cần giữ và chỉ mô tả chuyển động được phép: nhà không đổi mái/cửa, hàng rào không dịch vị trí, người không đổi đồ, vật không tự xuất hiện/biến mất. Negative chỉ là bổ sung, không thay thế ảnh tham chiếu.

Chỉ gửi và mô tả nhân vật có mặt trong shot. Shot cận tay đang làm việc vẫn phải gắn đúng actor để tool gửi ảnh mẫu. Không dồn mô tả cả dàn nhân vật hoặc mọi set vào từng prompt.

## 4. Phân biệt giữ thiết kế và nối chuyển động

Hai shot cắt góc vẫn dùng chung thiết kế địa điểm và trạng thái, nhưng có ảnh mở riêng. Chỉ shot continuous mới nối từ khung cuối clip trước. Với storyboard đã căn đúng kịch bản, dùng continuity=auto và link đúng từng shot. Không bật all để chữa đổi kiến trúc; không tắt off cho toàn bộ dự án chỉ vì mỗi shot có prompt riêng.

Nếu không có storyboard căn đúng, auto của tool suy từ bg_id: cùng mã không chứng minh cùng nơi/thời gian, đặc biệt khi dùng mã catalog thay thế. Phải kiểm tra từng liên kết trước khi chạy; nếu cần nối chọn lọc mà dữ liệu/tool không biểu đạt được, ghi rõ hạn chế và báo lỗi tool, không tự sửa code hoặc hợp đồng. Dùng off có ghi lý do khi các shot đều độc lập; vẫn bắt buộc tham chiếu chung.

Tool hiện không tự gửi khung cuối clip trước vào bước tạo ảnh của các shot cắt góc. Không giả định nó đã làm. Khi cần đối chiếu hướng nhìn/bố cục, người vận hành kiểm ảnh mở mới với khung cuối cũ. Bước clip gửi khung cuối cho liên kết continuous; ngoài ra dùng ảnh mở, ảnh nhân vật và ảnh địa điểm/đồ vật đã gán trong bộ mẫu khóa, cùng mô tả chuẩn. Panel ảnh địa điểm cũ cũng gửi ảnh vào cả hai bước.

## 5. Chạy thử trước khi tạo hàng loạt

Sau khi duyệt kịch bản, nhân vật và bộ mẫu, dùng ô **Cảnh chạy thử** (số 1-based) và **Thử ảnh / Thử clip các cảnh đã chọn** trong app; tối đa 10 cảnh mỗi lần. CLI tương đương --only (chỉ số 0-based) --images-only hoặc --clips-only. Chọn nhóm 3–5 shot đại diện: một toàn cảnh, một góc đảo, một cận người/đồ vật, một cảnh quay lại địa điểm hoặc sau biến đổi trạng thái. So các ảnh với cùng ảnh chuẩn, sửa prompt/ánh xạ tham chiếu nếu lệch. Sau đó dùng --clips-only cho nhóm này, kiểm đầu–giữa–cuối từng clip và chỗ cắt.

Chỉ tạo phần còn lại khi nhóm thử đạt và ghi kết quả vào continuity.md (file tham chiếu, phiên bản, số cảnh, người kiểm tra, lỗi còn lại). Duyệt nhóm thử là kiểm tra thủ công bắt buộc của quy trình, tách biệt với cổng duyệt bộ mẫu đã có trong app. Không dùng storyvid.auto đi thẳng tới hàng loạt trước khi kiểm nhóm thử; auto hiện chưa thực hiện bước kiểm này.

Tiếp tục theo lô nhỏ (tối đa 10 cảnh), kiểm từng lô trước lô sau. Kiểm tra cả các cảnh xa nhau cùng địa điểm, không chỉ hai cảnh liền nhau. Lệch kiến trúc/nhân vật/đồ vật quan trọng thì dừng lô, sửa nguyên nhân tham chiếu hoặc prompt rồi tạo lại phần bị ảnh hưởng.

## 6. Thay đổi và kiểm định cuối

Không ghi đè ảnh chuẩn âm thầm. Khi thay mẫu hoặc đổi trạng thái chuẩn, ghi phiên bản, liệt kê tất cả cảnh dùng nó và đánh dấu cần tạo lại; giữ bản clip cũ cho đến khi bản mới kiểm đạt. Nếu tạo lại clip có shot continuous phía sau, kiểm/tạo lại toàn bộ chuỗi phụ thuộc tới điểm cắt độc lập. App lưu dấu vết đầu vào và nội dung đầu ra ở `refs/generated.json`. Đổi ảnh/mô tả/gán cảnh/prompt làm mất duyệt bộ mẫu; các ảnh/clip không còn khớp được liệt kê là cần tạo lại. Lần chạy ảnh/clip tiếp theo tự tạo lại kết quả cũ không khớp. Clip từ ảnh mở cũ bị chặn. Chuỗi continuous phụ thuộc clip trước cũng bị đánh dấu cũ. File tạo trước khi có dấu vết được coi là chưa kiểm chứng, không tự gán đạt. Không tự duyệt bộ mẫu thay người; chỉ test dùng dữ liệu duyệt giả trong dự án tạm.

Trước bàn giao, xem đầu–giữa–cuối mỗi clip; ghép bảng so các góc cùng địa điểm và các lần quay lại. Sai hình khối, mặt, đồ, thời tiết hoặc trạng thái trọng yếu là major; người kiểm định có quyền ghi review.json theo phân vai dự án. Codex ghi nhận trong continuity.md và báo Claude, không sửa review.json. Chỉ đạt kiểm tra schema không có nghĩa hình đã nhất quán.

## Mẫu output/<id>/continuity.md

Sao chép cấu trúc này, điền giá trị thực trước khi chạy. Đây là tài liệu vận hành Markdown, không phải schema mới.

- Nguồn kịch bản; phong cách đã chọn; tập/series.
- Danh sách chuẩn: ID địa điểm/nhân vật/đồ vật; mô tả bất biến; đường dẫn ảnh; SHA-256; phiên bản; nguồn; trạng thái đã chốt hay còn nháp.
- Sơ đồ địa điểm và trục máy quay; các trạng thái theo thời gian truyện.

| Cảnh (1-based) | Set/phiên bản | Thời điểm/trạng thái đầu → cuối | Actor/vật | Ảnh gửi, tổng số | Kiểu nối/phụ thuộc | Kết quả ảnh/clip |
|---|---|---|---|---|---|---|

- Nhóm chạy thử: số cảnh; kết quả so với chuẩn; người kiểm; lỗi và lần chạy lại.
- Các lô còn lại: phạm vi; kiểm đầu/giữa/cuối; kiểm quay lại địa điểm.
- Thay đổi chuẩn: phiên bản cũ → mới; cảnh bị ảnh hưởng; trạng thái tạo lại.
- Bàn giao: mục chưa đạt và giới hạn tool còn tồn tại.

## Thao tác trong app

1. Duyệt kịch bản; tạo và duyệt ảnh nhân vật.
2. Ở tab **4. Hình Muse**, thêm mẫu nhà/địa điểm và đồ vật trong **Khóa hình ảnh**. Tải một ảnh hoặc bảng nhiều góc nhất quán; ghi mô tả đặc điểm chuẩn và số các cảnh dùng mẫu.
3. Bấm **Lưu bộ mẫu** rồi **Duyệt bộ mẫu**, xác nhận đã xem ảnh và rà soát cách gán cảnh. Dự án không cần mẫu địa điểm/đồ vật vẫn cần xác nhận bộ mẫu rỗng. Đổi ảnh cùng kích thước file cũng mất duyệt vì app băm nội dung ảnh.
4. Dùng **Cảnh chạy thử** → thử ảnh → xem → thử clip → xem đầu/giữa/cuối. Khi nhóm thử đạt mới tiếp tục ảnh/clip hoặc chạy tự động.
5. Sửa mẫu/prompt thì lưu và duyệt lại. App báo các cảnh cũ hoặc chưa kiểm chứng; dữ liệu video hiện có không bị xóa khi cập nhật ứng dụng.

Không có AI kiểm hình tự động trong thay đổi này. Cổng mới đảm bảo bộ tham chiếu đã được người duyệt và được truyền đúng, không cam kết Muse luôn vẽ đúng.
