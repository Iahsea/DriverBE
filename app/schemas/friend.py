"""
Pydantic Schemas for Friendship Features

Define request/response models cho friendship endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class FriendRequestCreate(BaseModel):
    """Schema cho POST /api/v1/friends/request - Gửi lời mời kết bạn"""
    to_user_id: str = Field(..., description="ID của user nhận lời mời")
    
    class Config:
        json_schema_extra = {
            "example": {
                "to_user_id": "5cc8d655...",
            }
        }


class FriendRequestResponse(BaseModel):
    """Schema cho Friend Request response"""
    id: str = Field(..., description="Request ID (UUID)")
    from_user_id: str = Field(..., description="User ID người gửi")
    from_username: str = Field(..., description="Username của người gửi")
    to_user_id: str = Field(..., description="User ID người nhận")
    to_username: str = Field(..., description="Username của người nhận")
    status: str = Field(..., description="pending, accepted, rejected, canceled")
    created_at: datetime = Field(..., description="Thời gian gửi lời mời")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")
    
    class Config:
        from_attributes = True


class FriendshipResponse(BaseModel):
    """Schema cho Friendship record"""
    id: str = Field(..., description="Friendship ID (UUID)")
    user_id_1: str = Field(..., description="User ID 1")
    user_1_username: str = Field(..., description="Username của user 1")
    user_id_2: str = Field(..., description="User ID 2")
    user_2_username: str = Field(..., description="Username của user 2")
    created_at: datetime = Field(..., description="Thời gian trở thành bạn")
    
    class Config:
        from_attributes = True


class FriendResponse(BaseModel):
    """Schema cho friend info (trong list friends)"""
    id: str = Field(..., description="User ID (UUID)")
    username: str = Field(..., description="Tên đăng nhập")
    email: str = Field(..., description="Email")
    created_at: datetime = Field(..., description="Thời gian user được tạo")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "5cc8d655...",
                "username": "john_doe",
                "email": "john@example.com",
                "created_at": "2026-04-09T00:00:00",
            }
        }


class FriendRequestListResponse(BaseModel):
    """Schema cho GET /api/v1/friends/requests"""
    total: int = Field(..., description="Tổng số lối mời")
    requests: List[FriendRequestResponse] = Field(..., description="Danh sách lời mời")


class FriendListResponse(BaseModel):
    """Schema cho GET /api/v1/friends"""
    total: int = Field(..., description="Tổng số bạn bè")
    friends: List[FriendResponse] = Field(..., description="Danh sách bạn bè")


class FriendSearchResponse(BaseModel):
    """Schema cho search user (name/email)"""
    id: str = Field(..., description="User ID (UUID)")
    username: str = Field(..., description="Tên đăng nhập")
    email: str = Field(..., description="Email")
    mutual_count: int = Field(0, description="Số bạn chung")

    class Config:
        from_attributes = True


class FriendSearchListResponse(BaseModel):
    """Schema cho GET /api/v1/friends/search"""
    total: int = Field(..., description="Tổng số kết quả")
    results: List[FriendSearchResponse] = Field(..., description="Danh sách user")


class FriendSuggestionListResponse(BaseModel):
    """Schema cho GET /api/v1/friends/suggestions"""
    total: int = Field(..., description="Tổng số gợi ý")
    suggestions: List[FriendSearchResponse] = Field(..., description="Danh sách user gợi ý")
