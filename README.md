# Sachitone Translator

Sachitone Translator là bot Discord dịch thuật AI theo ngữ cảnh và dịch vụ REST API siêu nhẹ viết bằng Python, sử dụng mô hình Google Gemini (`gemini-3.5-flash-lite`).

Khác với các công cụ dịch từ-qua-từ thông thường, Sachitone Translator được tinh chỉnh chuyên sâu cho văn hóa chat Discord: tự động hiểu ngôn ngữ nói, teencode tiếng Việt, từ lóng game, viết tắt, meme, emoji và lỗi chính tả, đồng thời giữ nguyên vẹn 100% cú pháp Discord (mentions, URLs, code blocks).

---

## Yêu cầu môi trường

- Python 3.11 trở lên
- Google Gemini API Key
- Discord Bot Token (đã bật **Message Content Intent**)

---

## Hướng dẫn cài đặt

### 1. Clone repository về máy

```bash
git clone https://github.com/your-org/sachitone-translator.git
cd sachitone-translator
```

2. Tạo môi trường ảo (Virtual Environment)

Trên Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Trên Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Cài đặt dependencies

```bash
pip install -e .
```

Cấu hình biến môi trường

Sao chép file cấu hình mẫu .env.example thành .env:

```bash
cp .env.example .env
```

Điền các thông tin vào .env:

```bash
DISCORD_TOKEN=your_discord_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
API_HOST=0.0.0.0
API_PORT=8000
BOT_PREFIX=!
LOG_LEVEL=INFO
MAX_TRANSLATION_LENGTH=2000
TRANSLATION_TIMEOUT=15
```

## Bảng giải thích cấu hình

| Tên biến                 | Mặc định                | Ý nghĩa                                              |
| ------------------------ | ----------------------- | ---------------------------------------------------- |
| `DISCORD_TOKEN`          | *(Bắt buộc cho bot)*    | Token của Discord Application Bot                    |
| `GEMINI_API_KEY`         | *(Bắt buộc)*            | API Key lấy từ Google AI Studio                      |
| `GEMINI_MODEL`           | `gemini-3.5-flash-lite` | Model Gemini được dùng                               |
| `API_HOST`               | `0.0.0.0`               | Địa chỉ IP lắng nghe của FastAPI                     |
| `API_PORT`               | `8000`                  | Cổng dịch vụ FastAPI                                 |
| `BOT_PREFIX`             | `!`                     | Prefix dự phòng cho bot                              |
| `LOG_LEVEL`              | `INFO`                  | Mức độ ghi log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `MAX_TRANSLATION_LENGTH` | `2000`                  | Số ký tự tối đa cho 1 lần dịch                       |
| `TRANSLATION_TIMEOUT`    | `15`                    | Thời gian chờ tối đa khi gọi AI (giây)               |

## Chạy ứng dụng

1. Kiểm tra cấu hình & kết nối trước khi chạy

Chạy script kiểm tra để xác thực API Key và dịch thử 1 câu mẫu:

```bash
python scripts/setup_commands.py
```

Nếu muốn sync nhanh Slash Command vào một Discord Server cụ thể để test ngay
(không phải chờ Discord đồng bộ global):

```bash
python scripts/setup_commands.py --guild <ID_SERVER_CUA_BAN>
```

2. Khởi chạy FastAPI Service

```bash
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Giao diện tài liệu API tương tác:

  - Swagger UI: http://localhost:8000/docs
  - ReDoc: http://localhost:8000/redoc

3. Khởi chạy Discord Bot

Mở một terminal khác và chạy:

```bash
python -m apps.bot.main
```

## Thiết lập Discord Bot trên Developer Portal

1.  Truy cập Discord Developer Portal.
2.  Tạo mới một ứng dụng (New Application) và thêm Bot.
3.  Ở mục Bot -> tìm đến Privileged Gateway Intents -> bật Message Content
    Intent.
4.  Ở mục OAuth2 -> URL Generator:
      - Chọn Scopes: bot, applications.commands
      - Chọn Bot Permissions:
          - Read Messages/View Channels
          - Send Messages
          - Read Message History
5.  Dán URL mời vừa tạo vào trình duyệt để thêm bot vào server Discord của bạn.

Danh sách lệnh Discord

| Lệnh                                  | Loại                 | Mô tả                                                                         |
| ------------------------------------- | -------------------- | ----------------------------------------------------------------------------- |
| `/translate <text> <target> [source]` | Slash Command        | Dịch văn bản sang ngôn ngữ đích (mặc định source là `auto`).                  |
| `Translate to English`                | Message Context Menu | Chuột phải vào bất kỳ tin nhắn nào -\> **Apps** -\> **Translate to English**. |
| `/ping`                               | Slash Command        | Kiểm tra độ trễ (latency) của bot tới Discord Gateway.                        |
| `/about`                              | Slash Command        | Xem thông tin phiên bản và trang web chính thức của dự án.                    |
| `/settings`                           | Slash Command        | Xem cấu hình runtime hiện tại của bot.                                        |

## REST API Endpoints

  - GET /: Trả về metadata và trạng thái online của service.
  - GET /health: Health check siêu nhẹ, trả về {"status": "healthy"} (không gọi
    Gemini để tránh tốn quota).
  - GET /api/v1/languages: Danh sách các ngôn ngữ được hỗ trợ phổ biến.
  - POST /api/v1/translate: Gửi yêu cầu dịch văn bản.

Ví dụ gọi API bằng cURL

Dịch Teencode tiếng Việt sang tiếng Anh:

```curl
curl -X POST "http://localhost:8000/api/v1/translate" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "hnay mik hok biet lam j",
       "source_language": "vi",
       "target_language": "en"
     }'
```

Kết quả trả về:

```json
{
  "success": true,
  "translation": "I don't know what to do today.",
  "source_language": "vi",
  "target_language": "en",
  "provider": "gemini",
  "model": "gemini-3.5-flash-lite"
}
```

Dịch tự động nhận diện ngôn ngữ nguồn (auto):

```curl
curl -X POST "http://localhost:8000/api/v1/translate" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "má nay con kia flex 3 pity ra char luôn",
       "source_language": "auto",
       "target_language": "en"
     }'
```

## Rate Limit & Giới hạn ký tự

  - Rate Limit cho User: Mỗi người dùng Discord được thực hiện tối đa 1 lượt
    dịch mỗi 2 giây. Nếu bấm liên tục sẽ nhận được thông báo nhắc nhở nhẹ nhàng.
  - Giới hạn độ dài: Từ chối yêu cầu vượt quá 2000 ký tự ngay lập tức để tiết
    kiệm token và bảo vệ tài nguyên.
  - Tự động chia nhỏ tin nhắn: Trường hợp kết quả dịch của AI dài hơn giới
    hạn 2000 ký tự của Discord, bot sẽ tự động tách thành nhiều phần tuần tự,
    đảm bảo không làm gãy vỡ các khối Markdown code block.

## Quyền riêng tư & Bảo mật

  - Không lưu tin nhắn: Hệ thống là stateless, không có database, không lưu trữ
    nội dung chat của người dùng.
  - Không đọc toàn bộ channel: Bot chỉ xử lý đúng đoạn text mà người dùng yêu
    cầu dịch thông qua lệnh /translate hoặc context menu.
  - Không log dữ liệu nhạy cảm: Log máy chủ chỉ ghi lại metadata (user ID, guild
    ID, mã ngôn ngữ, độ trễ và trạng thái thành công/thất bại).

## Đóng góp phát triển (Contributing)

1.  Fork repository.
2.  Tạo nhánh tính năng mới (git checkout -b feature/groq-provider).
3.  Commit mã nguồn rõ ràng, có type hint đầy đủ.
4.  Mở Pull Request.

## Giấy phép [LICENSE](LICENSE)

Dự án được phát hành theo giấy phép mã nguồn mở MIT License.
