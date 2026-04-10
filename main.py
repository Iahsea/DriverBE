"""
FastAPI Application Main Entry Point

Cấu hình chính của FastAPI server bao gồm:
- CORS middleware cho frontend (React)
- Authentication routes (Register, Login, Me)
- WebSocket endpoint cho chat
- Health check endpoints
- Startup/Shutdown events
"""

# Load .env file FIRST - before other imports
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, status, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from datetime import datetime, timezone
import jwt
import json

from app.database.database import init_db, SessionLocal, engine
from app.core.crypto_bridge import crypto_bridge
from app.core.security import verify_access_token
from app.core.id_utils import normalize_uuid
from app.api.v1 import auth, rooms, friends
from app.websocket.connection_manager import connection_manager
from app.websocket.notification_manager import notification_manager
from app.database.models import User, Room, RoomMember, Message
from sqlalchemy import text

# ==================== Logging Configuration ====================

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ==================== Database Migration ====================

def run_migrations():
    """Add new columns to messages table if they don't exist"""
    try:
        with engine.begin() as connection:
            # Try to add is_read column
            try:
                connection.execute(text(
                    "ALTER TABLE messages ADD COLUMN is_read BOOLEAN DEFAULT FALSE NOT NULL"
                ))
                logger.info("✅ Added 'is_read' column to messages table")
            except Exception as e:
                if "Duplicate column" in str(e) or "already exists" in str(e):
                    logger.debug("✓ 'is_read' column already exists")
                else:
                    logger.warning(f"⚠️ Could not add is_read column: {e}")
            
            # Try to add read_at column
            try:
                connection.execute(text(
                    "ALTER TABLE messages ADD COLUMN read_at DATETIME NULL"
                ))
                logger.info("✅ Added 'read_at' column to messages table")
            except Exception as e:
                if "Duplicate column" in str(e) or "already exists" in str(e):
                    logger.debug("✓ 'read_at' column already exists")
                else:
                    logger.warning(f"⚠️ Could not add read_at column: {e}")
            
            # Try to add index
            try:
                connection.execute(text(
                    "CREATE INDEX idx_messages_is_read ON messages(is_read)"
                ))
                logger.info("✅ Created index on 'is_read' column")
            except Exception as e:
                if "Duplicate key name" in str(e) or "already exists" in str(e):
                    logger.debug("✓ Index on 'is_read' already exists")
                else:
                    logger.debug(f"Index creation note: {e}")
            
            logger.info("✨ Database migrations completed")
    except Exception as e:
        logger.warning(f"⚠️ Migration error (backend will continue): {e}")

# ==================== Startup/Shutdown Events ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager cho FastAPI.
    
    Startup: Khởi tạo database, crypto bridge
    Shutdown: Cleanup resources
    """
    # === STARTUP ===
    logger.info("🚀 FastAPI Application Starting...")
    
    try:
        # Initialize database (create tables if not exist)
        init_db()
        logger.info("✓ Database initialized")
        
        # Run migrations
        run_migrations()
        
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
    
    logger.info("✓ Application ready to handle requests")
    
    yield  # Application running...
    
    # === SHUTDOWN ===
    logger.info("🛑 FastAPI Application Shutting Down...")
    
    try:
        crypto_bridge.shutdown()
        logger.info("✓ Crypto bridge cleanup completed")
    except Exception as e:
        logger.warning(f"Crypto bridge shutdown error: {e}")
    
    logger.info("✓ Application shutdown complete")


# ==================== FastAPI App Initialization ====================

app = FastAPI(
    title="Secure Chat System API",
    description="Backend API for secure chat with Kernel Driver based encryption",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ==================== CORS Middleware ====================

# Load CORS origins from .env file or use default
CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173")
ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_STR.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

logger.info(f"✓ CORS configured for origins: {ALLOWED_ORIGINS}")

# ==================== Include Routers ====================

# Auth routes: /api/v1/auth/*
app.include_router(
    auth.router,
    prefix="/api/v1",
)

# Rooms routes: /api/v1/rooms/*
app.include_router(
    rooms.router,
    prefix="/api/v1",
)

# Friends routes: /api/v1/friends/*
app.include_router(
    friends.router,
    prefix="/api/v1",
)

logger.info("✓ Auth routes registered at /api/v1/auth")
logger.info("✓ Rooms routes registered at /api/v1/rooms")
logger.info("✓ Friends routes registered at /api/v1/friends")

# ==================== Health Check Endpoints ====================

@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Root endpoint",
    tags=["Health"],
)
async def root():
    """Root endpoint - API is running."""
    return {
        "message": "Secure Chat System API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/api/docs",
    }


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    tags=["Health"],
)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Server is running",
    }


@app.get(
    "/api/v1/ping",
    status_code=status.HTTP_200_OK,
    summary="API ping",
    tags=["Health"],
)
async def ping():
    """API ping endpoint."""
    return {
        "message": "pong",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ==================== WebSocket Endpoint ====================

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"


@app.websocket("/ws/chat/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, token: str = Query(...)):
    """
    WebSocket endpoint cho group chat (per-room).
    
    Features:
    - Per-room connection management
    - JWT token authentication
    - Member verification
    - Message persistence to database
    - Per-room broadcasting
    
    Usage:
    ws://localhost:8000/ws/chat/{room_id}?token={JWT_TOKEN}
    
    Message format:
    {
        "content": "message text"
    }
    """
    
    try:
        # ===== 1. Verify JWT token =====
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("user_id")
            username = payload.get("username")
            
            if not user_id:
                await websocket.close(code=4001, reason="Invalid token: no user_id")
                logger.warning(f"WebSocket connection rejected: no user_id in token")
                return
        except jwt.ExpiredSignatureError:
            await websocket.close(code=4002, reason="Token expired")
            logger.warning(f"WebSocket connection rejected: token expired")
            return
        except jwt.InvalidTokenError as e:
            await websocket.close(code=4003, reason="Invalid token")
            logger.warning(f"WebSocket connection rejected: invalid token - {e}")
            return
        
        # ===== 2. Verify user exists and room exists =====
        db = SessionLocal()
        try:
            user_id_norm = normalize_uuid(user_id)
            user = db.query(User).filter(User.id == user_id_norm).first()
            if not user:
                await websocket.close(code=4004, reason="User not found")
                logger.warning(f"WebSocket rejected: user {user_id} not found")
                return
            
            room_id_norm = normalize_uuid(room_id)
            room = db.query(Room).filter(Room.id == room_id_norm).first()
            if not room:
                await websocket.close(code=4005, reason="Room not found")
                logger.warning(f"WebSocket rejected: room {room_id} not found")
                return
            
            # ===== 3. Verify user is member of room =====
            member = db.query(RoomMember).filter(
                (RoomMember.room_id == room_id_norm) & 
                (RoomMember.user_id == user_id_norm)
            ).first()
            
            if not member:
                await websocket.close(code=4006, reason="Not a member of this room")
                logger.warning(f"WebSocket rejected: user {user_id} is not member of room {room_id}")
                return
            
            # ===== 4. Accept connection =====
            await connection_manager.connect(room_id_norm, user_id_norm, websocket)
            logger.info(f"[CONNECT] User {user_id_norm[:8]}... vào room {room_id_norm[:8]}... ({connection_manager.get_room_member_count(room_id_norm)} members)")
            
            # ===== 5. Connection accepted =====
            member_count = connection_manager.get_room_member_count(room_id_norm)
            logger.info(f"[WS] User {user_id[:8]}... connected to room {room_id[:8]}... ({member_count} members)")
            
            # ===== 6. Handle incoming messages =====
            while True:
                # Receive message from client
                data_raw = await websocket.receive_text()
                
                try:
                    data = json.loads(data_raw)
                    content = data.get("content", "").strip()
                    content_encrypted = data.get("content_encrypted", "").strip()
                    
                    if not content and not content_encrypted:
                        continue

                    if content_encrypted:
                        try:
                            content = await crypto_bridge.decrypt_message_payload(content_encrypted)
                        except Exception as e:
                            logger.error(f"Decrypt incoming message failed: {e}")
                            await connection_manager.send_personal_message(
                                room_id_norm,
                                user_id_norm,
                                {
                                    "type": "error",
                                    "content": "Decrypt failed on server",
                                },
                            )
                            continue
                    else:
                        try:
                            content_encrypted = await crypto_bridge.encrypt_message_payload(content)
                        except Exception as e:
                            logger.error(f"Encrypt outgoing message failed: {e}")
                            await connection_manager.send_personal_message(
                                room_id_norm,
                                user_id_norm,
                                {
                                    "type": "error",
                                    "content": "Encrypt failed on server",
                                },
                            )
                            continue
                    
                    # ===== 7. Save message to database =====
                    message = Message(
                        id=None,  # Auto-generate UUID
                        room_id=room_id_norm,
                        sender_id=user_id_norm,
                        content=content,
                        content_encrypted=content_encrypted,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    
                    db.add(message)
                    db.commit()
                    db.refresh(message)
                    
                    # ===== 8. Broadcast message to room members =====
                    await connection_manager.broadcast_to_room(room_id_norm, {
                        "type": "message",
                        "id": message.id,
                        "room_id": room_id_norm,
                        "sender_id": user_id_norm,
                        "sender_name": user.username,
                        "content": content,
                        "content_encrypted": message.content_encrypted,
                        "created_at": message.created_at.isoformat(),
                        "updated_at": message.updated_at.isoformat(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    
                    logger.debug(f"[MSG] {user.username} → room {room_id_norm[:8]}...: {content[:50]}")
                
                except json.JSONDecodeError:
                    logger.warning(f"Invalid message format from {user_id}")
                    continue
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error processing message: {e}")
                    continue
        
        finally:
            db.close()
    
    except WebSocketDisconnect:
        db = SessionLocal()
        try:
            user_id_norm = normalize_uuid(user_id) if user_id else None
            user = db.query(User).filter(User.id == user_id_norm).first() if user_id_norm else None
            username = user.username if user else (user_id_norm[:8] if user_id_norm else "unknown")
            
            # Disconnect from connection manager
            room_id_norm = normalize_uuid(room_id)
            connection_manager.disconnect(room_id_norm, user_id_norm)
            
            member_count = connection_manager.get_room_member_count(room_id_norm)
            
            # Broadcast system message: user left (group only)
            if member_count > 0 and room.is_group:
                await connection_manager.broadcast_to_room(room_id_norm, {
                    "type": "system",
                    "content": f"👋 {username} đã rời phòng",
                    "user_id": user_id_norm,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            
            logger.info(f"[DISCONNECT] User {user_id_norm[:8]}... rời room {room_id_norm[:8]}... ({member_count} members còn lại)")
            logger.info(f"[WS] User {user_id_norm[:8]}... disconnected from room {room_id_norm[:8]}... ({member_count} members left)")
        
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id} in room {room_id}: {e}")
        try:
            if user_id and room_id:
                connection_manager.disconnect(normalize_uuid(room_id), normalize_uuid(user_id))
        except:
            pass


# ==================== WebSocket /ws/notifications ====================

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket endpoint cho real-time notifications (friend requests, accepted, rejected, ...).
    
    Features:
    - JWT token authentication via query params
    - Real-time friend notifications
    - Per-user connection management
    - Automatic cleanup on disconnect
    
    Usage:
    ws://localhost:8000/ws/notifications?token={JWT_TOKEN}
    
    Notification format:
    {
        "type": "friend_request|friend_request_accepted|friend_request_rejected|friend_request_canceled|friend_deleted",
        "from_user_id": "...",
        "from_username": "...",
        "user_id": "...",
        "username": "...",
        "request_id": "...",
        "message": "...",
        "timestamp": "2026-04-09T10:30:00"
    }
    """
    
    user_id = None
    
    try:
        # ===== 1. Lấy token từ query params =====
        query_params = dict(
            param.split("=") for param in websocket.scope.get("query_string", b"").decode().split("&") 
            if "=" in param
        )
        token = query_params.get("token", "").replace("Bearer ", "")
        
        if not token:
            await websocket.close(code=4001, reason="Token required")
            logger.warning("Notification WebSocket rejected: no token provided")
            return
        
        # ===== 2. Verify JWT token =====
        try:
            payload = verify_access_token(token)
            user_id = payload.get("user_id")
            
            if not user_id:
                await websocket.close(code=4001, reason="Invalid token: no user_id")
                logger.warning("Notification WebSocket rejected: no user_id in token")
                return
        except Exception as e:
            logger.warning(f"Notification WebSocket rejected: invalid token - {e}")
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # ===== 3. Verify user exists =====
        db = SessionLocal()
        try:
            user_id_norm = normalize_uuid(user_id)
            user = db.query(User).filter(User.id == user_id_norm).first()
            if not user:
                await websocket.close(code=4004, reason="User not found")
                logger.warning(f"Notification WebSocket rejected: user {user_id} not found")
                return
        finally:
            db.close()
        
        # ===== 4. Connect user tới notification manager =====
        await notification_manager.connect(user_id_norm, websocket)
        logger.info(f"✓ Notification WebSocket connected for user {user_id_norm[:8]}...")
        
        # ===== 5. Keep connection alive (ping/pong) =====
        while True:
            data = await websocket.receive_text()
            
            # Handle ping/pong để giữ connection sống
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "pong":
                # Ignore pong
                pass
            else:
                logger.debug(f"Received from {user_id[:8]}...: {data}")
    
    except WebSocketDisconnect:
        if user_id:
            user_id_norm = normalize_uuid(user_id)
            notification_manager.disconnect(user_id_norm)
            logger.info(f"✓ Notification WebSocket disconnected for user {user_id_norm[:8]}...")
    
    except Exception as e:
        logger.error(f"Notification WebSocket error for user {user_id}: {e}")
        if user_id:
            notification_manager.disconnect(normalize_uuid(user_id))


# ==================== Error Handlers ====================