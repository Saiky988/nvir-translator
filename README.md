<img src="./assets/icon.png" alt="Sachitone Translator" width="128" height="128" />

# Translator

Sachitone Translator là bot Discord dịch thuật AI theo ngữ cảnh và dịch vụ REST API siêu nhẹ viết bằng Python, sử dụng mô hình Google Gemini (`gemini-3.5-flash-lite`).

Khác với các công cụ dịch từ-qua-từ thông thường, Sachitone Translator được thiết kế tối ưu cho cộng đồng chat Discord: hiểu tự nhiên ngôn ngữ nói, teencode tiếng Việt, từ lóng game, viết tắt, meme, emoji và lỗi chính tả, đồng thời bảo toàn 100% cú pháp Discord (mentions, URLs, code blocks).

---

## Tính năng nổi bật

- **Hiểu ngữ cảnh chat & Teencode:** Xử lý tự nhiên các từ viết tắt tiếng Việt (`ko`, `k`, `kh`, `hok`, `hong`, `mik`, `m`, `t`, `j`, `cx`, `r`, `đc`), tiếng lóng game (`flex 3 pity ra char luôn`) mà không phụ thuộc vào từ điển cơ học.
- **Bảo toàn cú pháp Discord:** Giữ nguyên user mention (`<@123>`), role mention (`<@&123>`), channel mention (`<#123>`), custom emoji (`<:name:123>`), URL liên kết và định dạng Markdown.
- **Không dịch khối code:** Khối code inline (\`\` `code` \`\`) và code block (\`\`\` ... \`\`\`) được giữ nguyên hoàn toàn.
- **Giữ đúng sắc thái (Tone):** Bảo lưu văn phong tự nhiên, hài hước, suồng sã; không biến các câu chat mạng thành văn xuôi trịnh trọng.
- **2 phương thức dịch trên Discord:**
  - Slash command: `/translate <text> <target> [source]` (tự động gợi ý ngôn ngữ).
  - Context Menu: Chuột phải vào bất kỳ tin nhắn nào -> **Apps** -> **Translate to English**.
- **REST API + Swagger UI:** Đi kèm FastAPI service bất đồng bộ, tài liệu tương tác sẵn sàng tại `/docs`.
- **In-Memory Cache & Rate Limit:** Bounded LRU cache và giới hạn tần suất tích hợp sẵn trong bộ nhớ, không cần Redis hay database.
- **Triển khai linh hoạt:** Tương thích cả Shared Hosting thông thường lẫn môi trường Docker trên VPS.

---

## Yêu cầu môi trường

- Python 3.11 trở lên
- Google Gemini API Key
- Discord Bot Token (đã bật **Message Content Intent**)

---

## Cài đặt cho phát triển cục bộ (Local Development)

### 1. Clone mã nguồn
```bash
git clone https://github.com/your-org/sachitone-translator.git
cd sachitone-translator
```

### 2. Thiết lập Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # Trên Windows: .venv\Scripts\activate
```

### 3. Cài đặt thư viện
```bash
pip install -r requirements.txt
```

---

## Cấu hình biến môi trường

Tạo file cấu hình `.env` từ mẫu:
```bash
cp .env.example .env
```

Điền các thông số cần thiết:
```env
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

### Bảng giải thích chi tiết

| Tên biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DISCORD_TOKEN` | *(Bắt buộc cho bot)* | Token bí mật của Discord Bot |
| `GEMINI_API_KEY` | *(Bắt buộc)* | API Key lấy từ Google AI Studio |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Model Gemini được dùng để dịch |
| `API_HOST` | `0.0.0.0` | Địa chỉ IP lắng nghe của FastAPI |
| `API_PORT` | `8000` | Cổng HTTP (tự động ưu tiên biến `$PORT` của hosting) |
| `BOT_PREFIX` | `!` | Prefix dự phòng cho Discord bot |
| `LOG_LEVEL` | `INFO` | Mức log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `MAX_TRANSLATION_LENGTH` | `2000` | Giới hạn số ký tự cho một lượt dịch |
| `TRANSLATION_TIMEOUT` | `15` | Thời gian chờ tối đa khi gọi AI (giây) |

---

## Chạy cục bộ (Local Run)

### Kiểm tra kết nối trước khi khởi động
Chạy script kiểm tra để xác thực cấu hình và dịch thử câu mẫu:
```bash
python scripts/setup_commands.py
```

Nếu muốn đồng bộ ngay Slash Command vào 1 server cụ thể để test (bỏ qua thời gian đợi Discord sync toàn cầu):
```bash
python scripts/setup_commands.py --guild <ID_SERVER_CUA_BAN>
```

### Chạy FastAPI Service
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Tài liệu API tương tác:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Chạy Discord Bot
Mở một cửa sổ terminal mới và chạy:
```bash
python -m apps.bot.main
```

---

## Triển khai (Deployment)

### 1. Triển khai trên Shared Hosting / PaaS (cPanel, Render, Railway, Koyeb)

Dự án có sẵn file `main.py` ở thư mục gốc giúp các dịch vụ hosting dễ dàng trỏ tới ứng dụng mà không cần cấu hình phức tạp:

1. **Cài đặt thư viện:** Chạy lệnh hoặc upload theo `requirements.txt`.
2. **Cấu hình biến môi trường:** Khai báo các biến `DISCORD_TOKEN`, `GEMINI_API_KEY`, v.v. trên trang quản trị của nhà cung cấp.
3. **Khởi chạy Web App (FastAPI):**
   - Chỉ định entrypoint là: `main:app`
   - Hoặc lệnh khởi chạy:
     ```bash
     uvicorn main:app --host 0.0.0.0 --port $PORT
     ```
4. **Khởi chạy Discord Bot:**
   - Nếu hosting hỗ trợ background worker/process chạy ngầm liên tục:
     ```bash
     python -m apps.bot.main
     ```

> **Lưu ý quan trọng về Shared Hosting:**
> Discord Bot sử dụng kết nối liên tục (persistent WebSocket connection) qua Discord Gateway. Các gói shared web hosting thuần túy (chỉ kích hoạt worker khi có HTTP request gửi đến) sẽ làm bot mất kết nối khi không có ai truy cập web.
> Nếu hosting chỉ hỗ trợ HTTP Web, bạn có thể chạy API tại đó và chạy Bot (`python -m apps.bot.main`) trên một VPS hoặc dịch vụ hỗ trợ background worker miễn phí. Tuyệt đối không dùng request HTTP giả lập để cố duy trì bot Discord.

---

### 2. Triển khai trên VPS với Docker & Compose

Mã nguồn đi kèm sẵn file `Dockerfile` và `compose.yaml` cho phép khởi tạo cả API và Discord Bot song song chỉ với 1 câu lệnh.

#### Các bước triển khai:

1. **Chuẩn bị file cấu hình trên VPS:**
   ```bash
   git clone https://github.com/your-org/sachitone-translator.git
   cd sachitone-translator
   cp .env.example .env
   nano .env  # Điền DISCORD_TOKEN và GEMINI_API_KEY
   ```

2. **Khởi động các dịch vụ ngầm:**
   ```bash
   docker compose up -d --build
   ```

3. **Kiểm tra log trạng thái:**
   ```bash
   docker compose logs -f
   ```

4. **Kiểm tra sức khỏe dịch vụ API:**
   ```bash
   curl http://localhost:8000/health
   ```

5. **Dừng dịch vụ khi cần:**
   ```bash
   docker compose down
   ```

---

## Thiết lập Discord Bot trên Developer Portal

1. Truy cập [Discord Developer Portal](https://discord.com/developers/applications).
2. Tạo mới một Application và điều hướng đến tab **Bot**.
3. Tại mục **Privileged Gateway Intents**, bật kích hoạt **Message Content Intent**.
4. Vào mục **OAuth2** -> **URL Generator**:
   - Chọn Scopes: `bot`, `applications.commands`
   - Chọn Bot Permissions:
     - `Read Messages/View Channels`
     - `Send Messages`
     - `Read Message History`
5. Sử dụng link mời vừa tạo để cấp quyền cho bot vào server Discord.

---

## Danh sách lệnh Discord

| Lệnh | Loại | Mô tả |
|---|---|---|
| `/translate <text> <target> [source]` | Slash Command | Dịch văn bản sang ngôn ngữ đích (hỗ trợ autocomplete gợi ý ngôn ngữ). |
| `Translate to English` | Message Context Menu | Chuột phải vào bất kỳ tin nhắn nào -> **Apps** -> **Translate to English**. |
| `/ping` | Slash Command | Kiểm tra độ trễ (latency) của bot tới Discord Gateway. |
| `/about` | Slash Command | Hiển thị thông tin phiên bản và trang web chính thức của dự án. |
| `/settings` | Slash Command | Xem thông số cấu hình runtime hiện tại của bot. |

---

## REST API Endpoints

- `GET /`: Trả về metadata và trạng thái online của service.
- `GET /health`: Health check siêu nhẹ, trả về `{"status": "healthy"}` (không gọi Gemini).
- `GET /api/v1/languages`: Danh sách ngôn ngữ phổ biến kèm cờ quốc gia.
- `POST /api/v1/translate`: Gửi yêu cầu dịch thuật văn bản.

### Ví dụ gọi API bằng cURL

#### Dịch Teencode tiếng Việt:
```bash
curl -X POST "http://localhost:8000/api/v1/translate" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "hnay mik hok biet lam j",
       "source_language": "vi",
       "target_language": "en"
     }'
```

**Kết quả trả về:**
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

#### Dịch tự động nhận diện ngôn ngữ nguồn (`auto`):
```bash
curl -X POST "http://localhost:8000/api/v1/translate" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "má nay con kia flex 3 pity ra char luôn",
       "source_language": "auto",
       "target_language": "en"
     }'
```

---

## Rate Limit & Giới hạn ký tự

- **Rate Limit người dùng:** Cooldown 1 lượt dịch / 2 giây / người dùng nhằm tránh spam.
- **Giới hạn ký tự:** Từ chối xử lý các nội dung vượt quá `2000` ký tự.
- **Tự động chia tách tin nhắn:** Nếu kết quả trả về từ AI vượt quá 1950 ký tự, bot sẽ tự động chia nhỏ thành các tin nhắn kế tiếp mà không làm vỡ các khối Markdown code fence.

---

## Quyền riêng tư & Bảo mật

- **Không lưu dữ liệu chat:** Ứng dụng là stateless, không có database, không ghi lại nội dung tin nhắn của người dùng.
- **Chỉ gửi nội dung cần dịch:** Bot chỉ gửi duy nhất đoạn văn bản được yêu cầu dịch tới Google Gemini API.
- **An toàn log:** Không ghi token, key hoặc nội dung hội thoại riêng tư vào log file.

---

## Đóng góp phát triển (Contributing)

1. Fork repository.
2. Tạo nhánh tính năng mới (`git checkout -b feature/new-provider`).
3. Commit mã nguồn rõ ràng, có type hinting đầy đủ.
4. Tạo Pull Request.

---

## Giấy phép (License)

Dự án được phân phối theo giấy phép mã nguồn mở [MIT License](LICENSE).
