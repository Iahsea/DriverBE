# Quick Start Guide - Backend Setup and Configuration

## 🚀 Current Status

✅ **Server Running Successfully**
- API accessible at: http://localhost:8000
- API Documentation: http://localhost:8000/api/docs
- ReDoc Documentation: http://localhost:8000/api/redoc
- Health Check: http://localhost:8000/health

⚠️ **Database Status**
- Database initialization attempted but failed (expected - MySQL credentials not set)
- Server continues running - all API endpoints accessible
- Once MySQL is configured, database will auto-initialize

## 📋 Step-by-Step Setup

### Step 1: Configure Environment Variables

The `.env` file has been created with default settings. Update it with your MySQL credentials:

```bash
# File: .env
DATABASE_URL=mysql+pymysql://root:@localhost:3306/secure_chat
```

**Options:**
- If MySQL root has a password: `mysql+pymysql://root:your_password@localhost:3306/secure_chat`
- If using different user: `mysql+pymysql://chat_user:password@localhost:3306/secure_chat`

### Step 2: Create MySQL Database and User

Open MySQL command line or MySQL Workbench:

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS secure_chat;

-- Create user (if using specific user instead of root)
CREATE USER 'chat_user'@'localhost' IDENTIFIED BY 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON secure_chat.* TO 'chat_user'@'localhost';
FLUSH PRIVILEGES;

-- Verify
SHOW DATABASES;
```

### Step 3: Update DATABASE_URL in .env

Edit `.env` with your MySQL connection string:

```
# Option 1: Using root with password
DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/secure_chat

# Option 2: Using dedicated chat_user
DATABASE_URL=mysql+pymysql://chat_user:your_secure_password@localhost:3306/secure_chat
```

### Step 4: Restart the Server

The server currently has auto-reload enabled. Either:

**Option A:** Manually refresh the server
```bash
# Stop current server (Ctrl+C in terminal)
# Then restart:
./venv/Scripts/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Option B:** Auto-reload by modifying .env
- The server will auto-reload when you save changes to .env
- Check terminal for confirmation: "✓ Database initialized"

### Step 5: Test the API

#### Health Check (No Auth Required)
```bash
curl http://localhost:8000/health
# Response: {"status":"healthy"}
```

#### Register New User
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'

# Response (201 Created):
# {
#   "id": "uuid",
#   "username": "testuser",
#   "email": "test@example.com",
#   "is_active": true,
#   "created_at": "2024-04-08T22:00:00"
# }
```

#### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'

# Response (200 OK):
# {
#   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
#   "token_type": "bearer"
# }
```

#### Get Current User (Requires JWT Token)
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"

# Response (200 OK):
# {
#   "id": "uuid",
#   "username": "testuser",
#   "email": "test@example.com",
#   "is_active": true,
#   "created_at": "2024-04-08T22:00:00"
# }
```

## 🔧 Configuration Reference

### Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `mysql+pymysql://root:@localhost:3306/secure_chat` | MySQL connection string |
| `SECRET_KEY` | `dev-secret-key-...` | JWT signing secret (change for production!) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token expiration time |
| `SQL_ECHO` | `False` | Enable SQL query logging |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `RELOAD` | `True` | Enable auto-reload on file changes |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated list of allowed origins |

### Server Commands

```bash
# Start server with auto-reload (development)
./venv/Scripts/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start server without auto-reload (production)
./venv/Scripts/python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Run tests
./venv/Scripts/python -m pytest tests/ -v

# Check virtual environment
./venv/Scripts/pip list

# View database schema
# Login to MySQL and run:
# USE secure_chat;
# SHOW TABLES;
# DESCRIBE users;
```

## 📂 Project Structure

```
BackEnd/
├── main.py                 # FastAPI entry point
├── requirements.txt        # Python dependencies
├── .env                    # Environment configuration (created)
├── .env.example           # Environment template
├── app/
│   ├── __init__.py
│   ├── database/
│   │   ├── database.py    # SQLAlchemy ORM setup
│   │   └── models.py      # User ORM model
│   ├── api/
│   │   ├── v1/
│   │   │   └── auth.py    # Auth endpoints
│   ├── core/
│   │   ├── crypto_bridge.py    # Kernel Driver interface + Mock
│   │   └── security.py         # JWT token management
│   ├── schemas/
│   │   └── user.py        # Pydantic validation models
│   └── websocket/
│       └── connection_manager.py  # WebSocket message distribution
└── tests/
    └── test_auth.py       # Auth endpoint tests
```

## 🐛 Troubleshooting

### Database Connection Error
```
ERROR - ✗ Database initialization failed: (1045, "Access denied for user 'root'@'localhost'")
```

**Solutions:**
1. Verify MySQL is running: `mysql -u root -p`
2. Check DATABASE_URL in .env is correct
3. Verify MySQL password matches .env configuration
4. Restart server after updating .env

### Module Import Error
```
ModuleNotFoundError: No module named 'sqlalchemy'
```

**Solution:**
```bash
./venv/Scripts/pip install -r requirements.txt --upgrade
```

### Port Already in Use
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Change PORT in .env to a different number (8001, 8002, etc.)
# Or kill existing process on port 8000
# On Windows: netstat -ano | findstr :8000
```

### Virtual Environment Issues

```bash
# Recreate virtual environment
rmdir /s venv          # Windows
python -m venv venv
./venv/Scripts/activate
pip install -r requirements.txt
```

## 🔐 Production Deployment Checklist

- [ ] Change SECRET_KEY in .env to strong random value
- [ ] Set RELOAD=False in .env
- [ ] Use production-grade MySQL (not development instance)
- [ ] Configure DATABASE_URL with strong password
- [ ] Update CORS_ORIGINS with actual frontend URLs
- [ ] Enable SSL/HTTPS for API
- [ ] Set up database backups
- [ ] Configure logging and monitoring
- [ ] Use `.env.production` for production secrets

## 📞 Support

For issues or questions:
1. Check server logs in terminal
2. Review API documentation: http://localhost:8000/api/docs
3. Check test results: `./venv/Scripts/python -m pytest tests/ -v`
4. Review error messages (database connection, module imports, etc.)

---

**Next Step:** Update .env with MySQL credentials and restart server ✅
