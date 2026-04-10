"""
Message Management API Routes

Endpoints:
- GET /api/v1/messages/{message_id} - Lấy chi tiết message
- POST /api/v1/messages/{message_id}/decrypt - Giải mã message (Backend decrypt)
- GET /api/v1/rooms/{room_id}/messages - Lấy history messages của room
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.schemas.message import MessageResponse, MessageListResponse, DecryptMessageRequest, DecryptMessageResponse
from app.core.security import verify_access_token, get_token_from_header
from app.core.id_utils import normalize_uuid
from app.core.crypto_bridge import crypto_bridge
from app.database.models import User, Message, Room, RoomMember
from app.database.database import get_db
from datetime import datetime
import logging

router = APIRouter(prefix="/messages", tags=["Messages"])
logger = logging.getLogger(__name__)


def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    """
    Dependency: Lấy current user từ JWT token.
    """
    try:
        token = get_token_from_header(authorization)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ",
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload = verify_access_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID không hợp lệ",
            )
        
        user_id_norm = normalize_uuid(user_id)
        user = db.query(User).filter(User.id == user_id_norm).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User không tồn tại",
            )
        
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
        )


@router.get(
    "/{message_id}",
    response_model=MessageResponse,
    summary="Lấy chi tiết message",
    responses={
        200: {"description": "Message details"},
        401: {"description": "Unauthorized"},
        404: {"description": "Message not found"},
    },
)
async def get_message(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lấy chi tiết của một message theo ID.
    
    Kiểm tra: User phải là member của room chứa message.
    """
    message_id_norm = normalize_uuid(message_id)
    message = db.query(Message).filter(Message.id == message_id_norm).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message không tồn tại",
        )
    
    # Verify user is member of room containing this message
    member = db.query(RoomMember).filter(
        (RoomMember.room_id == message.room_id) &
        (RoomMember.user_id == current_user.id)
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không phải member của room chứa message này",
        )
    
    return MessageResponse(
        id=message.id,
        room_id=message.room_id,
        sender_id=message.sender_id,
        content=message.content,
        content_encrypted=message.content_encrypted,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


@router.post(
    "/{message_id}/decrypt",
    response_model=DecryptMessageResponse,
    summary="Giải mã message",
    responses={
        200: {"description": "Decrypted message"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Message not found"},
        422: {"description": "Decryption failed"},
    },
)
async def decrypt_message(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Giải mã (decrypt) một message đã mã hóa.
    
    Backend sẽ dùng Kernel Driver (hoặc mock crypto) để giải mã 
    encrypted message và trả về plaintext.
    
    Flow:
    1. Client2 nhận encrypted message qua WebSocket
    2. Client2 call POST /api/v1/messages/{message_id}/decrypt
    3. Backend nhận request, kiểm tra permissions
    4. Backend call crypto_bridge.decrypt_message_payload()
    5. Backend trả về plaintext trong response
    6. Client2 hiển thị plaintext
    
    Returns:
        {
            "id": "message_id",
            "room_id": "room_id",
            "sender_id": "user_id",
            "content_plaintext": "Hello",  # Decrypted plaintext
            "created_at": "2026-04-10T...",
            "message": "Message decrypted successfully"
        }
    """
    message_id_norm = normalize_uuid(message_id)
    message = db.query(Message).filter(Message.id == message_id_norm).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message không tồn tại",
        )
    
    # Verify user is member of room containing this message
    member = db.query(RoomMember).filter(
        (RoomMember.room_id == message.room_id) &
        (RoomMember.user_id == current_user.id)
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không phải member của room chứa message này",
        )
    
    # Decrypt the message using crypto_bridge
    try:
        plaintext = await crypto_bridge.decrypt_message_payload(message.content_encrypted)
        
        logger.info(f"✓ Message {message_id_norm[:8]}... decrypted successfully for user {current_user.username}")
        
        return DecryptMessageResponse(
            id=message.id,
            room_id=message.room_id,
            sender_id=message.sender_id,
            content_plaintext=plaintext,
            created_at=message.created_at,
            message="Message decrypted successfully",
        )
    
    except ValueError as e:
        logger.error(f"✗ Decryption validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Decryption validation failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"✗ Decryption failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Decryption failed: {str(e)}",
        )


@router.get(
    "/room/{room_id}",
    response_model=MessageListResponse,
    summary="Lấy history messages của room",
    responses={
        200: {"description": "List of messages"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Room not found"},
    },
)
async def get_room_messages(
    room_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lấy lịch sử messages của một room (pagination).
    
    Kiểm tra: User phải là member của room.
    
    Query params:
    - limit: Số messages trả về (default: 50, max: 100)
    - offset: Offset để pagination (default: 0)
    """
    room_id_norm = normalize_uuid(room_id)
    room = db.query(Room).filter(Room.id == room_id_norm).first()
    
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room không tồn tại",
        )
    
    # Verify user is member of room
    member = db.query(RoomMember).filter(
        (RoomMember.room_id == room_id_norm) &
        (RoomMember.user_id == current_user.id)
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không phải member của room này",
        )
    
    # Validate pagination params
    limit = min(limit, 100)  # Max 100 messages per request
    offset = max(offset, 0)
    
    # Query messages ordered by created_at DESC (newest first)
    total = db.query(Message).filter(Message.room_id == room_id_norm).count()
    
    messages = db.query(Message).filter(
        Message.room_id == room_id_norm
    ).order_by(desc(Message.created_at)).offset(offset).limit(limit).all()
    
    return MessageListResponse(
        total=total,
        limit=limit,
        offset=offset,
        messages=[
            MessageResponse(
                id=msg.id,
                room_id=msg.room_id,
                sender_id=msg.sender_id,
                content=msg.content,
                content_encrypted=msg.content_encrypted,
                created_at=msg.created_at,
                updated_at=msg.updated_at,
            )
            for msg in messages
        ],
    )
