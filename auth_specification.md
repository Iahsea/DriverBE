# Authentication Specification
## Secure Chat System - Register & Login Flow

---

## 1. Tổng Quan Hệ Thống

```
┌────────────────────────────────────────────────────────────────┐
│                      React Frontend                             │
│  (LoginForm, RegisterForm, AuthContext)                         │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ HTTP/JSON
                 ↓
┌────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                              │
│  (/register, /login, /me endpoints)                             │
│  - Xác thực thông tin                                           │
│  - Gưi mật khẩu xuống Driver                                    │
│  - So sánh MD5 hash từ Database                                 │
│  - Tạo JWT Token                                               │
└────────────────┬─────────────────────────────────────────────┘
                 │
         ┌───────┴────────┐
         │                │
         ↓                ↓
    ┌────────────┐  ┌──────────────┐
    │   Driver   │  │  PostgreSQL  │
    │ (MD5 Hash) │  │   Database   │
    └────────────┘  └──────────────┘
```

---

## 2. Quy Trình Register (Đăng Ký)

### 2.1 Luồng Đầy Đủ

```
┌─ Frontend ───────────────────────────────────────────────────┐
│                                                               │
│  1. User nhập form                                           │
│     - username (3-50 ký tự)                                 │
│     - email (email hợp lệ)                                  │
│     - password (8+ ký tự)                                   │
│     - confirm_password (match password)                     │
│                                                               │
│  2. Validate frontend:                                       │
│     - Kiểm tra format                                        │
│     - Password match                                         │
│     - Password strength                                      │
│                                                               │
│  3. POST /api/v1/auth/register                              │
│     ```json                                                  │
│     {                                                         │
│       "username": "john_doe",                               │
│       "email": "john@example.com",                          │
│       "password": "SecurePass123!"                          │
│     }                                                         │
│     ```                                                       │
└─────────────┬───────────────────────────────────────────────┘
              │
              ↓
┌─ FastAPI Backend ────────────────────────────────────────────┐
│                                                               │
│  4. Nhận request từ frontend                                 │
│                                                               │
│  5. Validate:                                                │
│     - Username không trùng (check DB)                        │
│     - Email không trùng (check DB)                           │
│     - Password format hợp lệ                                │
│                                                               │
│  6. Chuẩn bị dữ liệu gửi Driver:                            │
│     ```json                                                  │
│     {                                                         │
│       "operation": "hash_md5",                              │
│       "data": "SecurePass123!"                              │
│     }                                                         │
│     ```                                                       │
│                                                               │
│  7. Gọi Driver via IOCTL                                     │
│     (crypto_bridge.py - hash_password_with_driver())        │
└─────────────┬───────────────────────────────────────────────┘
              │
              ↓
┌─ Kernel Driver ──────────────────────────────────────────────┐
│                                                               │
│  8. Nhận request từ FastAPI                                  │
│                                                               │
│  9. Thực hiện MD5 Hashing:                                  │
│     Input:  "SecurePass123!"                                │
│     Output: "a1b2c3d4e5f6..."  (32 ký tự hex)             │
│                                                               │
│  10. Trả về bản hash cho FastAPI                           │
└─────────────┬───────────────────────────────────────────────┘
              │
              ↓
┌─ FastAPI Backend (tiếp) ─────────────────────────────────────┐
│                                                               │
│  11. Nhận bản hash MD5 từ Driver                            │
│      hash_value = "a1b2c3d4e5f6..."                       │
│                                                               │
│  12. Lưu vào Database:                                      │
│      CREATE user với:                                        │
│      - id: UUID (auto)                                       │
│      - username: "john_doe"                                 │
│      - email: "john@example.com"                            │
│      - password_hash: "a1b2c3d4e5f6..."  ← Hash từ Driver  │
│      - created_at: now()                                     │
│      - is_active: true                                       │
│                                                               │
│  13. Trả response về frontend:                              │
│      ```json                                                  │
│      {                                                         │
│        "status": "success",                                  │
│        "message": "User đăng ký thành công",               │
│        "user_id": "uuid-123",                              │
│        "username": "john_doe"                               │
│      }                                                         │
│      ```                                                       │
└─────────────┬───────────────────────────────────────────────┘
              │
              ↓
┌─ Frontend ───────────────────────────────────────────────────┐
│                                                               │
│  14. Hiển thị thông báo thành công                          │
│      → Auto redirect sang trang Login                        │
│      Hoặc auto-login và redirect sang Chat                  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 API Endpoint - Register

**URL:** `POST /api/v1/auth/register`

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!"
}
```

**Response (Success - 201):**
```json
{
  "status": "success",
  "message": "User đăng ký thành công",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "email": "john@example.com",
    "created_at": "2026-04-08T21:50:00Z"
  }
}
```

**Response (Error - 400):**
```json
{
  "status": "error",
  "message": "Username đã tồn tại",
  "code": "USERNAME_EXISTS"
}
```

---

## 3. Quy Trình Login (Đăng Nhập)

### 3.1 Luồng Đầy Đủ

```
┌─ Frontend ───────────────────────────────────────────────────┐
│                                                               │
│  1. User nhập form                                           │
│     - username hoặc email                                    │
│     - password                                               │
│                                                               │
│  2. POST /api/v1/auth/login                                 │
│     ```json                                                  │
│     {                                                         │
│       "username": "john_doe",                               │
│       "password": "SecurePass123!"                          │
│     }                                                         │
│     ```                                                       │
└─────────────┬───────────────────────────────────────────────┘
              │
              ↓
┌─ FastAPI Backend ────────────────────────────────────────────┐
│                                                               │
│  3. Nhận request từ frontend                                 │
│                                                               │
│  4. Query Database:                                          │
│     SELECT * FROM users WHERE username = "john_doe"         │
│                                                               │
│  5. Kiểm tra user tồn tại:                                  │
│     - Nếu không tồn tại → Return error 401                  │
│                                                               │
│  6. Chuẩn bị dữ liệu gửi Driver:                            │
│     ```json                                                  │
│     {                                                         │
│       "operation": "hash_md5",                              │
│       "data": "SecurePass123!"                              │
│     }                                                         │
│     ```                                                       │
│                                                               │
│  7. Gọi Driver via IOCTL                                     │
│     (crypto_bridge.py - hash_password_with_driver())        │
└─────────────┬───────────────────────────────────────────────┘
              │
              ↓
┌─ Kernel Driver ──────────────────────────────────────────────┐
│                                                               │
│  8. Nhận request từ FastAPI                                  │
│                                                               │
│  9. Thực hiện MD5 Hashing:                                  │
│     Input:  "SecurePass123!"                                │
│     Output: "a1b2c3d4e5f6..."  (32 ký tự hex)             │
│                                                               │
│  10. Trả về bản hash cho FastAPI                           │
└─────────────┬───────────────────────────────────────────────┘
              │
              ↓
┌─ FastAPI Backend (tiếp) ─────────────────────────────────────┐
│                                                               │
│  11. Nhận bản hash MD5 từ Driver                            │
│      hash_from_driver = "a1b2c3d4e5f6..."                 │
│                                                               │
│  12. So sánh với hash trong Database:                       │
│      hash_in_db = user.password_hash                        │
│                                                               │
│      if hash_from_driver == hash_in_db:                     │
│        ✓ Password khớp → Tạo JWT Token                      │
│      else:                                                    │
│        ✗ Password sai → Return error 401                    │
│                                                               │
│  13. Tạo JWT Token:                                         │
│      ```json                                                  │
│      {                                                         │
│        "user_id": "550e8400-e29b-41d4-a716-446655440000"   │
│        "username": "john_doe",                              │
│        "exp": 1712679000,                                    │
│        "iat": 1712592600                                     │
│      }                                                         │
│      ```                                                       │
│      JWT = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...       │
│                                                               │
│  14. Trả response về frontend:                              │
│      ```json                                                  │
│      {                                                         │
│        "status": "success",                                  │
│        "access_token": "eyJhbGc...",                        │
│        "token_type": "bearer",                              │
│        "user": {                                              │
│          "id": "550e8400...",                               │
│          "username": "john_doe",                            │
│          "email": "john@example.com"                        │
│        }                                                       │
│      }                                                         │
│      ```                                                       │
└─────────────┬───────────────────────────────────────────────┘
              │
              ↓
┌─ Frontend ───────────────────────────────────────────────────┐
│                                                               │
│  15. Nhận JWT Token từ Backend                              │
│                                                               │
│  16. Lưu vào:                                               │
│      - localStorage (hoặc sessionStorage)                    │
│      - AuthContext                                           │
│                                                               │
│  17. Set Authorization Header cho requests tiếp theo:       │
│      Header: Authorization: Bearer {access_token}           │
│                                                               │
│  18. Redirect sang trang Chat                               │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 API Endpoint - Login

**URL:** `POST /api/v1/auth/login`

**Request Body:**
```json
{
  "username": "john_doe",
  "password": "SecurePass123!"
}
```

**Response (Success - 200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNTUwZTg0MDAiLCJ1c2VybmFtZSI6ImpvaG5fZG9lIiwiZXhwIjoxNzEyNjc5MDAwfQ.signature",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "email": "john@example.com"
  }
}
```

**Response (Error - 401):**
```json
{
  "status": "error",
  "message": "Username hoặc password sai",
  "code": "INVALID_CREDENTIALS"
}
```

---

## 4. API Endpoint - Get Current User

### 4.1 Get Me

**URL:** `GET /api/v1/auth/me`

**Headers (Required):**
```
Authorization: Bearer {access_token}
```

**Response (Success - 200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "created_at": "2026-04-08T21:50:00Z"
}
```

**Response (Error - 401):**
```json
{
  "status": "error",
  "message": "Token không hợp lệ hoặc hết hạn",
  "code": "UNAUTHORIZED"
}
```

---

## 5. Cấu Trúc Database

### 5.1 Bảng Users

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(64) NOT NULL,  -- MD5 hash (32 chars) từ Driver
  is_active BOOLEAN DEFAULT TRUE,
  is_verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_login_at TIMESTAMP,
  
  CONSTRAINT username_length CHECK (LENGTH(username) >= 3),
  CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

CREATE INDEX idx_username ON users(username);
CREATE INDEX idx_email ON users(email);
```

### 5.2 Pydantic Model - User

```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID

class UserCreate(BaseModel):
    """Schema cho register"""
    username: str  # 3-50 ký tự
    email: EmailStr
    password: str  # 8+ ký tự

class UserLogin(BaseModel):
    """Schema cho login"""
    username: str
    password: str

class UserResponse(BaseModel):
    """Schema cho response"""
    id: UUID
    username: str
    email: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserInDB(BaseModel):
    """Schema cho database"""
    id: UUID
    username: str
    email: str
    password_hash: str  # Hash từ Driver
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

---

## 6. Backend Implementation

### 6.1 Crypto Bridge - Hash Password

```python
# app/core/crypto_bridge.py
import ctypes
import os
from typing import Optional

class CryptoBridge:
    """Giao tiếp với Kernel Driver để mã hóa"""
    
    def __init__(self) -> None:
        self.driver_available = False
        # Cố gắng load driver
        try:
            # Windows KMDF driver
            self.dll = ctypes.CDLL("ChatCryptoDriver.dll")
            self.driver_available = True
        except Exception:
            print("Driver không available, sử dụng mock")
    
    async def hash_password_with_driver(self, password: str) -> str:
        """
        Gửi password xuống Driver để MD5 hash
        
        Args:
            password: Password từ user
            
        Returns:
            MD5 hash (32 ký tự hex)
        """
        if self.driver_available:
            # Gọi Driver thực
            try:
                password_bytes = password.encode('utf-8')
                # Gọi IOCTL từ driver
                hash_result = self._call_driver_ioctl(password_bytes)
                return hash_result
            except Exception as e:
                print(f"Driver error: {e}, fallback to mock")
        
        # Fallback: Mock MD5 (nếu driver không available)
        return self._mock_md5_hash(password)
    
    def _mock_md5_hash(self, password: str) -> str:
        """Mock MD5 hash cho development"""
        import hashlib
        return hashlib.md5(password.encode()).hexdigest()
    
    def _call_driver_ioctl(self, data: bytes) -> str:
        """Gọi Driver via IOCTL"""
        # Implementation chi tiết tùy vào driver
        pass

crypto_bridge = CryptoBridge()
```

### 6.2 Auth Routes

```python
# app/api/v1/auth.py
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.core.crypto_bridge import crypto_bridge
from app.core.security import create_access_token
from app.database.models import User
import logging

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserCreate, db: Session) -> UserResponse:
    """
    Đăng ký user mới
    
    1. Validate dữ liệu
    2. Hash password với Driver
    3. Lưu vào Database
    4. Trả về user info
    """
    
    # 1. Check username/email đã tồn tại
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | 
        (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username hoặc email đã tồn tại"
        )
    
    # 2. Hash password với Driver
    try:
        password_hash = await crypto_bridge.hash_password_with_driver(user_data.password)
    except Exception as e:
        logger.error(f"Driver error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống"
        )
    
    # 3. Tạo user mới
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"User registered: {user_data.username}")
    
    return UserResponse.from_orm(new_user)


@router.post("/login")
async def login(login_data: UserLogin, db: Session) -> dict:
    """
    Đăng nhập user
    
    1. Kiểm tra user tồn tại
    2. Hash password với Driver
    3. So sánh hash
    4. Tạo JWT Token
    5. Trả về token
    """
    
    # 1. Tìm user
    user = db.query(User).filter(
        User.username == login_data.username
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username hoặc password sai"
        )
    
    # 2. Hash password input với Driver
    try:
        password_hash = await crypto_bridge.hash_password_with_driver(login_data.password)
    except Exception as e:
        logger.error(f"Driver error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống"
        )
    
    # 3. So sánh hash
    if password_hash != user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username hoặc password sai"
        )
    
    # 4. Tạo JWT Token
    access_token = create_access_token(
        data={"user_id": str(user.id), "username": user.username}
    )
    
    logger.info(f"User logged in: {user.username}")
    
    # 5. Trả về token
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str, db: Session) -> UserResponse:
    """
    Lấy thông tin user hiện tại
    
    Cần JWT Token trong Authorization header
    """
    user_id = verify_access_token(token)  # Decrypt JWT
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ"
        )
    
    return UserResponse.from_orm(user)
```

---

## 7. Frontend Implementation

### 7.1 AuthContext

```javascript
// src/context/AuthContext.js
import React, { createContext, useReducer, useCallback, useEffect } from 'react';

export const AuthContext = createContext();

const initialState = {
  user: null,
  token: null,
  isAuthenticated: false,
  loading: true,
  error: null,
};

const authReducer = (state, action) => {
  switch (action.type) {
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        isAuthenticated: true,
        error: null,
      };
    case 'LOGOUT':
      return initialState;
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
      };
    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };
    case 'LOAD_FROM_STORAGE':
      return action.payload;
    default:
      return state;
  }
};

export const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Tải token từ localStorage khi component mount
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const user = localStorage.getItem('user');
    
    if (token && user) {
      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: {
          token,
          user: JSON.parse(user),
        },
      });
    }
  }, []);

  const login = useCallback(async (username, password) => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = await response.json();
      
      // Lưu token vào localStorage
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      
      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: {
          token: data.access_token,
          user: data.user,
        },
      });
    } catch (error) {
      dispatch({
        type: 'SET_ERROR',
        payload: error.message,
      });
    }
  }, []);

  const register = useCallback(async (username, email, password) => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      });

      if (!response.ok) {
        throw new Error('Register failed');
      }

      return await response.json();
    } catch (error) {
      dispatch({
        type: 'SET_ERROR',
        payload: error.message,
      });
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    dispatch({ type: 'LOGOUT' });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
```

### 7.2 LoginForm Component

```javascript
// src/components/LoginForm.js
import React, { useContext, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export const LoginForm = () => {
  const { login, error } = useContext(AuthContext);
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      await login(formData.username, formData.password);
      navigate('/chat');  // Redirect sang chat
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-form">
      <h2>Đăng Nhập</h2>
      
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Username</label>
          <input
            type="text"
            name="username"
            value={formData.username}
            onChange={handleChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
          />
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Đang đăng nhập...' : 'Đăng Nhập'}
        </button>
      </form>
      
      <p>
        Chưa có tài khoản? <a href="/register">Đăng ký ngay</a>
      </p>
    </div>
  );
};
```

### 7.3 RegisterForm Component

```javascript
// src/components/RegisterForm.js
import React, { useContext, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export const RegisterForm = () => {
  const { register, error } = useContext(AuthContext);
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirm_password: '',
  });
  const [loading, setLoading] = useState(false);
  const [validationError, setValidationError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError('');
    setLoading(true);
    
    try {
      // Validate frontend
      if (formData.password !== formData.confirm_password) {
        throw new Error('Password không khớp');
      }
      
      if (formData.password.length < 8) {
        throw new Error('Password phải có ít nhất 8 ký tự');
      }
      
      // Register
      const result = await register(
        formData.username,
        formData.email,
        formData.password
      );
      
      if (result) {
        // Auto-redirect sang login hoặc auto-login
        navigate('/login');
      }
    } catch (err) {
      setValidationError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="register-form">
      <h2>Đăng Ký</h2>
      
      {error && <div className="error-message">{error}</div>}
      {validationError && <div className="error-message">{validationError}</div>}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Username</label>
          <input
            type="text"
            name="username"
            value={formData.username}
            onChange={handleChange}
            minLength="3"
            maxLength="50"
            required
          />
        </div>
        
        <div className="form-group">
          <label>Email</label>
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            minLength="8"
            required
          />
        </div>
        
        <div className="form-group">
          <label>Confirm Password</label>
          <input
            type="password"
            name="confirm_password"
            value={formData.confirm_password}
            onChange={handleChange}
            minLength="8"
            required
          />
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Đang đăng ký...' : 'Đăng Ký'}
        </button>
      </form>
      
      <p>
        Đã có tài khoản? <a href="/login">Đăng nhập ngay</a>
      </p>
    </div>
  );
};
```

---

## 8. Tóm Tắt Luồng

### Register
```
User Input → Frontend Validate → POST /api/v1/auth/register 
→ Backend Validate → Driver Hash MD5 → Save to DB → Return User
```

### Login
```
User Input → Frontend Validate → POST /api/v1/auth/login 
→ Backend Query DB → Driver Hash MD5 → Compare Hash 
→ Create JWT → Return Token → Frontend Save Token
```

### Authenticated Request
```
Frontend (with token) → POST /api/v1/auth/me 
→ Verify JWT → Return User Info
```

---

## 9. Security Checklist

- ✅ Password hashed với MD5 từ **Kernel Driver** (không user-mode)
- ✅ Hash không bao giờ trả về frontend
- ✅ JWT Token có thời hạn hết hạn (expiration)
- ✅ CORS cấu hình chặt chẽ
- ✅ HTTPS nên enable trên production
- ✅ Password requirements (8+ ký tự, complexity)
- ✅ Rate limiting trên login endpoint
- ✅ Audit logging cho auth events
