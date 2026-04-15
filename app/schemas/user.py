"""
Pydantic Schemas for User Authentication

Define request/response models cho FastAPI endpoints.
Tự động validation và serialization/deserialization.
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


class UserCreate(BaseModel):
    """Schema cho POST /register"""
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 chars)")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password (8+ chars)")
    
    class Config:
        """Pydantic config"""
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "SecurePass123!",
            }
        }


class UserLogin(BaseModel):
    """Schema cho POST /login"""
    username: str = Field(..., min_length=1, description="Username or email")
    password: str = Field(..., min_length=1, description="Password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "SecurePass123!",
            }
        }


class UserResponse(BaseModel):
    """Schema cho user response (safe, không có password hash)"""
    id: UUID
    username: str
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    is_friend: bool = False  # Có là bạn không
    is_pending: bool = False  # Có pending request không
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "john_doe",
                "email": "john@example.com",
                "is_active": True,
                "is_verified": False,
                "created_at": "2026-04-08T21:50:00Z",
                "is_friend": False,
                "is_pending": False,
            }
        }


class LoginResponse(BaseModel):
    """Schema cho /login response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "username": "john_doe",
                    "email": "john@example.com",
                    "is_active": True,
                    "is_verified": False,
                    "created_at": "2026-04-08T21:50:00Z",
                },
            }
        }


class TokenPayload(BaseModel):
    """JWT payload structure"""
    user_id: str
    username: str
    exp: Optional[int] = None  # Expiration timestamp
