# Chuyển cảnh chưa mượt: nguyên nhân và cách sửa (2026-11-04)

Đo trên video thử `output/thach_thon` (21 cảnh, 3:01, ảnh và clip Muse, dựng bằng `--visuals`). Nguyên tắc dựng phim ở mục 3 là kiến thức nghề phổ biến, chưa đối chiếu nguồn web (lượt tìm web bị bỏ qua).

## 1. Đo được gì

| Cảnh | Nối khung cuối | Lời | Thấy gì ở chỗ cắt |
|---|---|---|---|
| 2 → 3 | không | 10,5 s → 7,1 s | Cận mặt cụ già ban đêm cắt thẳng sang núi vàng buổi sớm. Đổi cả thời gian lẫn nơi chốn mà không có chuyển tiếp. |
| 6 → 7 | có | 8,6 s → 7,5 s | Muse bỏ qua yêu cầu nối, cắt cứng. Câu đầu cảnh 7 “Nó múa may xiêu vẹo” nói về nhóc, nhưng hình là hai cụ và trai tráng. |
| 11 → 12 | có | 5,6 s → 10,3 s | Clip 12 bắt đầu bằng thầy dạy và lũ trẻ (khung cuối cảnh 11), khoảng 2 giây sau mới trôi sang gốc liễu. Trong lúc đó lời đã đọc “Đầu thôn có một gốc liễu già…”. |
| 13 → 14 | có | 9,5 s → 8,8 s | Muse bỏ qua yêu cầu nối, cắt cứng giữa hai nơi khác nhau (bữa ăn → sân tộc trưởng). Cắt cứng ở đây lại hợp lý. |
| 10, 11 | có | 5,0 s, 5,6 s | Clip 10 giây bị cắt ngang ở giây thứ 5, giữa lúc nhân vật đang chạy. |
| 21 | không | 16,5 s | Clip chỉ đủ 14 giây, 3 giây cuối đứng hình. |

12/21 cảnh bị nối khung cuối. Không có cảnh nào dùng hòa hình hay tối dần; mọi chỗ nối đều là cắt cứng, đúng ngay lúc đổi đoạn lời.

## 2. Nguyên nhân (ba lớp)

**a. Tool nối khung cuối theo mã nền.** Chế độ “Tự động” (`visuals.linked`) nối mọi cặp cảnh liền nhau có cùng `bg_id`. Nhưng `bg_id` chỉ là mã gần đúng của nơi chốn: bãi tập và gốc liễu đầu làng cùng là `village_path_day`. Hai cảnh cùng mã vẫn có thể là hai cú máy khác hẳn nhau (cận nhóc con → cảnh rộng các cụ). Kết quả:
- Muse làm theo: vài giây đầu clip là hình của cảnh trước biến dần sang cảnh mới, trong lúc lời đã nói chuyện mới (11 → 12).
- Muse bỏ qua: vẫn là cắt cứng, chỉ tốn thêm điều kiện chạy tuần tự (6 → 7, 13 → 14).

Trong dựng phim, hai cú máy liền nhau vốn cắt cứng. Chỉ nên nối liền khi cảnh sau là **cùng một hành động đang tiếp diễn** trong cùng khung hình.

**b. Kịch bản chia cảnh theo đoạn lời, chưa theo ý hình.** Bản đầu do Claude viết. Mỗi cảnh là một đoạn lời, nhưng có chỗ câu đầu cảnh còn nói về chủ thể của cảnh trước (cảnh 7). Thêm nữa, các cảnh rất ngắn (5 giây) và rất dài (16,5 giây) đều làm clip bị cắt ngang hoặc đứng hình. Nhịp cảnh không đều cũng khiến chuyển cảnh giật.

**c. Phần dựng chỉ có cắt cứng.** `render_clips` chuyển hình đúng lúc đổi đoạn lời, không có hòa hình khi đổi thời gian hay nơi chốn. Không có khoảng thở giữa hai đoạn lời, cũng không cho hình đi trước lời.

## 3. Nguyên tắc dựng dùng làm chuẩn

1. **Hình theo lời:** khi câu nói về ai, cái gì, thì hình đang có đúng người, vật đó. Chỗ cắt rơi vào đầu câu mà chủ thể đổi.
2. **Mỗi cảnh một ý hình**, dài vừa một clip, khoảng 6–10 giây. Lời dài hơn thì tách cảnh; lời quá ngắn thì gộp cảnh hoặc thêm khoảng lặng.
3. **Cỡ cảnh tiến dần trong cùng một nơi:** rộng (thiết lập) → trung → cận. Hai cảnh liền nhau không cùng cỡ cảnh, cùng góc máy, vì cắt như vậy trông như hình bị giật.
4. **Cắt cứng khi cùng nơi, cùng lúc. Hòa hình (0,5–1 giây) hoặc tối dần khi đổi thời gian hay đổi nơi** (đêm → sáng, làng → rừng sâu, hiện tại → hồi tưởng).
5. **J-cut / L-cut:** hình của cảnh mới vào trước lời khoảng 0,3–0,5 giây, hoặc tiếng cảnh cũ kéo dài sang hình mới. Chỗ cắt không trùng khít đúng điểm bắt đầu câu nên đỡ giật.
6. **Không cắt giữa động tác:** clip nên kết ở một khung lặng, đã dừng chuyển động. Chuyển động máy của hai cảnh liền nhau không ngược chiều (zoom vào rồi zoom ra ngay).

## 4. Đề xuất, theo thứ tự nên làm

| # | Sửa gì | Nằm ở | Công | Đổi chuẩn? |
|---|---|---|---|---|
| 1 | Bỏ nối khung cuối mặc định: mặc định mỗi cảnh bắt đầu từ ảnh của chính nó (cắt cứng). Giữ “Nối tất cả” làm tùy chọn, hoặc nối khi cảnh sau có cùng diễn viên, cùng cỡ cảnh với cảnh trước. | `storyvid/visuals.py` `linked`, ô “Nối khung cuối” | nhỏ | không |
| 2 | Hòa hình 0,6 giây khi đổi `_day`/`_night` hoặc đổi nơi chốn (đổi `bg_id` sang mã khác), cắt cứng khi cùng mã. Hình vào trước lời 0,3 giây, nghỉ 0,3 giây giữa hai đoạn lời. | `storyvid/render_clips.py` | vừa | không |
| 3 | Thêm luật chia cảnh cho AI viết kịch bản và vào checklist: câu đầu mỗi cảnh nói đúng chủ thể của hình; mỗi cảnh 6–10 giây (khoảng 18–30 từ tiếng Việt); cỡ cảnh tiến dần; đổi nơi thì đổi `bg_id`. Đánh giá kịch bản có thêm tiêu chí “chuyển cảnh”. | `storyvid/script.py`, `script_review.py`, `docs/review-checklist.md` | nhỏ | không |
| 4 | Prompt clip yêu cầu kết bằng khung lặng, chuyển động máy không ngược chiều cảnh trước; cảnh quá ngắn thì không cắt clip giữa chừng mà chọn đoạn clip có chuyển động trọn vẹn. | `storyvid/visuals.py` (SYSTEM, clip), `render_clips.py` | vừa | không |
| 5 | Về sau: một đoạn lời dài chia thành 2 cú máy (shot list trong cảnh). | `storyvid/contract.py` | lớn | có |

Đề xuất 1–3 giải quyết hầu hết các chỗ giật đã đo, mà không cần tạo lại ảnh. Kiểm chứng: dựng lại Thạch Thôn từ clip hiện có (bỏ nối chỉ có tác dụng với clip làm mới), so lại các chỗ cắt 2→3, 7→8, 11→12, 20→21.
