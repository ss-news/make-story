# Các cách tối ưu video ngoài thumbnail và mở đầu

Ngày 28/10/2026. Viết tiếp sau `2026-10-28-ma-lon-analytics.md` (Ma Lon: CTR 1,1%, xem 43 giây, bị đề xuất cạnh Mr Bean). Research cũ ở `2026-10-22-san-xuat-va-tang-truong.md` đã có checklist đăng, cách đọc Analytics, chính sách nội dung AI; file này chỉ thêm phần mới.

Nhãn: **[Chính thức]** nguồn YouTube hoặc báo công nghệ dẫn lời YouTube; **[Blog]** blog hoặc công cụ bên thứ ba, nhiều bên bán dịch vụ; **[Ý kiến]** nhận định của mình.

## 1. YouTube thử video mới như thế nào

- Mỗi video mới được thử với một nhóm người xem nhỏ; 24–48 giờ đầu là lúc hệ thống xem CTR và cách người ta xem. Các nguồn không thống nhất con số chính xác. [Blog] https://subscribr.ai/youtube-strategy/youtube-algorithm-new-channels
- Người xem bấm vào vì tưởng là thứ khác sẽ kéo điểm hài lòng xuống, và YouTube ngừng đẩy. CTR thấp hơn một chút từ đúng người xem tốt hơn CTR cao từ người bỏ đi ngay. [Blog, cùng nguồn]
- Ngưỡng tham khảo (không chính thức): CTR dưới 4% sau 500 lượt hiển thị là lỗi thumbnail; CTR trên 10% nhưng giữ chân kém là lỗi mở đầu. [Blog] https://humbleandbrag.com/blog/new-youtube-channel-average-views

**Áp vào Ma Lon** [Ý kiến]: kênh chưa có lịch sử nên YouTube đoán khán giả theo hình ảnh. Hình que mắt tròn, màu phẳng → nhóm hoạt hình thiếu nhi. Mọi thứ trong khung hình (thumbnail, 10 giây đầu) phải nói "truyện ma cho người lớn" để YouTube thử đúng nhóm ngay lần đầu.

## 2. Thử nhiều thumbnail và tiêu đề (Test & Compare)

- Có trong YouTube Studio cho kênh đã bật **Tính năng nâng cao** (xác minh số điện thoại và giấy tờ). Nguồn 2026 không thống nhất có cần YPP không. Kiểm tra ở Studio > Cài đặt > Kênh > Điều kiện sử dụng tính năng. [Blog] https://1of10.com/blog/how-to-ab-test-youtube-thumbnails/
- Không dùng được cho video riêng tư, video dành cho trẻ em hay giới hạn độ tuổi. Ảnh phải từ 720p. Chọn thắng theo **tỷ lệ thời gian xem**, không theo CTR. [Blog, cùng nguồn] https://www.lindseygamble.com/blog/youtube-rolls-out-highly-anticipated-test-compare-feature-to-all-creators

**Việc làm** [Ý kiến]: mỗi video chuẩn bị 3 thumbnail khác hẳn nhau (chủ thể đáng sợ cận cảnh / nhân vật hoảng sợ / chữ lớn), chạy thử ngay khi đăng. Thử lại cho Ma Lon ngay bây giờ.

## 3. Thêm bản lồng tiếng (multi-language audio)

- Từ 9/2025 mọi kênh đều tải được nhiều bản âm thanh cho một video. Theo YouTube, kênh dùng tính năng này có trung bình hơn 25% thời gian xem đến từ ngôn ngữ phụ. [Chính thức, TechCrunch dẫn YouTube] https://techcrunch.com/2025/09/10/youtubes-multi-language-audio-feature-for-dubbing-videos-rolls-out-to-all-creators/
- Với kênh nhỏ, một video lồng tiếng không tạo khác biệt lớn; lợi ích đến khi làm đều. [Blog, bên bán dịch vụ] https://anyspeech.io/blog/how-to-dub-a-youtube-video

**Áp vào dự án** [Ý kiến]: đây là việc rẻ nhất với tool này. `output/ma_lon/story-vi.txt` đã có bản tiếng Việt; chỉ cần dựng thêm `narration.wav` tiếng Việt cùng mốc thời gian rồi tải lên làm bản âm thanh phụ. Hình không có chữ cứng ngoài phụ đề, nên dùng chung được. Người Việt trong nước và Việt kiều là nhóm dễ tìm thấy truyện ma Việt nhất.

## 4. Thị trường tiếng Việt

- Truyện ma tiếng Việt có kênh lớn, nhưng gần như là đọc truyện, không phải hoạt hình: Chuyện Ma Vũ Mập khoảng 634 nghìn người đăng ký, Nam Kể Chuyện Ma khoảng 123 nghìn. Không tìm thấy kênh truyện ma **hoạt hình** tiếng Việt nổi bật. [Blog, số liệu vidIQ/SocialCounts, có thể cũ] https://vidiq.com/youtube-stats/channel/UC9cTTLH7G6YVpjvDdb0O6Sg · https://socialcounts.org/youtube-live-subscriber-count/UC6jt82q8H5ottcWhFlQA_PA
- Kênh hoạt hình kinh dị theo vùng có thể rất lớn: Horror Animation Hindi TV khoảng 922 nghìn người đăng ký (7/2026); CJ Horror Toons lượt xem trung vị cao hơn nhiều lần số người đăng ký. Điểm chung: gắn chuyện ma vào đời sống thường ngày địa phương, theo một khuôn cố định. [Blog] https://vidiq.com/youtube-stats/channel/UCVfpn2-KaTlldC11UT49PFw · https://outlierkit.com/channel/cjhorrortoons

**Lựa chọn** [Ý kiến]: (a) giữ kênh tiếng Anh, thêm audio tiếng Việt (mục 3); (b) mở kênh tiếng Việt riêng, nơi có khoảng trống cho hoạt hình truyện ma. Cách (a) không tốn thêm kênh nên làm trước; nếu bản audio tiếng Việt chiếm phần lớn thời gian xem thì cân nhắc (b).

## 5. Shorts

- Nghiên cứu gần 800 nghìn video (Metricool, 2026): kênh không đăng Short trung bình 4.364 view mỗi video dài; kênh đăng khoảng 5 Short mỗi tháng đạt 8.789. Đây là tương quan, chưa chứng minh Short gây ra. [Blog] https://metricool.com/youtube-trends/
- Shorts feed chiếm 61% lượt xem trong mẫu. [Blog, cùng nguồn]
- Short Ma Lon có 0 lượt xem trong 48 giờ đầu theo trang tổng quan kênh: cần kiểm tra lại trạng thái (công khai chưa).

**Việc làm** [Ý kiến]: mỗi video dài cắt 3–5 Short (không chỉ 1), đăng rải trong tuần, gắn Related video về bản dài. Short phải đầy khung dọc (đã ghi trong luật dự án).

## 6. Nhịp hình trong video

- Lời khuyên chung: trong phần mở đầu cứ 8–12 giây có một thay đổi hình (cắt cảnh, chuyển camera, đổi âm thanh). [Blog] https://outlierkit.com/resources/youtube-hooks-and-retention/
- Ma Lon có vài cảnh giữ một hình khoảng 17 giây (review.json đã ghi).

**Việc làm** [Ý kiến]: trong 60 giây đầu, mỗi cảnh không quá 8 giây; cả video không quá 12 giây. Dùng `camera` và đổi tư thế/biểu cảm giữa các câu thay vì giữ nguyên.

## 7. Kéo khán giả đầu tiên

- r/horror có thread **Self Promo Sunday** mỗi tuần cho phép đăng link kênh; ngoài thread đó Reddit rất ghét tự quảng cáo, phải đọc luật từng subreddit. [Blog/cộng đồng] https://redlib.groet-infra.nl/r/horror/comments/1swbeia/weekly_thread_self_promo_sunday/
- Chọn video tốt nhất làm video giới thiệu kênh; hợp tác với kênh cùng ngách. [Blog/cộng đồng] https://redlib.groet-infra.nl/r/creepypastachannel/comments/10g1e4i/starting_a_creepypasta_channel_part_eight_getting

**Áp vào dự án** [Ý kiến]: vài chục người xem đúng ngách trong 24 giờ đầu (thích truyện ma, xem hết) giúp YouTube biết thử video với ai. Nơi phù hợp: r/horror (Self Promo Sunday), nhóm Facebook truyện ma Việt (cho bản tiếng Việt), cộng đồng người Việt ở nước ngoài. Không mua view, không nhờ người không quan tâm bấm vào: kéo nhầm người còn hại hơn.

## 8. Việc cho tool `storyvid`

| Ưu tiên | Việc | Lý do |
|---|---|---|
| 1 | Xuất **thumbnail** (2–3 phương án) từ nền + nhân vật + chữ, tông tối | Ma Lon không có thumbnail riêng |
| 2 | Dựng **bản âm thanh thứ hai** (tiếng Việt) cùng mốc thời gian với bản tiếng Anh | Multi-language audio, rẻ |
| 3 | Xuất **SRT** cùng video | Hiện chưa có; 91% lượt xem không phụ đề |
| 4 | Cắt **nhiều Short** từ một `scenes.json` | Hiện mỗi truyện chỉ một Short |
| 5 | `storyvid.check` cảnh báo cảnh dài quá 8 giây trong phút đầu, quá 12 giây sau đó | Nhịp hình |

Các mục này đụng code `storyvid/` nên cần người dùng duyệt trước khi làm.

## Còn chưa xác minh

- Test & Compare có cần YPP không: kiểm tra trực tiếp trong Studio của kênh.
- Short Ma Lon 0 view: chưa rõ do riêng tư hay do không được đẩy.
- Số liệu kênh đối thủ là ước tính của bên thứ ba.
