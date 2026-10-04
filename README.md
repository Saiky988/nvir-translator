<p align="center">
  <img src="./assets/icon.png" alt="Nvirya Translator" width="128" height="128" />
</p>

<h1 align="center">Nvirya Translator</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Discord.py-v2.0+-5865F2?style=flat&logo=discord&logoColor=white" alt="Discord.py" />
  <img src="https://img.shields.io/badge/Google%20Gemini-Flash--Lite-8E75B2?style=flat&logo=google-gemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=flat" alt="MIT License" />
  <img src="https://img.shields.io/badge/Version-v1.0.0--beta-orange?style=flat" alt="Version" />
</p>


<p align="center">
  Bot Discord dịch thuật AI theo ngữ cảnh và dịch vụ REST API siêu nhẹ viết bằng Python, sử dụng mô hình Google Gemini.
</p>

---

## Tính năng nổi bật

- **Dịch tự động theo kênh (Auto-Translate Channel):** Tự động nhận diện và dịch tin nhắn của thành viên sang từ 1 đến 3 ngôn ngữ chỉ trong 1 request Gemini duy nhất.
- **Tự động lọc bỏ ngôn ngữ nguồn:** AI tự động phát hiện ngôn ngữ gốc. Nếu tin nhắn được viết bằng một trong các ngôn ngữ đích đã cài đặt, bot sẽ chỉ dịch sang các ngôn ngữ còn lại (không bao giờ dịch lặp lại chính ngôn ngữ gốc).
- **Đồng bộ chỉnh sửa & xóa theo thời gian thực:**
  - Khi người dùng sửa tin nhắn gốc (Edit), bản dịch tương ứng sẽ tự động cập nhật nội dung tại chỗ mà không tạo tin nhắn rác.
  - Khi tin nhắn gốc bị xóa (Delete hoặc Bulk Delete), toàn bộ tin nhắn dịch tương ứng sẽ được tự động xóa sạch.
- **2 chế độ hiển thị tùy chọn:**
  - **Text Mode:** Dạng phản hồi subtext gọn gàng (`-# Tên_Tác_Giả` kèm nhãn ngôn ngữ in hoa `**EN:** ...`).
  - **Embed Mode:** Dạng thẻ Discord embed trang nhã với avatar tác giả và link trỏ tới tin nhắn gốc.
- **Không dịch cờ & Không gắn footer:** Giao diện dịch trực quan, sạch sẽ, không hiển thị icon cờ và không chèn footer thừa thãi.
- **Hiểu ngữ cảnh chat & Teencode:** Xử lý tự nhiên tiếng lóng Discord, teencode tiếng Việt (`ko`, `k`, `kh`, `hok`, `hong`, `mik`, `m`, `t`, `j`, `cx`, `r`, `đc`), thuật ngữ game (`flex 3 pity ra char luôn`), meme và lỗi chính tả.
- **Bảo toàn 100% cú pháp Discord:** Giữ nguyên user mention (`<@id>`), role mention (`<@&id>`), channel mention (`<#id>`), custom emoji (`<:name:id>`), liên kết URL và định dạng Markdown.
- **Không dịch khối code:** Khối code inline (\`\` `code` \`\`) và code block (\`\`\` \`\`\`) luôn được giữ nguyên vẹn.
- **Chống lặp vô tận (Loop Prevention):** Tự động bỏ qua tin nhắn từ bot/webhook và theo dõi ID tin nhắn do chính bot tạo ra để tránh dịch chéo.
- **Lưu trữ SQLite bất đồng bộ (WAL Mode):** Cấu hình kênh và ánh xạ tin nhắn tự động lưu bền vững, không yêu cầu cài đặt Redis hay PostgreSQL.
- **REST API + Swagger UI:** Đi kèm FastAPI service bất đồng bộ, tài liệu tương tác sẵn sàng tại `/docs`.

---

## Yêu cầu môi trường

- **Python:** Phiên bản 3.11 trở lên
- **Google Gemini API Key:** Lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/)
- **Discord Bot Token:** Đã bật **Message Content Intent** trên Developer Portal

---

## Cài đặt cho phát triển cục bộ (Local Development)

### 1. Clone mã nguồn
```bash
git clone https://github.com/Saiky988/nvir-translator.git
cd nvir-translator
```

### 2. Thiết lập môi trường ảo (Virtual Environment)
```bash
python3 -m venv .venv
source .venv/bin/activate  # Trên Windows: .venv\Scripts\activate
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

---

## Cấu hình biến môi trường

Tạo file `.env` từ file mẫu:
```bash
cp .env.example .env
```

Điền các thông số vào `.env`:
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
DATABASE_PATH=data/sachitone.db
```

### Bảng giải thích chi tiết

| Tên biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DISCORD_TOKEN` | *(Bắt buộc cho bot)* | Token bí mật của Discord Application Bot |
| `GEMINI_API_KEY` | *(Bắt buộc)* | API Key Gemini từ Google AI Studio |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Model Gemini được dùng để dịch |
| `API_HOST` | `0.0.0.0` | Địa chỉ IP lắng nghe của FastAPI |
| `API_PORT` | `8000` | Cổng HTTP (tự động nhận biến `$PORT` của hosting) |
| `BOT_PREFIX` | `!` | Prefix dự phòng cho bot |
| `LOG_LEVEL` | `INFO` | Mức độ log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `MAX_TRANSLATION_LENGTH` | `2000` | Giới hạn số ký tự tối đa cho một lượt dịch |
| `TRANSLATION_TIMEOUT` | `15` | Thời gian chờ tối đa khi gọi AI (giây) |
| `DATABASE_PATH` | `data/sachitone.db` | Đường dẫn lưu trữ file SQLite database |

---

## 💻 Chạy ứng dụng

### 1. Kiểm tra cấu hình & kết nối trước khi chạy
Chạy script kiểm tra để xác thực API key và dịch thử câu mẫu:
```bash
python scripts/setup_commands.py
```

Nếu muốn đồng bộ nhanh Slash Command vào một server cụ thể để test ngay:
```bash
python scripts/setup_commands.py --guild <ID_SERVER_CUA_BAN>
```

### 2. Khởi chạy FastAPI Service (Web API)
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Tài liệu API tương tác:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 3. Khởi chạy Discord Bot
Mở một cửa sổ terminal mới và chạy:
```bash
python -m apps.bot.main
```

---

## Triển khai (Deployment)

### 1. Triển khai trên Shared Hosting / PaaS (Pikamc, cPanel, Render, Railway, Koyeb)

Entrypoint `main.py` ở thư mục gốc giúp các nền tảng hosting dễ dàng khởi động dịch vụ:

1. **Cài đặt thư viện:** Upload và cài đặt thông qua `requirements.txt`.
2. **Cấu hình biến môi trường:** Nhập các biến `DISCORD_TOKEN`, `GEMINI_API_KEY`, v.v. vào phần Environment Variables của hosting.
3. **Chạy Web API:**
   - Entrypoint: `main:app`
   - Hoặc lệnh khởi chạy: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Chạy Discord Bot:**
   - Nếu hosting hỗ trợ background process chạy 24/7:
     ```bash
     python -m apps.bot.main
     ```
   - Hoặc sửa `main.py` để chạy song song cả API lẫn Bot bằng `multiprocessing`.

> **Lưu ý về Shared Hosting:**
> Discord Bot yêu cầu kết nối WebSocket liên tục (Gateway). Các gói shared hosting thuần HTTP (chỉ bật worker khi có người vào web) sẽ ngắt kết nối của bot khi web không có traffic. Cần đảm bảo hosting có hỗ trợ worker chạy nền bền vững.

---

### 2. Triển khai trên VPS với Docker & Compose

File `compose.yaml` đã được cấu hình sẵn volume mount `./data:/app/data` để giữ database SQLite bền vững qua các lần build/restart.

```bash
# 1. Chuẩn bị file cấu hình
cp .env.example .env
nano .env  # Điền token và API key

# 2. Khởi động API và Bot dưới dạng dịch vụ ngầm
docker compose up -d --build

# 3. Theo dõi log hoạt động
docker compose logs -f

# 4. Kiểm tra sức khỏe của API
curl http://localhost:8000/health

# 5. Dừng dịch vụ khi cần
docker compose down
```

---

## Thiết lập Discord Bot trên Developer Portal

1. Truy cập [Discord Developer Portal](https://discord.com/developers/applications).
2. Tạo ứng dụng mới (**New Application**) và thêm Bot.
3. Tại tab **Bot** -> tìm đến **Privileged Gateway Intents** -> bật kích hoạt **Message Content Intent**.
4. Tại tab **OAuth2** -> **URL Generator**:
   - Chọn Scopes: `bot`, `applications.commands`
   - Chọn Bot Permissions:
     - `View Channels`
     - `Send Messages`
     - `Read Message History`
     - `Embed Links` *(Bắt buộc nếu dùng Embed Mode)*
5. Sử dụng đường link vừa tạo để mời bot vào server của bạn.

---

## Danh sách lệnh Discord

### 1. Dịch tự động theo kênh (`/autotranslate`)
*Yêu cầu quyền **Manage Server** (Quản lý máy chủ).*

| Lệnh | Mô tả |
|---|---|
| `/autotranslate setup <channel> <lang1> [lang2] [lang3] [mode] [sync_edits] [sync_deletes]` | Bật dịch tự động trong kênh với tối đa 3 ngôn ngữ đích. |
| `/autotranslate disable <channel>` | Tắt dịch tự động trong kênh (vẫn giữ ánh xạ để xóa tin nhắn nếu cần). |
| `/autotranslate config [channel]` | Hiển thị cấu hình và trạng thái dịch hiện tại của kênh. |
| `/autotranslate languages <channel> <lang1> [lang2] [lang3]` | Thay đổi danh sách các ngôn ngữ dịch tự động của kênh. |
| `/autotranslate mode <channel> <mode>` | Chuyển đổi định dạng hiển thị giữa `text` và `embed`. |

### 2. Lệnh dịch thủ công & Tiện ích

| Lệnh | Loại | Mô tả |
|---|---|---|
| `/translate <text> <target> [source]` | Slash Command | Dịch đoạn văn bản bất kỳ sang ngôn ngữ đích (mặc định source là `auto`). |
| `Translate to English` | Message Context Menu | Chuột phải vào bất kỳ tin nhắn nào -> **Apps** -> **Translate to English**. |
| `/ping` | Slash Command | Kiểm tra độ trễ (latency) của bot tới Discord Gateway. |
| `/about` | Slash Command | Xem thông tin phiên bản và trang web chính thức của dự án. |
| `/settings` | Slash Command | Xem thông số cấu hình runtime hiện tại của bot. |

---

## Cơ sở dữ liệu SQLite & Lưu trữ (Persistence)

- **Cơ chế:** Dùng thư viện chuẩn `sqlite3` của Python với chế độ **WAL Mode** (`PRAGMA journal_mode = WAL`) và khóa bất đồng bộ (`asyncio.Lock`).
- **Vị trí lưu:** Mặc định tại `./data/translator.db` (tự động đồng bộ với thư mục `/app/data` trong Docker).
- **Các bảng dữ liệu:**
  - `auto_translate_configs`: Lưu ID server, ID kênh, danh sách ngôn ngữ đích, chế độ hiển thị (`text`/`embed`) và trạng thái bật/tắt.
  - `translation_messages`: Lưu ánh xạ giữa ID tin nhắn gốc và ID các tin nhắn dịch, tác giả, ngôn ngữ nguồn phát hiện và chuỗi hash SHA-256 để phát hiện chỉnh sửa nội dung.

---

## REST API Endpoints

- `GET /`: Trả về metadata và trạng thái hoạt động của hệ thống.
- `GET /health`: Health check siêu nhẹ, trả về `{"status": "healthy"}` (không gọi Gemini để tránh tiêu tốn quota).
- `GET /api/v1/languages`: Danh sách các mã ngôn ngữ được hỗ trợ.
- `POST /api/v1/translate`: Gửi yêu cầu dịch văn bản.

### Ví dụ gọi API bằng cURL

#### Dịch Teencode tiếng Việt sang tiếng Anh:
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

## Rate Limit & Giới hạn an toàn

- **Giới hạn người dùng:** Cooldown 1 yêu cầu / 2 giây / người dùng đối với các lệnh thủ công nhằm chống spam.
- **Giới hạn ký tự:** Từ chối xử lý các nội dung vượt quá `2000` ký tự.
- **Kiểm soát đồng thời (Concurrency Control):** Semaphore giới hạn tối đa 5 yêu cầu Gemini đồng thời trong chế độ tự động dịch để bảo vệ hạn ngạch API.
- **Chia tách tin nhắn an toàn:** Nếu bản dịch dài hơn 1950 ký tự, bot sẽ tự động chia nhỏ thành các phần kế tiếp mà không làm gãy vỡ các khối Markdown code fence.

---

## Quyền riêng tư & Bảo mật

- **Không lưu trữ nội dung chat lâu dài:** Hệ thống chỉ lưu chuỗi hash SHA-256 để phục vụ tính năng cập nhật khi sửa tin nhắn. Nội dung chat thô không được lưu vào cơ sở dữ liệu.
- **Tự động dọn dẹp:** Khi tin nhắn gốc bị xóa, toàn bộ ánh xạ trong cơ sở dữ liệu cũng được xóa theo ngay lập tức.
- **An toàn log:** Không ghi token, key hay nội dung chat riêng tư vào console và log file.

---

## Danh sách kiểm thử hoàn thành (Checklist)

- [x] Đăng ký đầy đủ nhóm lệnh `/autotranslate` (`setup`, `disable`, `config`, `languages`, `mode`).
- [x] Dịch đồng thời nhiều ngôn ngữ đích bằng 1 request AI cấu trúc JSON duy nhất.
- [x] Tự động loại bỏ ngôn ngữ nguồn (ví dụ: gõ tiếng Việt thì chỉ dịch ra Anh & Tây Ban Nha).
- [x] Hỗ trợ hiển thị Text và Embed sạch sẽ, không có cờ và không có footer.
- [x] Tắt mention tự động (`allowed_mentions=none`) để tránh ping làm phiền người dùng.
- [x] Tự động cập nhật bản dịch khi sửa tin nhắn gốc (`on_message_edit`).
- [x] Tự động xóa bản dịch khi xóa tin nhắn gốc (`on_message_delete` & `on_raw_bulk_message_delete`).
- [x] Chống lặp dịch và bỏ qua tin nhắn từ bot hoặc webhook.
- [x] Lưu trữ cấu hình bền vững qua SQLite WAL mode và volume mount Docker.
- [x] Tiếp tục hỗ trợ các lệnh cũ `/translate`, Context Menu, `/ping`, `/about`, `/settings` và REST API.

---

## Đóng góp phát triển (Contributing)

1. Fork repository.
2. Tạo nhánh tính năng mới (`git checkout -b feature/new-provider`).
3. Commit mã nguồn rõ ràng, có type hint đầy đủ.
4. Mở Pull Request.

---

## Giấy phép (License)

Dự án được phân phối theo giấy phép mã nguồn mở [MIT License](LICENSE).
