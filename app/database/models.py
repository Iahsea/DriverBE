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
    friend_requests_sent = relationship("FriendRequest", back_populates="from_user", foreign_keys="FriendRequest.from_user_id", cascade="all, delete-orphan")
    friend_requests_received = relationship("FriendRequest", back_populates="to_user", foreign_keys="FriendRequest.to_user_id", cascade="all, delete-orphan")
    friendships_1 = relationship("Friendship", back_populates="user_1", foreign_keys="Friendship.user_id_1", cascade="all, delete-orphan")
    friendships_2 = relationship("Friendship", back_populates="user_2", foreign_keys="Friendship.user_id_2", cascade="all, delete-orphan")

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
    
    Backend Driver Encryption Flow:
    1. Client1 gửi plaintext message
    2. Backend nhận và gọi Kernel Driver encrypt (AES-256-CBC)
    3. Backend lưu BOTH plaintext + encrypted vào database
    4. Backend broadcast encrypted message tới room members
    5. Client2 nhận encrypted, giải mã via Web Crypto API, hiển thị plaintext
    
    Attributes:
        id: UUID primary key
        room_id: UUID của phòng
        sender_id: UUID của người gửi
        content: Nội dung tin nhắn (plaintext - for display/logging)
        content_encrypted: Nội dung mã hóa (AES-256-CBC via Kernel Driver)
        message_hash: MD5 hash của plaintext (32 hex chars) - integrity verification via Kernel Driver
        is_read: Tin nhắn đã được đọc hay chưa
        read_at: Thời gian đọc tin nhắn
        created_at: Thời gian gửi
        updated_at: Thời gian cập nhật
    """
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex, nullable=False)
    room_id = Column(String(36), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Plaintext message (for display/broadcast)
    content_encrypted = Column(Text, nullable=False)  # AES-256-CBC encrypted via Kernel Driver
    message_hash = Column(String(64), nullable=True)  # MD5 hash (32 hex chars) - integrity verification via Driver
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
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


class FriendRequest(Base):
    """
    FriendRequest Model - Quản lý lời mời kết bạn.
    
    Attributes:
        id: UUID primary key
        from_user_id: ID của user gửi lời mời
        to_user_id: ID của user nhận lời mời
        status: pending, accepted, rejected, canceled
        created_at: Thời gian gửi lời mời
        updated_at: Thời gian cập nhật
    """
    __tablename__ = "friend_requests"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex, nullable=False)
    from_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    to_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, accepted, rejected, canceled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    from_user = relationship("User", back_populates="friend_requests_sent", foreign_keys=[from_user_id])
    to_user = relationship("User", back_populates="friend_requests_received", foreign_keys=[to_user_id])

    def __repr__(self) -> str:
        return f"<FriendRequest(from={self.from_user_id[:8]}, to={self.to_user_id[:8]}, status={self.status})>"


class Friendship(Base):
    """
    Friendship Model - Các cặp bạn bè đã chấp nhận lời mời.
    
    Note: user_id_1 < user_id_2 để tránh duplicates (A-B == B-A).
    
    Attributes:
        id: UUID primary key
        user_id_1: ID user 1 (nhỏ hơn user_id_2)
        user_id_2: ID user 2 (lớn hơn user_id_1)
        created_at: Thời gian trở thành bạn
    """
    __tablename__ = "friendships"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex, nullable=False)
    user_id_1 = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user_1 = relationship("User", back_populates="friendships_1", foreign_keys=[user_id_1])
    user_2 = relationship("User", back_populates="friendships_2", foreign_keys=[user_id_2])

    def __repr__(self) -> str:
        return f"<Friendship(user1={self.user_id_1[:8]}, user2={self.user_id_2[:8]})>"
