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

from app.database.database import init_db, SessionLocal
from app.core.crypto_bridge import crypto_bridge
from app.core.security import verify_access_token
from app.api.v1 import auth, rooms, friends
from app.websocket.connection_manager import ConnectionManager
from app.database.models import User, Room, RoomMember, Message

# ==================== Logging Configuration ====================

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

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

# Initialize connection manager (per-room)
connection_manager = ConnectionManager()

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
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                await websocket.close(code=4004, reason="User not found")
                logger.warning(f"WebSocket rejected: user {user_id} not found")
                return
            
            room = db.query(Room).filter(Room.id == room_id).first()
            if not room:
                await websocket.close(code=4005, reason="Room not found")
                logger.warning(f"WebSocket rejected: room {room_id} not found")
                return
            
            # ===== 3. Verify user is member of room =====
            member = db.query(RoomMember).filter(
                (RoomMember.room_id == room_id) & 
                (RoomMember.user_id == user_id)
            ).first()
            
            if not member:
                await websocket.close(code=4006, reason="Not a member of this room")
                logger.warning(f"WebSocket rejected: user {user_id} is not member of room {room_id}")
                return
            
            # ===== 4. Accept connection =====
            await connection_manager.connect(room_id, user_id, websocket)
            logger.info(f"[CONNECT] User {user_id[:8]}... vào room {room_id[:8]}... ({connection_manager.get_room_member_count(room_id)} members)")
            
            # ===== 5. Broadcast system message: user joined =====
            member_count = connection_manager.get_room_member_count(room_id)
            await connection_manager.broadcast_to_room(room_id, {
                "type": "system",
                "content": f"👋 {user.username} đã tham gia phòng",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            
            logger.info(f"[WS] User {user_id[:8]}... connected to room {room_id[:8]}... ({member_count} members)")
            
            # ===== 6. Handle incoming messages =====
            while True:
                # Receive message from client
                data_raw = await websocket.receive_text()
                
                try:
                    data = json.loads(data_raw)
                    content = data.get("content", "").strip()
                    
                    if not content:
                        continue
                    
                    # ===== 7. Save message to database =====
                    message = Message(
                        id=None,  # Auto-generate UUID
                        room_id=room_id,
                        sender_id=user_id,
                        content=content,
                        content_encrypted=None,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    
                    db.add(message)
                    db.commit()
                    db.refresh(message)
                    
                    # ===== 8. Broadcast message to room members =====
                    await connection_manager.broadcast_to_room(room_id, {
                        "type": "message",
                        "id": message.id,
                        "room_id": room_id,
                        "sender_id": user_id,
                        "sender_name": user.username,
                        "content": content,
                        "content_encrypted": message.content_encrypted,
                        "created_at": message.created_at.isoformat(),
                        "updated_at": message.updated_at.isoformat(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    
                    logger.debug(f"[MSG] {user.username} → room {room_id[:8]}...: {content[:50]}")
                
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
            user = db.query(User).filter(User.id == user_id).first()
            username = user.username if user else user_id[:8]
            
            # Disconnect from connection manager
            connection_manager.disconnect(room_id, user_id)
            
            member_count = connection_manager.get_room_member_count(room_id)
            
            # Broadcast system message: user left
            if member_count > 0:
                await connection_manager.broadcast_to_room(room_id, {
                    "type": "system",
                    "content": f"👋 {username} đã rời phòng",
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            
            logger.info(f"[DISCONNECT] User {user_id[:8]}... rời room {room_id[:8]}... ({member_count} members còn lại)")
            logger.info(f"[WS] User {user_id[:8]}... disconnected from room {room_id[:8]}... ({member_count} members left)")
        
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id} in room {room_id}: {e}")
        try:
            connection_manager.disconnect(room_id, user_id)
        except:
            pass


# ==================== Error Handlers ====================

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "status": "error",
        "message": "Internal server error",
    }


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload on file changes
        log_level="info",
    )
