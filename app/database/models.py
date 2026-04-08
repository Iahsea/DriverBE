"""
SQLAlchemy Models for Secure Chat Database

Define database tables structure using SQLAlchemy ORM.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from app.database.database import Base
from datetime import datetime
import uuid


class User(Base):
    """
    User Model - Bảng users trong database.
    
    Attributes:
        id: UUID primary key
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

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

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
