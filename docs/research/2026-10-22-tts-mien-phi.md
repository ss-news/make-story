# TTS miễn phí trên GitHub (22/10/2026)

Code của repo thường là MIT hoặc Apache, nhưng **file model có thể có giấy phép khác**. Quyền dùng giọng đọc cho kênh kiếm tiền phụ thuộc vào giấy phép của model. Giấy phép dưới đây lấy từ trang Hugging Face của từng model.

## Dùng được cho kênh kiếm tiền

| Repo | Sao | Tiếng Anh | Tiếng Việt | Chạy trên Mac | Nhân bản giọng | Ghi chú |
|---|---|---|---|---|---|---|
| [hexgrad/kokoro](https://github.com/hexgrad/kokoro) | — | Có | Không | Có (CPU/MPS) | Không | 82M, nhẹ, giọng sạch, ít cảm xúc |
| [resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox) | 27k | Có | Không | Có (MPS/CPU) | Có | Có nút chỉnh độ cường điệu cảm xúc; có watermark ẩn |
| [pnnbao97/VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS) | 2,9k | Yếu | **Có, chuyên tiếng Việt** | Có (CPU/ONNX) | Có | Dùng bản v3 Turbo (v4 không mở). Có thẻ cảm xúc như `[cười]` (thử nghiệm) |
| [OpenBMB/VoxCPM](https://github.com/OpenBMB/VoxCPM) | 40k | Có | **Có** | Có (MPS), có thể chậm | Có | 2B, chỉnh được phong cách giọng, 30 ngôn ngữ |
| [supertone-oss-archive/supertonic](https://github.com/supertone-oss-archive/supertonic) | 14k | Có | **Có** | Có (ONNX), rất nhanh | Không | Giấy phép OpenRAIL-M (có điều khoản cấm dùng sai mục đích). Repo đã ngừng cập nhật |
| [kyutai-labs/pocket-tts](https://github.com/kyutai-labs/pocket-tts) | 10k | Có | Không | Có, ~6× thời gian thực trên M4 | Có | CC-BY-4.0: phải ghi công Kyutai |
| [RVC-Boss/GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) | 63k | Có | Không | Có (MPS/CPU) | Có, 5 giây mẫu | Tốt nhất khi luyện thêm 1 phút giọng mẫu |
| [KittenML/KittenTTS](https://github.com/KittenML/KittenTTS) bản 0.8 | 16k | Có | Không | Có (MLX) | Không | 15–80M, chạy CPU. Bản kitten-tts-2 dùng giấy phép khác |
| [QwenAudio/CosyVoice](https://github.com/QwenAudio/CosyVoice) | 24k | Có | Không | Chưa rõ | Có | Điều khiển cảm xúc bằng câu lệnh |
| [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) | 14k | Có | Không | Chưa rõ (tài liệu chỉ nói GPU NVIDIA) | Có, 3 giây | Tự mô tả giọng bằng chữ |
| [nari-labs/dia](https://github.com/nari-labs/dia) | 19k | Có | Không | **Không** (cần GPU NVIDIA) | Có | Hội thoại nhiều người, có `[laughter]` |
| [myshell-ai/OpenVoice](https://github.com/myshell-ai/OpenVoice) | 38k | Có | Không | Chưa rõ | Có | Chuyển giọng lên một giọng gốc |

## Chưa rõ, cần đọc kỹ giấy phép

| Repo | Vấn đề |
|---|---|
| [rhasspy/piper](https://github.com/rhasspy/piper) / [piper1-gpl](https://github.com/OHF-Voice/piper1-gpl) | Mỗi giọng một giấy phép. Giọng Việt `vais1000` dùng dữ liệu CC-BY-4.0 (dùng được, phải ghi công); **tránh `vivos`** (phi thương mại). Giọng hơi máy |
| [index-tts/index-tts](https://github.com/index-tts/index-tts) | Giấy phép riêng của bilibili, cho thương mại có điều kiện. Điều khiển cảm xúc rất tốt |
| KittenTTS bản 2 | Cho thương mại dưới $1M doanh thu/năm, phải đăng ký với Stellon Labs |
| [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio) | App gói nhiều engine. Engine mặc định (OmniVoice) là phi thương mại |

## Không dùng cho kênh kiếm tiền (model phi thương mại)

[F5-TTS](https://github.com/SWivid/F5-TTS), [OmniVoice](https://github.com/k2-fsa/OmniVoice), [Spark-TTS](https://github.com/SparkAudio/Spark-TTS), [fish-speech](https://github.com/fishaudio/fish-speech), [ChatTTS](https://github.com/2noise/ChatTTS), [Coqui XTTS v2](https://github.com/coqui-ai/TTS). Code là MIT hay Apache nhưng model cấm dùng thương mại.

## Gợi ý cho `storyvid`

- **Kênh tiếng Anh:** Kokoro (nhẹ, nhanh, làm giọng người dẫn chuyện) + Chatterbox (giọng nhân vật có cảm xúc, nhân bản giọng). Cả hai đều MIT/Apache và chạy được trên Mac.
- **Kênh tiếng Việt:** VieNeu-TTS v3 Turbo. Muốn nhiều ngôn ngữ trong một model thì thử VoxCPM2 hoặc Supertonic.
- Cần nghe thử trước khi chọn. Tốc độ trên Mac của phần lớn repo chưa được kiểm chứng.

## Nguồn giấy phép model

Kokoro https://huggingface.co/hexgrad/Kokoro-82M · Chatterbox https://huggingface.co/ResembleAI/chatterbox · VieNeu https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo · VoxCPM2 https://huggingface.co/openbmb/VoxCPM2 · Supertonic https://huggingface.co/Supertone/supertonic-3 · Pocket-TTS https://huggingface.co/api/models/kyutai/pocket-tts · GPT-SoVITS https://huggingface.co/lj1995/GPT-SoVITS · KittenTTS https://huggingface.co/KittenML/kitten-tts-mini-0.8 · CosyVoice https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512 · Qwen3-TTS https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base · Dia https://huggingface.co/nari-labs/Dia-1.6B · OpenVoice https://huggingface.co/myshell-ai/OpenVoiceV2 · Piper vi https://huggingface.co/rhasspy/piper-voices/raw/main/vi/vi_VN/vais1000/medium/MODEL_CARD · F5 https://huggingface.co/SWivid/F5-TTS · Spark https://huggingface.co/SparkAudio/Spark-TTS-0.5B · Fish https://huggingface.co/fishaudio/s2-pro · ChatTTS https://huggingface.co/2Noise/ChatTTS · XTTS https://huggingface.co/coqui/XTTS-v2
