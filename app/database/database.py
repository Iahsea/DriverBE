"""
Database Configuration and Connection Management

Cấu hình SQLAlchemy ORM để kết nối MySQL.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from typing import Generator

# Base class cho tất cả models
Base = declarative_base()

# Cấu hình database URL
# Default: MySQL connection
# Format: mysql+pymysql://user:password@localhost:3306/database_name
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:@localhost:3306/secure_chat"
)

# Tạo engine
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "False").lower() == "true",
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,  # Test connection trước khi sử dụng
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """
    Dependency injection cho FastAPI routes.
    Trả về database session cho mỗi request.
    
    Usage:
        @app.get("/users/{user_id}")
        async def get_user(user_id: int, db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Tạo tất cả tables trong database.
    Chạy một lần khi application startup.
    """
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """
    Xóa tất cả tables (chỉ dùng cho testing).
    """
    Base.metadata.drop_all(bind=engine)
