# Làm video YouTube: chính sách, bản quyền, sản xuất và tăng trưởng

Ngày 22/10/2026. Phần tiếp theo của research ở session "Công cụ video hoạt hình tiết kiệm chi phí" (đã có: chọn tool, thị trường, đối thủ, kinh dị dân gian VN, độ dài video, Shorts, lập kênh và thuế).

Nhãn độ tin cậy: **[Chính thức]** trang của YouTube/Microsoft; **[Blog]** blog bên thứ ba, chưa kiểm chứng từ nguồn gốc; **[Ý kiến]** nhận định, không có nguồn.

## 1. Chính sách kiếm tiền với nội dung AI

- Ngày 15/7/2025, chính sách "repetitious content" đổi tên thành **"inauthentic content"**. YouTube nói đây là làm rõ luật cũ. [Chính thức] https://support.google.com/youtube/answer/1311392
- **Bị từ chối kiếm tiền:** nội dung sản xuất hàng loạt, làm theo khuôn mẫu, các video gần như giống nhau, ít giá trị tự sự hay bình luận.
- **Được chấp nhận:** intro/outro lặp lại; series mà mỗi tập có cốt truyện riêng; **dùng AI để hiện thực hóa nhân vật và câu chuyện do chính bạn sáng tạo** (đúng trường hợp kênh này).
- Không có điều nào cấm giọng TTS. Rủi ro là tổ hợp: giọng đều đều + hình lặp + kịch bản chung chung. YouTube được cho là xét **cả kênh**, không xét từng video. [Blog] https://air.io/news-air/how-youtube-treats-ai-in-2026-new-update
- **Chưa xác minh, cần đọc YouTube blog gốc:** AIR viết ngày 10/8/2026 YouTube công bố thay đổi YPP có hiệu lực 1/2/2027, ngưỡng cho kênh mới tăng gấp đôi. Nếu đúng, kênh nào đạt ngưỡng trước 2/2027 sẽ có lợi. [Blog] https://air.io/en/monetization/youtube-monetization-policy-changes-2026-a-complete-dated-timeline

**Cách thể hiện "đóng góp gốc"** [Ý kiến]: kịch bản có giọng riêng, mỗi tập một cốt truyện và bối cảnh khác; có đoạn giải thích văn hóa (ma da là gì, vì sao làng kiêng…); nhân vật và nền có phong cách riêng nhất quán; không đăng dồn nhiều video na ná nhau.

**Nhãn "altered or synthetic content":** chỉ bắt buộc khi nội dung trông như thật (người thật, sự kiện thật, cảnh quang thực). Hoạt hình người que trên nền tranh **thường không cần**. Dùng AI viết kịch bản hay phụ đề cũng không cần khai. [Chính thức] https://support.google.com/youtube/answer/14328491

## 2. Bản quyền các thành phần trong tool

| Thành phần | Hiện tại | Rủi ro | Nên làm |
|---|---|---|---|
| Giọng đọc | edge-tts | Dùng dịch vụ Microsoft không qua gói Azure, **có thể vi phạm điều khoản**; có thể bị chặn bất cứ lúc nào [Chính thức, Microsoft Q&A] https://learn.microsoft.com/en-us/answers/questions/2088770/are-opensource-edge-tts-free-for-commercial-use | Đổi trước khi bật kiếm tiền |
| Ảnh nền | Flux schnell (fal) | Apache-2.0, thương mại được | Giữ. **Tránh Flux dev** (phi thương mại) |
| Ảnh nền | Codex/ChatGPT, Seedream | Chưa đọc được điều khoản gốc | Đọc điều khoản trước khi dùng cho kênh kiếm tiền |
| Nhân vật | Vẽ bằng code | Của bạn | — |
| Nhạc/SFX | chưa có | Nhạc miễn phí hay bị bên thứ ba claim Content ID nhầm | Lưu bằng chứng giấy phép, kiểm tra tab Bản quyền sau khi đăng |
| Truyện | dân gian VN | Bản kể dân gian dùng được, nên ghi nguồn. **Bản viết lại của một tác giả cụ thể** (Nguyễn Đổng Chi…) hay truyện ma trên sách/web hiện đại **vẫn có bản quyền** | Lấy motif dân gian làm hạt giống, tự viết lại cốt truyện và lời văn |

**Giọng đọc thay thế:**

| Lựa chọn | Giá / giấy phép |
|---|---|
| Azure AI Speech (chính thức, cùng giọng với edge-tts) | Gói F0 miễn phí 0,5 triệu ký tự/tháng (~8–10 video 15 phút) |
| Kokoro (chạy local) | Apache-2.0, thương mại được. Cần nghe thử chất giọng |
| ElevenLabs | Starter $6/tháng có giấy phép thương mại (30k ký tự), Creator $11 (121k). Gói Free **không** có giấy phép thương mại |
| F5-TTS, XTTS v2 | Phi thương mại, không dùng |

Đổi sang Azure là ít việc nhất: cùng tên giọng (`en-US-AndrewNeural`…), chỉ thay phần gọi API trong `storyvid/tts.py`.

**Nhạc:** YouTube Audio Library (miễn phí, chỉ dùng trên YouTube). Epidemic Sound khoảng $10–18/tháng; video đã đăng lúc còn thuê bao vẫn hợp lệ nếu kênh đã được whitelist.

## 3. Viết kịch bản để giữ người xem

- **10 giây đầu** chứng minh lời hứa của tiêu đề; bỏ chào hỏi và intro kênh. [Blog] https://outlierkit.com/resources/youtube-hooks-and-retention/
- **Re-hook mỗi 2–3 phút:** câu lửng gợi đoạn kế tiếp. Chỉ mở 1–2 "câu hỏi lớn" mỗi video và phải trả lời hết.
- Kênh faceless nên **đổi hình mỗi 5–10 giây** (đổi nền, đổi góc máy, nhân vật đổi tư thế). [Blog]
- Tốc độ đọc khoảng **140–150 từ/phút**, chừa khoảng lặng trước cảnh sợ. Video 15 phút ≈ 2.000–2.200 từ. [Ý kiến]
- Khung truyện [Ý kiến]: hook bằng khoảnh khắc đáng sợ nhất → bối cảnh ngắn, có điều lạ ngay → 3–4 nấc leo thang, mỗi nấc kết bằng câu lửng → cao trào → twist hoặc dư âm (điều kiêng kỵ của làng) → gợi ý video kế. Truyện dân gian Việt hợp với format **"luật của làng + người phá luật"**.
- Hệ thống đề xuất cân cả CTR, thời gian xem và mức hài lòng (khảo sát, like, xem tiếp hay rời YouTube). [Blog, trích YouTube Liaison] https://www.searchenginejournal.com/how-youtubes-recommendation-system-works-in-2025/538379/

## 4. Tiêu đề và thumbnail

- [Ý kiến] Một chủ thể rõ (bóng người, mặt ma che nửa, cổng làng), nền tối + một màu nhấn, chữ tối đa 3–4 từ, đọc được trên điện thoại. Tiêu đề tiếng Anh nên có "Vietnamese" / "folklore" để định vị ngách. Không nói dối trong tiêu đề.
- **Test & Compare** trong YouTube Studio: thử tối đa 3 thumbnail (và tiêu đề), chọn theo thời gian xem. Có thể chỉ mở cho kênh YPP, chỉ trên desktop. [Blog] https://www.tubefilter.com/2025/07/16/youtube-feature-test-and-compare-titles-thumbnails/
- Thumbnail có thể dựng từ chính ảnh nền + nhân vật của tool.

## 5. Checklist khi đăng

- [ ] **Chapters**: timestamp trong mô tả (tự nhập sẽ thay chapter tự động). [Chính thức] https://support.google.com/youtube/answer/57407
- [ ] **Tags**: vai trò nhỏ, chủ yếu cho từ dễ viết sai. Thêm tên ma có dấu và không dấu (ma da / "ma đa"). [Chính thức, cùng trang]
- [ ] **Mô tả**: 2 dòng đầu có từ khóa + hook; chapters; nguồn truyện dân gian; link playlist.
- [ ] **Playlist** theo series (ví dụ "Vietnamese Folklore", "Village Curses").
- [ ] **End screen** 5–20 giây cuối trỏ 1–2 video; tối đa 5 card.
- [ ] **Bình luận ghim**: một câu hỏi, hoặc giải thích truyền thuyết thật.
- [ ] **Phụ đề SRT** tải lên từ kịch bản (không dùng phụ đề tự động), thêm vài ngôn ngữ.
- [ ] **Auto-dubbing**: báo cáo 2/2026 là 27 ngôn ngữ; kiểm tra trong Studio > Ngôn ngữ xem kênh có quyền chưa. [Blog]
- [ ] Đăng đều 1–2 video dài/tuần cùng khung giờ; xem "Thời điểm người xem trên YouTube" trong Analytics. [Ý kiến]

## 6. Đọc Analytics

Theo thứ tự:
1. **Impressions + CTR**: có ai thấy, có ai bấm. Kênh mới ~3% chấp nhận được, 4–6% tốt. CTR giảm khi video được đẩy rộng là bình thường. [Blog]
2. **Đường retention**: chỗ tụt ở đầu = hook yếu; vách giữa video = đoạn chán.
3. **AVD %**: với video 15 phút, mục tiêu thực tế 35–45%. [Blog] https://research.stripo.email/youtube-benchmarks
4. **Người xem quay lại**, sub/video.

Đánh giá sau **8–12 video**, mỗi lần chỉ đổi **một** yếu tố (hook, độ dài, thumbnail). Kỳ vọng 6–12 tháng, 30–50 video mới thấy xu hướng. [Ý kiến]

## 7. Shorts

- Khi đăng Short, gắn **Related video** trỏ về video dài; đầu video dài phải trả lời ngay điều Short gợi ra. [Blog]
- 30–45 giây, cảnh đáng sợ nhất ở giây đầu, kết lửng. 3–5 Short/tuần cắt từ video dài.
- Đo lượt xem video dài đến từ Shorts, không chỉ đếm view Shorts.

## 8. Lỗi hay gặp của kênh faceless AI [Ý kiến]

Giọng TTS phẳng; hình tĩnh lặp lại; kịch bản chung chung hoặc dịch máy; đổi ngách liên tục; thumbnail không khớp nội dung; sai chi tiết văn hóa; đăng nhiều video dở thay vì ít video tốt.

## 9. Công cụ miễn phí

vidIQ free (~150 credit AI/tháng, giới hạn hằng ngày); TubeBuddy free (từ khóa hạn chế); YouTube Studio tab Nghiên cứu và gợi ý tìm kiếm của YouTube; Canva / Photopea cho thumbnail.

## 10. Việc cần làm cho tool `storyvid`

| Ưu tiên | Việc | Lý do |
|---|---|---|
| 1 | Thêm provider TTS **Azure** (và/hoặc Kokoro) bên cạnh edge-tts | Rủi ro điều khoản khi kiếm tiền |
| 2 | Xuất **SRT** và **chapters** (từ mốc thời gian từng cảnh) cùng video | Checklist đăng |
| 3 | Chế độ **Shorts 9:16** từ cùng `scenes.json` | Đã đề xuất từ research trước |
| 4 | Tạo **thumbnail** từ nền + nhân vật + chữ | Đỡ làm tay |
| 5 | Prompt kịch bản: hook 10 giây, re-hook mỗi 2–3 phút, đoạn giải thích văn hóa, ~145 từ/phút | Retention + "đóng góp gốc" |
| 6 | Lớp nhạc nền / SFX | Hiện chưa có |

## Còn chưa xác minh

- Thay đổi YPP hiệu lực 1/2/2027 (chỉ có nguồn AIR).
- Điều khoản thương mại của ảnh từ Codex/ChatGPT và Seedream.
- Test & Compare và auto-dubbing đã mở cho kênh chưa vào YPP chưa.
- Phân tích trực tiếp 10 video top của các kênh đối thủ (tiêu đề, thumbnail, độ dài): chưa làm.
