"""
Pydantic Schemas for Message Management

Define request/response models cho message endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class MessageCreate(BaseModel):
    """Schema cho POST /api/v1/rooms/{id}/messages - Gửi tin nhắn"""
    content: str = Field(..., min_length=1, max_length=10000, description="Nội dung tin nhắn")
    content_encrypted: Optional[str] = Field(None, description="Nội dung mã hóa (nếu có)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Hello everyone!",
                "content_encrypted": None,
            }
        }


class MessageResponse(BaseModel):
    """Schema cho GET /api/v1/rooms/{id}/messages - Lấy tin nhắn"""
    id: str = Field(..., description="Message ID (UUID)")
    room_id: str = Field(..., description="Room ID")
    sender_id: str = Field(..., description="Sender User ID")
    sender_name: Optional[str] = Field(None, description="Tên người gửi (optional)")
    content: str = Field(..., description="Nội dung tin nhắn")
    content_encrypted: Optional[str] = Field(None, description="Nội dung mã hóa")
    is_read: bool = Field(False, description="Tin nhắn đã được đọc hay chưa")
    read_at: Optional[datetime] = Field(None, description="Thời gian đọc tin nhắn")
    created_at: datetime = Field(..., description="Thời gian gửi")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "acdc9190c2d54b0ba3680b0ebade65f6",
                "room_id": "550e8400e29b41d4a716446655440000",
                "sender_id": "550e8400e29b41d4a716446655440001",
                "sender_name": "john_doe",
                "content": "Hello everyone!",
                "content_encrypted": None,
                "is_read": True,
                "read_at": "2026-04-09T00:05:00",
                "created_at": "2026-04-09T00:00:00",
                "updated_at": "2026-04-09T00:05:00",
            }
        }


class MessageListResponse(BaseModel):
    """Schema cho danh sách tin nhắn"""
    total: int = Field(..., description="Tổng số tin nhắn")
    messages: list[MessageResponse] = Field(..., description="List tin nhắn")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 10,
                "messages": [
                    {
                        "id": "acdc9190c2d54b0ba3680b0ebade65f6",
                        "room_id": "550e8400e29b41d4a716446655440000",
                        "sender_id": "550e8400e29b41d4a716446655440001",
                        "sender_name": "john_doe",
                        "content": "Hello everyone!",
                        "content_encrypted": None,
                        "created_at": "2026-04-09T00:00:00",
                        "updated_at": "2026-04-09T00:00:00",
                    }
                ],
            }
        }


class WebSocketMessage(BaseModel):
    """Schema cho WebSocket message (tới `/ws/chat/{room_id}`)"""
    type: str = Field(..., description="message, system, typing, etc")
    content: str = Field(..., description="Nội dung")
    sender_id: Optional[str] = Field(None, description="Sender ID (từ server gửi lại)")
    sender_name: Optional[str] = Field(None, description="Sender name (từ server gửi lại)")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "message",
                "content": "Hello everyone!",
                "sender_id": "550e8400e29b41d4a716446655440001",
                "sender_name": "john_doe",
                "timestamp": "2026-04-09T00:00:00Z",
            }
        }
