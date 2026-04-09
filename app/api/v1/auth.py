"""
Authentication API Routes

Endpoints:
- POST /api/v1/auth/register - Đăng ký user mới
- POST /api/v1/auth/login - Đăng nhập
- GET /api/v1/auth/me - Lấy thông tin user hiện tại
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    LoginResponse,
    TokenPayload,
)
from app.core.crypto_bridge import crypto_bridge
from app.core.security import create_access_token, verify_access_token, get_token_from_header
from app.core.id_utils import normalize_uuid
from app.database.models import User
from app.database.database import get_db
from datetime import datetime
import logging

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

# ==================== Register Endpoint ====================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký user mới",
    description="""
    Quy trình đăng ký:
    1. Validate dữ liệu (username, email, password)
    2. Kiểm tra username/email chưa tồn tại
    3. Gửi password xuống Kernel Driver để MD5 hash
    4. Lưu user mới vào database
    5. Trả về user info
    
    🔐 Password được hash bởi Kernel Driver, không lưu plain text.
    """,
)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Đăng ký user mới.
    
    Args:
        user_data: UserCreate schema với username, email, password
        db: Database session (tự động inject bởi FastAPI)
    
    Returns:
        UserResponse với user info (không bao gồm password_hash)
    
    Raises:
        400: Username/email đã tồn tại, password format sai
        500: Lỗi Driver hoặc database
    
    Example:
        POST /api/v1/auth/register
        {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "SecurePass123!"
        }
        
        Response: {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "username": "john_doe",
            ...
        }
    """
    try:
        # 1. Kiểm tra username/email chưa tồn tại
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            logger.warning(f"Register failed: username/email already exists ({user_data.username})")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username hoặc email đã tồn tại",
            )
        
        # 2. Gửi password xuống Driver để hash
        try:
            password_hash = await crypto_bridge.hash_password_with_driver(user_data.password)
            logger.debug(f"Password hashed successfully (hash: {password_hash[:8]}...)")
        except Exception as e:
            logger.error(f"Crypto bridge error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi hệ thống (hashing failed)",
            )
        
        # 3. Tạo user mới
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            is_active=True,
            is_verified=False,
        )
        
        # 4. Lưu vào database
        try:
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            logger.info(f"✓ User registered: {user_data.username} (ID: {new_user.id})")
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username hoặc email đã tồn tại",
            )
        
        # 5. Trả về user info
        return UserResponse.from_orm(new_user)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in register: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== Login Endpoint ====================

@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Đăng nhập",
    description="""
    Quy trình đăng nhập:
    1. Kiểm tra user tồn tại
    2. Hash password input với Driver
    3. So sánh hash với database
    4. Nếu khớp: Tạo JWT Token
    5. Trả về token + user info
    
    🔐 Password được hash bởi Driver để so sánh an toàn.
    """,
)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """
    Đăng nhập user.
    
    Args:
        login_data: UserLogin schema với username, password
        db: Database session
    
    Returns:
        LoginResponse với JWT access_token và user info
    
    Raises:
        401: Username hoặc password sai
        500: Lỗi Driver
    
    Example:
        POST /api/v1/auth/login
        {
            "username": "john_doe",
            "password": "SecurePass123!"
        }
        
        Response: {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user": {...}
        }
    """
    try:
        # 1. Tìm user trong database
        user = db.query(User).filter(User.username == login_data.username).first()
        
        if not user:
            logger.warning(f"Login failed: user not found ({login_data.username})")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username hoặc password sai",
            )
        
        # 2. Hash password input với Driver
        try:
            password_hash = await crypto_bridge.hash_password_with_driver(login_data.password)
        except Exception as e:
            logger.error(f"Crypto bridge error during login: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi hệ thống (hashing failed)",
            )
        
        # 3. So sánh hash
        if password_hash != user.password_hash:
            logger.warning(f"Login failed: invalid password ({login_data.username})")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username hoặc password sai",
            )
        
        # 4. Tạo JWT Token
        try:
            access_token = create_access_token(
                data={"user_id": str(user.id), "username": user.username}
            )
        except Exception as e:
            logger.error(f"Token creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi tạo token",
            )
        
        # 5. Update last_login_at
        try:
            user.last_login_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to update last_login_at: {e}")
        
        logger.info(f"✓ User logged in: {user.username} (ID: {user.id})")
        
        # Trả về response
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.from_orm(user),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== Get Current User Endpoint ====================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin user hiện tại",
    description="""
    Lấy thông tin user dựa trên JWT Token.
    
    Cần Authorization header: Bearer {token}
    """,
)
async def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Lấy thông tin user hiện tại.
    
    Args:
        authorization: Authorization header (format: "Bearer {token}")
        db: Database session
    
    Returns:
        UserResponse với user info
    
    Raises:
        401: Token không hợp lệ hoặc hết hạn
        404: User không tìm thấy
    
    Example:
        GET /api/v1/auth/me
        Headers: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        
        Response: {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "username": "john_doe",
            ...
        }
    """
    try:
        # 1. Extract token từ header
        token = get_token_from_header(authorization)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 2. Verify JWT token
        try:
            payload = verify_access_token(token)
            user_id_str = payload.get("user_id")
            if not user_id_str:
                raise ValueError("Invalid token payload")
            user_id = normalize_uuid(user_id_str)
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 3. Tìm user trong database
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User không tìm thấy",
            )
        
        logger.debug(f"Retrieved user info: {user.username}")
        return UserResponse.from_orm(user)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )
