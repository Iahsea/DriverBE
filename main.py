import os
from datetime import datetime, timezone

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.websocket.connection_manager import ConnectionManager


class MessagePreviewRequest(BaseModel):
    room_id: str
    sender: str
    message: str


class MessagePreviewResponse(BaseModel):
    room_id: str
    sender: str
    message: str
    encrypted: bool
    received_at: str


def load_cors_origins() -> list[str]:
    raw_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    )
    return [item.strip() for item in raw_origins.split(",") if item.strip()]


app = FastAPI(
    title="Secure Chat Backend",
    version="0.1.0",
    description="FastAPI backend ready to connect with React and WebSocket clients.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=load_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo WebSocket Connection Manager
connection_manager = ConnectionManager()

api_v1 = APIRouter(prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "secure-chat-backend", "status": "running"}


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@api_v1.get("/ping")
async def ping() -> dict[str, str]:
    return {"message": "pong"}


@api_v1.post("/messages/preview", response_model=MessagePreviewResponse)
async def preview_message(payload: MessagePreviewRequest) -> MessagePreviewResponse:
    # Placeholder: this is where driver AES encryption integration will be called.
    return MessagePreviewResponse(
        room_id=payload.room_id,
        sender=payload.sender,
        message=payload.message,
        encrypted=False,
        received_at=datetime.now(timezone.utc).isoformat(),
    )


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """
    WebSocket endpoint cho chat application.
    
    Quản lý kết nối, nhận message từ client, 
    broadcast đến tất cả clients khác đang online.
    """
    await connection_manager.connect(websocket)
    
    try:
        # Gửi thông báo khi client vừa kết nối
        await connection_manager.broadcast(
            {
                "type": "system",
                "message": f"Một client mới vừa kết nối. Tổng: {connection_manager.get_connection_count()} clients online",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        
        # Nhận message từ client và broadcast đến tất cả
        while True:
            data = await websocket.receive_text()
            
            # Broadcast message đến tất cả clients
            await connection_manager.broadcast(
                {
                    "type": "chat",
                    "message": data,
                    "encrypted": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
    except WebSocketDisconnect:
        # Loại bỏ client khỏi danh sách khi disconnect
        connection_manager.disconnect(websocket)
        
        # Thông báo đến các clients còn lại
        await connection_manager.broadcast(
            {
                "type": "system",
                "message": f"Một client vừa ngắt kết nối. Còn lại: {connection_manager.get_connection_count()} clients online",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


app.include_router(api_v1)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
