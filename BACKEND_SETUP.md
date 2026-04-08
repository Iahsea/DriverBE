# Secure Chat System Backend - Setup & Run Guide

## 📋 Mục lục
1. [Kiến trúc hệ thống](#kiến-trúc)
2. [Cài đặt và chạy](#cài-đặt)
3. [API Endpoints](#api-endpoints)
4. [WebSocket Guide](#websocket)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

---

## 🏗️ Kiến trúc

```
Secure Chat System
├── Frontend (React)
│   └── ws://localhost:8000/ws/chat
│   └── http://localhost:8000/api/v1/auth/*
│
├── Backend (FastAPI)
│   ├── /api/v1/auth/register    → POST (UserCreate)
│   ├── /api/v1/auth/login       → POST (UserLogin)
│   ├── /api/v1/auth/me          → GET  (with JWT token)
│   └── /ws/chat                 → WebSocket
│
├── Database (PostgreSQL/SQLite)
│   └── Users table (with MD5 password_hash)
│
└── Kernel Driver (Windows KMDF / Linux LKM)
    ├── MD5 hash (via IOCTL)
    └── AES encrypt/decrypt (future)
```

### Cấu trúc thư mục Backend
```
BackEnd/
├── main.py                          # FastAPI entry point
├── requirements.txt                 # Python dependencies
├── test_backend.py                  # Test suite
├── test_websocket.py                # WebSocket test client
├── PROJECT_SPEC.md                  # Project specification
├── auth_specification.md            # Auth flows documentation
│
└── app/
    ├── __init__.py
    ├── api/v1/
    │   ├── __init__.py
    │   └── auth.py                  # Auth routes (register, login, me)
    │
    ├── core/
    │   ├── __init__.py
    │   ├── crypto_bridge.py         # IOCTL bridge + Mock crypto
    │   └── security.py              # JWT token handling
    │
    ├── database/
    │   ├── __init__.py
    │   ├── database.py              # SQLAlchemy setup
    │   └── models.py                # User model (ORM)
    │
    ├── schemas/
    │   ├── __init__.py
    │   └── user.py                  # Pydantic schemas
    │
    └── websocket/
        ├── __init__.py
        └── connection_manager.py    # WebSocket connection management
```

---

## 🚀 Cài đặt và Chạy

### 1️⃣ Yêu cầu hệ thống
- **Python 3.13+** (tested on 3.13.7)
- **Windows 10/11** hoặc **Linux (Ubuntu 20.04+)**
- **PostgreSQL 12+** (hoặc SQLite for development)

### 2️⃣ Cài đặt Dependencies

```bash
# Navigate to backend directory
cd d:/HVKTMM_TL/Nam_4/Ki_2/Dot_1/LTDRV/BackEnd

# Install dependencies
/d/D_CNTT/Python313/python -m pip install -r requirements.txt
```

**Dependencies được cài:**
- `fastapi>=0.111.0` - Web framework
- `uvicorn[standard]>=0.30.0` - ASGI server
- `pydantic>=2.7.0` - Data validation
- `websockets>=16.0` - WebSocket support
- `SQLAlchemy>=2.0.0` - ORM
- `PyJWT>=2.8.0` - JWT tokens
- `cryptography>=41.0.0` - Mock encryption
- `psycopg2-binary>=2.9.0` - PostgreSQL driver
- `email-validator>=2.0.0` - Email validation

### 3️⃣ Configuration

#### Database Configuration
Mặc định dùng **SQLite** cho development:
```python
# file: app/database/database.py
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./secure_chat.db"  # SQLite
)
```

**Để dùng PostgreSQL:**
```bash
# Set environment variable
set DATABASE_URL=postgresql://user:password@localhost:5432/secure_chat_db
# hoặc
export DATABASE_URL=postgresql://user:password@localhost:5432/secure_chat_db
```

#### JWT Secret
```bash
# Set secret key (production)
set SECRET_KEY=your-secret-key-here
export SECRET_KEY=your-secret-key-here
```

Default (development): `dev-secret-key-change-in-production`

### 4️⃣ Chạy Server

```bash
cd "/d/HVKTMM_TL/Nam_4/Ki_2/Dot_1/LTDRV/BackEnd"

# Chạy FastAPI server (thường port 8000)
/d/D_CNTT/Python313/python main.py
```

**Output:**
```
✓ Database initialized
✓ CORS configured for origins: ['http://localhost:3000', ...]
✓ Application ready to handle requests
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Hoặc dùng uvicorn trực tiếp:**
```bash
/d/D_CNTT/Python313/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📡 API Endpoints

### Authentication Routes `/api/v1/auth/`

#### 1. **POST /register** - Đăng ký user mới

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true,
  "is_verified": false,
  "created_at": "2026-04-08T21:50:00Z"
}
```

**Quy trình:**
1. Validate username/email (3-50 chars, valid email)
2. Hash password với **Kernel Driver** (MD5)
3. Lưu user vào database
4. Trả về user info (không có password_hash)

---

#### 2. **POST /login** - Đăng nhập

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePass123!"
  }'
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "email": "john@example.com",
    "is_active": true,
    "is_verified": false,
    "created_at": "2026-04-08T21:50:00Z"
  }
}
```

**Quy trình:**
1. Tìm user trong database
2. Hash password input với **Kernel Driver** (MD5)
3. So sánh hash với DB
4. Nếu khớp → Tạo JWT Token
5. Trả về token + user info

---

#### 3. **GET /me** - Lấy thông tin user hiện tại

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true,
  "is_verified": false,
  "created_at": "2026-04-08T21:50:00Z"
}
```

---

### Health Check Routes

#### GET /
```bash
curl http://localhost:8000/
# Response: {"service": "secure-chat-backend", "status": "running"}
```

#### GET /health
```bash
curl http://localhost:8000/health
# Response: {"status": "healthy", "message": "Server is running"}
```

#### GET /api/v1/ping
```bash
curl http://localhost:8000/api/v1/ping
# Response: {"message": "pong", "timestamp": "2026-04-08T..."}
```

---

## 🔌 WebSocket Guide

### Connect to WebSocket
```javascript
// Frontend (JavaScript/React)
const ws = new WebSocket('ws://localhost:8000/ws/chat');

ws.onopen = () => {
  console.log('Connected');
  ws.send('Hello from client');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Message:', message);
};

ws.onerror = (error) => {
  console.error('Error:', error);
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

### Message Format

**System Message (on join):**
```json
{
  "type": "system",
  "content": "Client joined. Total connections: 1",
  "timestamp": "2026-04-08T21:50:00Z"
}
```

**Chat Message:**
```json
{
  "type": "message",
  "content": "Hello everyone!",
  "timestamp": "2026-04-08T21:50:05Z"
}
```

### Python Test Client
```bash
cd "/d/HVKTMM_TL/Nam_4/Ki_2/Dot_1/LTDRV/BackEnd"

# Run WebSocket test
/d/D_CNTT/Python313/python test_websocket.py
```

---

## 🧪 Testing

### Run Full Test Suite
```bash
cd "/d/HVKTMM_TL/Nam_4/Ki_2/Dot_1/LTDRV/BackEnd"

/d/D_CNTT/Python313/python test_backend.py
```

**Tests included:**
- ✓ Crypto bridge (MD5 hash)
- ✓ JWT token creation/verification
- ✓ Health check endpoints
- ✓ User registration
- ✓ Login flow
- ✓ Get current user
- ✓ Error handling

**Output example:**
```
============================================================
Secure Chat Backend Test Suite
============================================================

--- Testing Crypto Bridge ---
✓ Hash test passed: a1b2c3d4e5f6...
✓ Deterministic hash test passed
✓ Different password test passed

--- Testing JWT Security ---
✓ JWT test passed: Token=eyJhbGciOiJI...
✓ Invalid token test passed: Caught HTTPException

--- Testing Auth Flow ---
✓ Register test passed: User testuser_abc123 created
✓ Duplicate username test passed
✓ Login success test passed: Token obtained
✓ Invalid password test passed
✓ Get current user test passed
✓ Invalid token test passed

============================================================
✓ All tests passed!
============================================================
```

### Individual Component Tests

**Test Crypto Bridge Only:**
```bash
/d/D_CNTT/Python313/python -c "
from app.core.crypto_bridge import crypto_bridge
import asyncio

async def test():
    hash1 = await crypto_bridge.hash_password_with_driver('TestPass123')
    print(f'MD5 Hash: {hash1}')

asyncio.run(test())
"
```

**Test Database Connection:**
```bash
/d/D_CNTT/Python313/python -c "
from app.database.database import init_db, SessionLocal
from app.database.models import User

init_db()
print('✓ Database initialized')

session = SessionLocal()
users = session.query(User).all()
print(f'✓ Users in DB: {len(users)}')
"
```

---

## 📚 Postman Collection

### Import URLs

**Base URL:** `http://localhost:8000`

#### Register
- **Method:** POST
- **URL:** `{{base_url}}/api/v1/auth/register`
- **Body (JSON):**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!"
}
```

#### Login
- **Method:** POST
- **URL:** `{{base_url}}/api/v1/auth/login`
- **Body (JSON):**
```json
{
  "username": "john_doe",
  "password": "SecurePass123!"
}
```

#### Get Me
- **Method:** GET
- **URL:** `{{base_url}}/api/v1/auth/me`
- **Headers:**
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`

---

## 🔧 Troubleshooting

### Issue 1: "Module not found" errors

**Solution:**
```bash
# Ensure you're in correct directory
cd "/d/HVKTMM_TL/Nam_4/Ki_2/Dot_1/LTDRV/BackEnd"

# Reinstall dependencies
/d/D_CNTT/Python313/python -m pip install -r requirements.txt --upgrade

# Verify imports
/d/D_CNTT/Python313/python -c "from app.database.database import init_db; print('✓ OK')"
```

### Issue 2: Port 8000 already in use

**Solution:**
```bash
# Change port in main.py or use:
/d/D_CNTT/Python313/python -m uvicorn main:app --port 8001
```

### Issue 3: Database locked (SQLite)

**Solution:**
```bash
# Delete old database and restart
del /Q secure_chat.db
/d/D_CNTT/Python313/python main.py
```

### Issue 4: CORS errors from React

**Check main.py CORS configuration:**
```python
ALLOWED_ORIGINS = [
    "http://localhost:3000",      # Add your React server here
    "http://localhost:5173",
]
```

### Issue 5: "Driver not found" message

**This is NORMAL** - it means:
- Kernel Driver not installed yet (expected for development)
- System falling back to **Mock MD5 implementation** using Python's `cryptography` library
- All hashing tests will work correctly using mock

**When actual driver is installed:**
```
✓ Windows KMDF driver loaded from: CryptoChatDriver.dll
```

---

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(64) NOT NULL,  -- MD5 hash từ Driver
  is_active BOOLEAN DEFAULT TRUE,
  is_verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_login_at TIMESTAMP,
  
  CONSTRAINT username_length CHECK (LENGTH(username) >= 3)
);

CREATE INDEX idx_username ON users(username);
CREATE INDEX idx_email ON users(email);
```

---

## 🔐 Security Notes

⚠️ **Important:**

1. **Password Hashing:** Được thực hiện bởi **Kernel Driver** (hoặc mock cho development)
   - Plain text password KHÔNG bao giờ lưu
   - MD5 hash generated bởi Driver được lưu trong DB
   
2. **JWT Token:**
   - Hết hạn mặc định: 30 phút (có thể config)
   - Secret key phải được thay đổi trong production
   - Token phải được gửi trong `Authorization: Bearer {token}` header

3. **CORS:**
   - Configure strictly cho production
   - Chỉ allow domain của React frontend

4. **HTTPS:**
   - Enable HTTPS trong production
   - Update cookie settings for secure transmission

---

## 📞 Contact & Support

- Project: Secure Chat System (LTDRV - Kernel Driver Integration)
- Tech Stack: Python FastAPI + React + PostgreSQL + Kernel Driver
- Architecture: Fullstack with User-mode ↔ Kernel-mode communication

---

## 📝 Next Steps

1. ✅ Backend FastAPI setup (hoàn chỉnh)
2. ✅ Auth routes (Register, Login, Me)
3. ✅ WebSocket endpoint
4. ✅ Database models + ORM
5. ✅ Crypto bridge (IOCTL + Mock)
6. ⏳ Implement actual C Kernel Driver (KMDF/LKM)
7. ⏳ AES encrypt/decrypt via Driver
8. ⏳ Frontend React components
9. ⏳ Integration testing
10. ⏳ Production deployment

---

**Version:** 1.0.0  
**Last Updated:** April 8, 2026  
**Status:** ✓ Ready for development and testing
