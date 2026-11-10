# Quy trình giữ nhất quán hình và clip

Áp dụng cho mọi dự án dùng Muse, kể cả các tập trong cùng series. Đây là quy trình agent/người vận hành phải làm; hiện tool chưa tự khóa bước tạo hàng loạt theo kiểm tra bối cảnh. Các cổng duyệt kịch bản và nhân vật hiện có vẫn bắt buộc. Không thêm trường vào scenes.json, visuals.json hay storyboard.json ngoài schema.

## 1. Khóa thiết kế trước khi viết prompt từng cảnh

Tạo output/<id>/continuity.md theo mẫu bên dưới. Nhân vật, địa điểm và đồ vật xuất hiện lại phải có mô tả chuẩn duy nhất, ảnh tham chiếu và phiên bản. Cùng series dùng lại đúng file ảnh đã chốt, không viết lại ngoại hình hoặc tạo lại ảnh mẫu mỗi tập. Địa điểm khác dùng mẫu khác dù cùng là nhà, sân hay rừng.

- Nhân vật: khuôn mặt, tuổi, vóc dáng, tóc, trang phục, phụ kiện; tay xuất hiện trong cận cảnh cũng phải xác định là tay của ai và có actor tương ứng.
- Địa điểm: hình khối nhà, vật liệu, độ dốc mái, cửa/cửa sổ, ống khói; vị trí nhà–chuồng–cổng–hàng rào–suối. Ghi hướng theo sơ đồ mặt bằng, không ghi trái/phải khung hình như một thuộc tính cố định của địa điểm.
- Đồ vật: kích thước, màu, vật liệu, dấu hỏng riêng và người cầm. Đồ vật quan trọng dùng ảnh chi tiết tham chiếu; không đăng ký ảnh nhân vật thành prop.
- Trạng thái: ngày/đêm, thời tiết, tuyết, mức hư hỏng/sửa chữa, trang phục ướt/bẩn, vị trí người và vật. Mỗi thay đổi phải có nguyên nhân trong truyện; khi quay lại địa điểm phải dùng đúng trạng thái tại thời điểm đó.

Ảnh mẫu địa điểm cần góc rộng thấy rõ bố cục và ít nhất một góc kiểm chứng mặt nhà. Chốt ảnh chuẩn trước khi sinh cảnh; không lấy một ảnh ngẫu nhiên chưa kiểm tra làm chuẩn. Ảnh chuẩn là thiết kế của địa điểm, không buộc mọi shot có cùng góc máy. Không dùng ảnh có người không liên quan làm chuẩn trang phục/nhân vật.

## 2. Lập bảng cảnh → tham chiếu và trạng thái

Trong continuity.md, mỗi cảnh ghi số 1-based, địa điểm/phiên bản, thời điểm, người xuất hiện, vật quan trọng, trạng thái đầu/cuối, kiểu nối và cảnh phụ thuộc. Đối chiếu với cảnh 0-based trong visuals.json và review.json để tránh sửa lệch một cảnh.

Dùng refs/places.json (storyvid.places/1) để gửi ảnh địa điểm vào bước tạo ảnh mở cảnh, kể cả địa điểm hư cấu do dự án thiết kế. Dùng danh sách scenes rõ ràng; không chỉ dựa từ khóa chung house/yard để gán nhầm địa điểm. sources ghi nguồn thực khi có, không tạo URL giả. Ảnh chuẩn phải nằm trong thư mục dự án.

Tool hiện chỉ lấy ảnh đầu tiên của mỗi địa điểm, tối đa 4 ảnh tham chiếu tổng cộng, tối đa 3 ảnh nhân vật. Nếu cần nhiều góc, gộp các góc nhất quán vào một bảng ảnh địa điểm rõ ràng. Kiểm tra ngân sách tham chiếu từng cảnh: ảnh nhân vật + ảnh địa điểm + ảnh phong cách. Nếu vượt giới hạn, thiết kế lại shot hoặc bảng ảnh; không âm thầm bỏ ảnh địa điểm. Không dùng style_refs làm nơi chứa nhà/đồ vật để gửi nhầm vào mọi cảnh.

## 3. Viết prompt từ mô tả chuẩn

Prompt ảnh = góc máy và hành động của shot + mô tả địa điểm chuẩn + trạng thái hiện tại + chi tiết riêng thật sự có mặt. Prompt clip lặp lại các đặc điểm cần giữ và chỉ mô tả chuyển động được phép: nhà không đổi mái/cửa, hàng rào không dịch vị trí, người không đổi đồ, vật không tự xuất hiện/biến mất. Negative chỉ là bổ sung, không thay thế ảnh tham chiếu.

Chỉ gửi và mô tả nhân vật có mặt trong shot. Shot cận tay đang làm việc vẫn phải gắn đúng actor để tool gửi ảnh mẫu. Không dồn mô tả cả dàn nhân vật hoặc mọi set vào từng prompt.

## 4. Phân biệt giữ thiết kế và nối chuyển động

Hai shot cắt góc vẫn dùng chung thiết kế địa điểm và trạng thái, nhưng có ảnh mở riêng. Chỉ shot continuous mới nối từ khung cuối clip trước. Với storyboard đã căn đúng kịch bản, dùng continuity=auto và link đúng từng shot. Không bật all để chữa đổi kiến trúc; không tắt off cho toàn bộ dự án chỉ vì mỗi shot có prompt riêng.

Nếu không có storyboard căn đúng, auto của tool suy từ bg_id: cùng mã không chứng minh cùng nơi/thời gian, đặc biệt khi dùng mã catalog thay thế. Phải kiểm tra từng liên kết trước khi chạy; nếu cần nối chọn lọc mà dữ liệu/tool không biểu đạt được, ghi rõ hạn chế và báo lỗi tool, không tự sửa code hoặc hợp đồng. Dùng off có ghi lý do khi các shot đều độc lập; vẫn bắt buộc tham chiếu chung.

Tool hiện không tự gửi khung cuối clip trước vào bước tạo ảnh của các shot cắt góc. Không giả định nó đã làm. Khi cần đối chiếu hướng nhìn/bố cục, người vận hành kiểm ảnh mở mới với khung cuối cũ. Bước clip có thể gửi khung cuối cho liên kết continuous; ngoài ra clip dùng ảnh mở và ảnh nhân vật, không tự nhận thêm toàn bộ ảnh địa điểm.

## 5. Chạy thử trước khi tạo hàng loạt

Sau các cổng duyệt hiện có, chỉ tạo ảnh cho nhóm 3–5 shot đại diện bằng --only (chỉ số 0-based) --images-only: một toàn cảnh, một góc đảo, một cận người/đồ vật, một cảnh quay lại địa điểm hoặc sau biến đổi trạng thái. So các ảnh với cùng ảnh chuẩn, sửa prompt/ánh xạ tham chiếu nếu lệch. Sau đó dùng --clips-only cho nhóm này, kiểm đầu–giữa–cuối từng clip và chỗ cắt.

Chỉ tạo phần còn lại khi nhóm thử đạt và ghi kết quả vào continuity.md (file tham chiếu, phiên bản, số cảnh, người kiểm tra, lỗi còn lại). Đây là kiểm tra thủ công bắt buộc của quy trình, chưa phải cổng tự động hoặc approved_* mới. Không dùng storyvid.auto đi thẳng tới hàng loạt trước khi kiểm nhóm thử; auto hiện chưa thực hiện bước kiểm này.

Tiếp tục theo lô nhỏ (tối đa 10 cảnh), kiểm từng lô trước lô sau. Kiểm tra cả các cảnh xa nhau cùng địa điểm, không chỉ hai cảnh liền nhau. Lệch kiến trúc/nhân vật/đồ vật quan trọng thì dừng lô, sửa nguyên nhân tham chiếu hoặc prompt rồi tạo lại phần bị ảnh hưởng.

## 6. Thay đổi và kiểm định cuối

Không ghi đè ảnh chuẩn âm thầm. Khi thay mẫu hoặc đổi trạng thái chuẩn, ghi phiên bản, liệt kê tất cả cảnh dùng nó và đánh dấu cần tạo lại; giữ bản clip cũ cho đến khi bản mới kiểm đạt. Nếu tạo lại clip có shot continuous phía sau, kiểm/tạo lại toàn bộ chuỗi phụ thuộc tới điểm cắt độc lập. Thay ảnh chuẩn không tự làm tool bỏ cache; phải chỉ rõ --only và --redo cho phần cần tạo lại.

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
