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
import asyncio
import urllib.parse

from app.database.database import init_db, SessionLocal, engine
from app.core.crypto_bridge import crypto_bridge
from app.core.security import verify_access_token
from app.core.id_utils import normalize_uuid
from app.api.v1 import auth, rooms, friends, messages
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

# Messages routes: /api/v1/messages/*
app.include_router(
    messages.router,
    prefix="/api/v1",
)

logger.info("✓ Auth routes registered at /api/v1/auth")
logger.info("✓ Rooms routes registered at /api/v1/rooms")
logger.info("✓ Friends routes registered at /api/v1/friends")
logger.info("✓ Messages routes registered at /api/v1/messages")

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
    
    user_id = None
    user_id_norm = None
    room_id_norm = None
    username = None
    room_is_group = False

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
        
        # ===== 2. Verify user exists and room exists (SHORT-LIVED DB SESSION) =====
        user_id_norm = normalize_uuid(user_id)
        room_id_norm = normalize_uuid(room_id)

        db_init = SessionLocal()
        try:
            user = db_init.query(User).filter(User.id == user_id_norm).first()
            if not user:
                await websocket.close(code=4004, reason="User not found")
                logger.warning(f"WebSocket rejected: user {user_id} not found")
                return

            # Prefer username from DB to avoid stale token payload
            username = user.username

            room = db_init.query(Room).filter(Room.id == room_id_norm).first()
            if not room:
                await websocket.close(code=4005, reason="Room not found")
                logger.warning(f"WebSocket rejected: room {room_id} not found")
                return

            room_is_group = bool(room.is_group)

            # ===== 3. Verify user is member of room =====
            member = db_init.query(RoomMember).filter(
                (RoomMember.room_id == room_id_norm)
                & (RoomMember.user_id == user_id_norm)
            ).first()

            if not member:
                await websocket.close(code=4006, reason="Not a member of this room")
                logger.warning(
                    f"WebSocket rejected: user {user_id} is not member of room {room_id}"
                )
                return
        finally:
            db_init.close()

        # ===== 4. Accept connection =====
        await connection_manager.connect(room_id_norm, user_id_norm, websocket)
        logger.info(
            f"[CONNECT] User {user_id_norm[:8]}... vào room {room_id_norm[:8]}... ({connection_manager.get_room_member_count(room_id_norm)} members)"
        )

        # ===== 5. Connection accepted =====
        member_count = connection_manager.get_room_member_count(room_id_norm)
        logger.info(
            f"[WS] User {user_id_norm[:8]}... connected to room {room_id_norm[:8]}... ({member_count} members)"
        )

        # ===== 6. Handle incoming messages =====
        while True:
                # Receive message from client
                data_raw = await websocket.receive_text()
                
                try:
                    data = json.loads(data_raw)
                    content = data.get("content", "").strip()
                    
                    # ===== 6a. Client sends plaintext - Backend receives =====
                    if not content:
                        continue
                    
                    # [DEBUG] Phase 6: Backend receives from WebSocket
                    logger.info(f"[🔄 PHASE 6] Backend receives from WebSocket | msg_len={len(content)} | from user {user_id_norm[:8]}... in room {room_id_norm[:8]}...")

                    
                    # ===== 6b. Backend calls Kernel Driver to encrypt =====
                    try:
                        # [DEBUG] Phase 7: Backend encrypts with driver
                        logger.info(f"[🔐 PHASE 7] Starting encryption with driver | content: {content[:50]} | content_len={len(content)}")
                        
                        # Call crypto_bridge to encrypt message using Driver (IOCTL_ENCRYPT_AES)
                        # Returns encrypted ciphertext (base64 encoded with IV prepended)
                        content_encrypted = await crypto_bridge.encrypt_message_payload(content)
                        
                        # [DEBUG] Phase 8: Backend encryption success
                        logger.info(f"[✅ PHASE 8] Encryption success | encrypted_len={len(content_encrypted)} | encrypted_start: {content_encrypted[:50]}")

                    except Exception as e:
                        logger.error(f"[❌ ERROR] Backend Driver encrypt failed: {e}")
                        await connection_manager.send_personal_message(
                            room_id_norm,
                            user_id_norm,
                            {
                                "type": "error",
                                "message": "Backend encryption failed",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                        continue
                    
                    # ===== 7. Save message to database (BOTH plaintext + encrypted) =====
                    # [DEBUG] Phase 9: Backend saves to DB
                    logger.info(f"[💾 PHASE 9] Saving to database | plaintext: {content[:50]} | encrypted: {content_encrypted[:50]}")
                    
                    message = Message(
                        id=None,  # Auto-generate UUID
                        room_id=room_id_norm,
                        sender_id=user_id_norm,
                        content=content,  # Plaintext for display/logging
                        content_encrypted=content_encrypted,  # Encrypted by Driver
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    
                    db_msg = SessionLocal()
                    try:
                        db_msg.add(message)
                        db_msg.commit()
                        db_msg.refresh(message)
                    except Exception:
                        db_msg.rollback()
                        raise
                    finally:
                        db_msg.close()
                    
                    # [DEBUG] Phase 10: Backend saves to DB success
                    logger.info(f"[✅ PHASE 10] Database saved | message_id: {message.id[:8]}...")
                    
                    # ===== 8. Broadcast encrypted message to room members =====
                    # [DEBUG] Phase 11: Backend broadcasts to room
                    logger.info(f"[📡 PHASE 11] Broadcasting to room members | room: {room_id_norm[:8]}... | message_id: {message.id[:8]}... | encrypted_len: {len(content_encrypted)}")
                    
                    # Clients receive encrypted and can decrypt using Web Crypto API
                    await connection_manager.broadcast_to_room(room_id_norm, {
                        "type": "message",
                        "id": message.id,
                        "room_id": room_id_norm,
                        "sender_id": user_id_norm,
                        "sender_name": user.username,
                        # "content": content,  # For fallback if client can't decrypt
                        "content_encrypted": message.content_encrypted,  # Encrypted by Driver
                        "created_at": message.created_at.isoformat(),
                        "updated_at": message.updated_at.isoformat(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    
                    logger.info(f"[✅ PHASE 11+] Broadcast completed | message_id: {message.id[:8]}...")
                
                except json.JSONDecodeError:
                    logger.warning(f"Invalid message format from {user_id}")
                    continue
                except Exception as e:
                    logger.error(f"[❌ ERROR] Error processing message: {e}", exc_info=True)
                    continue
    
    except WebSocketDisconnect:
        try:
            # Best-effort cleanup without holding DB connections
            if room_id_norm and user_id_norm:
                connection_manager.disconnect(room_id_norm, user_id_norm)

            member_count = connection_manager.get_room_member_count(room_id_norm) if room_id_norm else 0

            # Broadcast system message: user left (group only)
            if member_count > 0 and room_is_group and room_id_norm and user_id_norm:
                display_name = username or (user_id_norm[:8] if user_id_norm else "unknown")
                await connection_manager.broadcast_to_room(
                    room_id_norm,
                    {
                        "type": "system",
                        "content": f"👋 {display_name} đã rời phòng",
                        "user_id": user_id_norm,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

            if room_id_norm and user_id_norm:
                logger.info(
                    f"[DISCONNECT] User {user_id_norm[:8]}... rời room {room_id_norm[:8]}... ({member_count} members còn lại)"
                )
                logger.info(
                    f"[WS] User {user_id_norm[:8]}... disconnected from room {room_id_norm[:8]}... ({member_count} members left)"
                )

        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id} in room {room_id}: {e}")
        try:
            if user_id and room_id:
                connection_manager.disconnect(normalize_uuid(room_id), normalize_uuid(user_id))
        except:
            pass


# ==================== WebSocket /ws/notifications ====================

import asyncio
import urllib.parse

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket endpoint cho real-time notifications (friend requests, accepted, rejected, ...).
    
    Features:
    - JWT token authentication via query params
    - Real-time friend notifications
    - Per-user connection management
    - Automatic cleanup on disconnect
    - Heartbeat mechanism (ping/pong) để giữ connection alive
    
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
    user_id_norm = None
    heartbeat_task = None
    websocket_accepted = False
    
    async def safe_close(code: int = 1000, reason: str = ""):
        """Gracefully close websocket connection"""
        try:
            if websocket_accepted:
                await websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.debug(f"Error closing websocket: {e}")
    
    async def heartbeat():
        """Gửi ping định kỳ để giữ connection alive"""
        try:
            while True:
                await asyncio.sleep(30)  # Ping mỗi 30 giây
                try:
                    await websocket.send_text("ping")
                except Exception as e:
                    logger.debug(f"Heartbeat failed for user {user_id_norm[:8] if user_id_norm else 'unknown'}...: {e}")
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Heartbeat error: {e}")
    
    try:
        # ===== 1. Lấy token từ query params (SAFE PARSING) =====
        query_string = websocket.scope.get("query_string", b"").decode()
        
        # Parse query string an toàn
        try:
            parsed_qs = urllib.parse.parse_qs(query_string)
            token = parsed_qs.get("token", [""])[0].replace("Bearer ", "")
        except Exception as e:
            logger.warning(f"Query string parsing error: {e}")
            return
        
        if not token:
            logger.warning("Notification WebSocket rejected: no token provided")
            return
        
        # ===== 2. Verify JWT token =====
        try:
            payload = verify_access_token(token)
            user_id = payload.get("user_id")
            
            if not user_id:
                logger.warning("Notification WebSocket rejected: no user_id in token")
                return
        except Exception as e:
            logger.warning(f"Notification WebSocket rejected: invalid token - {e}")
            return
        
        user_id_norm = normalize_uuid(user_id)
        
        # ===== 3. Verify user exists =====
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id_norm).first()
            if not user:
                logger.warning(f"Notification WebSocket rejected: user {user_id_norm} not found")
                return
        except Exception as e:
            logger.error(f"Database error during user verification: {e}")
            return
        finally:
            db.close()
        
        # ===== 4. Accept WebSocket connection (AFTER all validations) =====
        try:
            await websocket.accept()
            websocket_accepted = True
            logger.info(f"✓ Notification WebSocket connected for user {user_id_norm[:8]}...")
        except Exception as e:
            logger.error(f"Failed to accept websocket: {e}")
            return
        
        # ===== 5. Connect user tới notification manager =====
        # Lưu ý: websocket đã được accept rồi, nên chỉ thêm vào dict
        notification_manager.active_connections[user_id_norm] = websocket
        logger.info(f"✓ User {user_id_norm[:8]}... added to notification manager")
        
        # ===== 6. Start heartbeat task =====
        heartbeat_task = asyncio.create_task(heartbeat())
        
        # ===== 7. Keep connection alive (ping/pong) =====
        while True:
            try:
                data = await websocket.receive_text()
                
                # Handle ping/pong để giữ connection sống
                if data == "ping":
                    try:
                        await websocket.send_text("pong")
                    except Exception as e:
                        logger.debug(f"Failed to send pong to {user_id_norm[:8]}...: {e}")
                        break
                elif data == "pong":
                    # Ignore pong from client
                    pass
                else:
                    logger.debug(f"Received from {user_id_norm[:8]}...: {data}")
            
            except WebSocketDisconnect:
                logger.info(f"✓ Notification WebSocket disconnected for user {user_id_norm[:8]}...")
                break
            except Exception as e:
                logger.warning(f"Error receiving data from {user_id_norm[:8]}...: {e}")
                break
    
    except Exception as e:
        logger.error(f"Notification WebSocket error for user {user_id_norm or user_id or 'unknown'}: {e}")
    
    finally:
        # ===== CLEANUP =====
        # Hủy heartbeat task
        if heartbeat_task:
            try:
                heartbeat_task.cancel()
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Error cancelling heartbeat: {e}")
        
        # Remove from notification manager
        if user_id_norm:
            try:
                notification_manager.disconnect(user_id_norm)
                logger.info(f"✓ Cleanup: User {user_id_norm[:8]}... removed from notification manager")
            except Exception as e:
                logger.debug(f"Error during cleanup: {e}")


# ==================== Server Startup ====================

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Secure Chat Backend Server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )



# ==================== Error Handlers ====================