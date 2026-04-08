"""
Pydantic Schemas for Room (Group Chat) Management

Define request/response models cho room endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class RoomCreate(BaseModel):
    """Schema cho POST /api/v1/rooms - Tạo phòng chat mới"""
    name: str = Field(..., min_length=1, max_length=255, description="Tên phòng")
    description: Optional[str] = Field(None, max_length=1000, description="Mô tả phòng")
    is_group: bool = Field(default=False, description="0: 1-to-1, 1: Group Chat")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Dev Team Chat",
                "description": "Nhóm chat của dev team",
                "is_group": True,
            }
        }


class RoomMemberResponse(BaseModel):
    """Schema cho room member"""
    id: str = Field(..., description="Member ID (UUID)")
    room_id: str = Field(..., description="Room ID (UUID)")
    user_id: str = Field(..., description="User ID (UUID)")
    role: str = Field(..., description="admin, moderator, member")
    joined_at: datetime = Field(..., description="Thời gian tham gia")
    
    class Config:
        from_attributes = True


class RoomResponse(BaseModel):
    """Schema cho GET /api/v1/rooms/{id} - Lấy chi tiết phòng"""
    id: str = Field(..., description="Room ID (UUID)")
    name: str = Field(..., description="Tên phòng")
    description: Optional[str] = Field(None, description="Mô tả phòng")
    is_group: bool = Field(..., description="0: 1-to-1, 1: Group Chat")
    created_by_id: str = Field(..., description="User ID của người tạo")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")
    member_count: Optional[int] = Field(None, description="Số lượng thành viên")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "acdc9190c2d54b0ba3680b0ebade65f6",
                "name": "Dev Team Chat",
                "description": "Nhóm chat của dev team",
                "is_group": True,
                "created_by_id": "550e8400e29b41d4a716446655440000",
                "created_at": "2026-04-09T00:00:00",
                "updated_at": "2026-04-09T00:00:00",
                "member_count": 5,
            }
        }


class RoomListResponse(BaseModel):
    """Schema cho GET /api/v1/rooms - Lấy danh sách phòng"""
    id: str
    name: str
    is_group: bool
    member_count: Optional[int] = None
    last_message_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class RoomMemberAddRequest(BaseModel):
    """Schema cho POST /api/v1/rooms/{id}/members - Thêm thành viên"""
    user_id: str = Field(..., description="User ID cần thêm vào phòng")
    role: str = Field(default="member", description="admin, moderator, member")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400e29b41d4a716446655440000",
                "role": "member",
            }
        }


class RoomMemberDetailResponse(BaseModel):
    """Schema cho member detail (kèm user info)"""
    id: str
    room_id: str
    user_id: str
    username: str
    email: str
    role: str
    joined_at: datetime
    
    class Config:
        from_attributes = True
