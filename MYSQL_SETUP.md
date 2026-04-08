# MySQL Configuration Guide

## Tình trạng hiện tại
✅ **Server đang chạy trên http://localhost:8000**
⚠️ Database chưa được kết nối (cần MySQL credentials)

## Cách 1: Cấu hình MySQL (Recommended)

### Bước 1: Tạo Database
```sql
-- Mở MySQL Command Line (hoặc MySQL Workbench)
CREATE DATABASE secure_chat;
CREATE USER 'chat_user'@'localhost' IDENTIFIED BY 'secure_password123';
GRANT ALL PRIVILEGES ON secure_chat.* TO 'chat_user'@'localhost';
FLUSH PRIVILEGES;
```

### Bước 2: Set Environment Variable
**Trên Windows PowerShell:**
```powershell
$env:DATABASE_URL = "mysql+pymysql://chat_user:secure_password123@localhost:3306/secure_chat"
```

**Trên Windows CMD:**
```cmd
set DATABASE_URL=mysql+pymysql://chat_user:secure_password123@localhost:3306/secure_chat
```

**Trên Linux/Mac:**
```bash
export DATABASE_URL="mysql+pymysql://chat_user:secure_password123@localhost:3306/secure_chat"
```

### Bước 3: Chạy lại Server
```bash
cd "d:/HVKTMM_TL/Nam_4/Ki_2/Dot_1/LTDRV/BackEnd"
./venv/Scripts/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Cách 2: Dùng Default MySQL (root user, no password)

Nếu bạn dùng MySQL Server mặc định (root user, không có password), hãy tạo database:

```sql
-- Kết nối với default root (password rỗng)
CREATE DATABASE secure_chat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Sau đó chạy: `./venv/Scripts/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`

---

## Cách 3: Sử dụng SQLite cho Development (Nhanh nhất)

Nếu chưa có MySQL hoặc muốn test nhanh, có thể quay lại SQLite:

```python
# Tệp: app/database/database.py
# Thay đổi dòng này:
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./secure_chat.db"  # Thay về SQLite
)
```

---

## Kiểm tra Server

**API Docs (đã chạy):**
- http://localhost:8000/api/docs (Swagger UI)
- http://localhost:8000/api/redoc (ReDoc)

**Health Check:**
```bash
curl http://localhost:8000/health
# Response: {"status": "healthy", "message": "Server is running"}
```

**API Root:**
```bash
curl http://localhost:8000/
# Response: {"service": "secure-chat-backend", "status": "running", ...}
```

---

## MySQL Connection String Format

```
mysql+pymysql://username:password@host:port/database
```

**Examples:**
- `mysql+pymysql://root:password@localhost:3306/secure_chat`
- `mysql+pymysql://chat_user:secure_password123@localhost:3306/secure_chat`
- `mysql+pymysql://root@localhost:3306/secure_chat` (no password)

---

## Troubleshooting

| Lỗi | Giải pháp |
|-----|----------|
| `Access denied for user 'root'@'localhost'` | Thiếu password hoặc sai credentials |
| `Can't connect to MySQL server on 'localhost'` | MySQL server không chạy |
| `Unknown database 'secure_chat'` | Database chưa được tạo |

**Kiểm tra MySQL đang chạy:**
```bash
# Windows
tasklist | findstr mysql

# Linux/Mac
ps aux | grep mysql
```

---

## Các tệp liên quan
- `app/database/database.py` - Cấu hình database connection
- `requirements.txt` - Dependencies (bao gồm pymysql)
- `.env` - (Tạo để lưu DATABASE_URL nếu cần)

---

**Status:** Server chạy ✅ | Database chờ config ⏳
