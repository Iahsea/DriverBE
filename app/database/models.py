"""
SQLAlchemy Models for Secure Chat Database

Define database tables structure using SQLAlchemy ORM.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database.database import Base
from datetime import datetime
import uuid


class User(Base):
    """
    User Model - Bảng users trong database.
    
    Attributes:
        id: UUID string (36 chars) primary key - consistent with Room/RoomMember
        username: Tên đăng nhập duy nhất (3-50 ký tự)
        email: Email duy nhất
        password_hash: MD5 hash từ Kernel Driver (32 chars)
        is_active: Tài khoản hoạt động hay không
        is_verified: Email đã xác minh hay không
        created_at: Thời gian tạo tài khoản
        updated_at: Thời gian cập nhật lần cuối
        last_login_at: Lần đăng nhập gần nhất
    """
    __tablename__ = "users"

    # Primary Key - Use String(36) like other models for consistency
    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex, nullable=False)

    # User Info
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(64), nullable=False)  # MD5 hash (32 hex chars)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    rooms = relationship("Room", back_populates="created_by_user", foreign_keys="Room.created_by_id")
    room_members = relationship("RoomMember", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="sender", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Room(Base):
    """
    Room Model - Bảng rooms (phòng chat group hoặc 1-to-1).
    
    Attributes:
        id: UUID primary key
        name: Tên phòng (255 ký tự)
        description: Mô tả phòng
        is_group: 0 = 1-to-1 chat, 1 = Group chat
        created_by_id: UUID của user tạo phòng
        created_at: Thời gian tạo
        updated_at: Thời gian cập nhật
    """
    __tablename__ = "rooms"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_group = Column(Boolean, default=False, nullable=False, index=True)  # 0: 1-to-1, 1: Group
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    created_by_user = relationship("User", back_populates="rooms", foreign_keys=[created_by_id])
    members = relationship("RoomMember", back_populates="room", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="room", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Room(id={self.id}, name='{self.name}', is_group={self.is_group})>"


class RoomMember(Base):
    """
    RoomMember Model - Bảng room_members (quản lý thành viên phòng).
    
    Attributes:
        id: UUID primary key
        room_id: UUID của phòng
        user_id: UUID của user
        role: admin, moderator, member
        joined_at: Thời gian tham gia
    """
    __tablename__ = "room_members"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex, nullable=False)
    room_id = Column(String(36), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), default="member", nullable=False)  # admin, moderator, member
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    room = relationship("Room", back_populates="members")
    user = relationship("User", back_populates="room_members")

    def __repr__(self) -> str:
        return f"<RoomMember(room={self.room_id[:8]}, user={self.user_id[:8]}, role={self.role})>"


class Message(Base):
    """
    Message Model - Bảng messages (tin nhắn trong phòng).
    
    Attributes:
        id: UUID primary key
        room_id: UUID của phòng
        sender_id: UUID của người gửi
        content: Nội dung tin nhắn (plaintext)
        content_encrypted: Nội dung mã hóa (AES)
        created_at: Thời gian gửi
        updated_at: Thời gian cập nhật
    """
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex, nullable=False)
    room_id = Column(String(36), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    content_encrypted = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    room = relationship("Room", back_populates="messages")
    sender = relationship("User", back_populates="messages")

    # Create composite index for efficient message history queries
    __table_args__ = (
        # Index on (room_id, created_at) for efficient message history queries
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id[:8]}, room={self.room_id[:8]}, sender={self.sender_id[:8]})>"
