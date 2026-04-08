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

from fastapi import FastAPI, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from datetime import datetime, timezone

from app.database.database import init_db
from app.core.crypto_bridge import crypto_bridge
from app.api.v1 import auth
from app.websocket.connection_manager import ConnectionManager

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

logger.info("✓ Auth routes registered at /api/v1/auth")

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

# Initialize connection manager
connection_manager = ConnectionManager()


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint cho chat.
    
    Features:
    - Quản lý kết nối với ConnectionManager
    - Broadcast tin nhắn sang tất cả clients
    - System messages khi client join/leave
    
    Path: ws://localhost:8000/ws/chat
    
    Message format:
    {
        "type": "message|system",
        "content": "...",
        "username": "...",  (optional)
        "timestamp": "..."  (optional)
    }
    """
    await connection_manager.connect(websocket)
    
    try:
        # Broadcast system message: user joined
        await connection_manager.broadcast({
            "type": "system",
            "content": f"Client joined. Total connections: {connection_manager.get_connection_count()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        logger.info(f"✓ WebSocket client connected. Total: {connection_manager.get_connection_count()}")
        
        # Handle incoming messages
        while True:
            # Receive message từ client
            data = await websocket.receive_text()
            
            # Broadcast message đến tất cả clients
            await connection_manager.broadcast({
                "type": "message",
                "content": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        
        # Broadcast system message: user left
        await connection_manager.broadcast({
            "type": "system",
            "content": f"Client disconnected. Total connections: {connection_manager.get_connection_count()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        logger.info(f"WebSocket client disconnected. Total: {connection_manager.get_connection_count()}")
    
    except Exception as e:
        connection_manager.disconnect(websocket)
        logger.error(f"WebSocket error: {e}")


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
