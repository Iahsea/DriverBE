"""
Security Utilities: JWT Token Creation and Verification

Xử lý JWT token cho xác thực stateless.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import jwt
import os
from fastapi import HTTPException, status

# Cấu hình JWT
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Tạo JWT access token.
    
    Args:
        data: Dictionary chứa claims (ví dụ: {"user_id": "...", "username": "..."})
        expires_delta: Quãng thời gian hết hạn (mặc định: ACCESS_TOKEN_EXPIRE_MINUTES)
    
    Returns:
        JWT token string
    
    Example:
        token = create_access_token(
            data={"user_id": "550e8400", "username": "john_doe"}
        )
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Encode JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Dict:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string từ Authorization header
    
    Returns:
        Payload dictionary (claims)
    
    Raises:
        HTTPException: Nếu token không hợp lệ hoặc hết hạn
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token đã hết hạn",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
        )


def get_token_from_header(auth_header: Optional[str]) -> Optional[str]:
    """
    Extract token từ Authorization header.
    
    Format: "Bearer {token}"
    
    Args:
        auth_header: Authorization header value
    
    Returns:
        Token string hoặc None nếu header không hợp lệ
    """
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]
