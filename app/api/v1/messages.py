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
from app.schemas.message import MessageResponse, MessageListResponse, DecryptMessageRequest, DecryptMessageResponse, VerifyIntegrityRequest
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
        message_hash=message.message_hash,
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
    encrypted message và trả về plaintext + message_hash để Client2 xác thực.
    
    SECURITY FLOW:
    1. Client2 nhận {content_encrypted, message_hash} qua WebSocket
    2. Client2 gọi POST /api/v1/messages/{message_id}/decrypt để lấy plaintext
    3. Backend trả về plaintext + message_hash
    4. Client2 (MUST) compute MD5(plaintext) và so sánh với message_hash
       - Nếu match: ✅ Message verified (không bị sửa đổi)
       - Nếu mismatch: ⚠️ Tampering detected (có thể bị attacker sửa)
    5. Client2 hiển thị message với verification indicator
    
    CLIENT2 IMPLEMENTATION (Frontend):
    ```javascript
    // 1. Decrypt
    const response = await decryptMessage(messageId)
    const { content_plaintext, message_hash } = response
    
    // 2. Compute MD5 (IMPORTANT!)
    const localHash = await computeMD5(content_plaintext)
    
    // 3. Verify (IMPORTANT!)
    const isValid = localHash === message_hash
    
    if (isValid) {
      console.log("✅ Message integrity verified")
    } else {
      console.warn("⚠️ Message integrity check FAILED - data may have been modified")
    }
    ```
    
    Returns:
        {
            "id": "message_id",
            "room_id": "room_id",
            "sender_id": "user_id",
            "content_plaintext": "Hello",  # Decrypted plaintext
            "message_hash": "802c21ae4d9853d40ef331b4bb2bb22c",  # For verification
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
        # [DEBUG] Phase 15: Backend receives decrypt request
        logger.info(f"[🔑 PHASE 15] Backend receives decrypt request | message_id: {message_id_norm[:8]}... | user: {current_user.username}")
        
        # [DEBUG] Phase 16: Backend decrypts
        logger.info(f"[🔓 PHASE 16] Starting decryption | encrypted_len: {len(message.content_encrypted)} | encrypted_start: {message.content_encrypted[:50]}")
        
        plaintext = await crypto_bridge.decrypt_message_payload(message.content_encrypted)
        
        # [DEBUG] Phase 17: Backend decrypt success
        logger.info(f"[✅ PHASE 17] Decryption success | plaintext_len: {len(plaintext)} | plaintext: {plaintext[:50]}")
        
        # [DEBUG] Phase 18: Backend sends decrypt response
        logger.info(f"[📤 PHASE 18] Sending decrypt response | message_id: {message_id_norm[:8]}... | plaintext: {plaintext[:50]}")
        
        logger.info(f"✓ Message {message_id_norm[:8]}... decrypted successfully for user {current_user.username}")
        
        return DecryptMessageResponse(
            id=message.id,
            room_id=message.room_id,
            sender_id=message.sender_id,
            content_plaintext=plaintext,
            message_hash=message.message_hash,
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


@router.post(
    "/{message_id}/verify-integrity",
    summary="Verify message integrity via backend (optional helper)",
    responses={
        200: {"description": "Verification result"},
        401: {"description": "Unauthorized"},
        404: {"description": "Message not found"},
    },
)
async def verify_message_integrity(
    message_id: str,
    body: VerifyIntegrityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Optional helper endpoint: Backend verifies message integrity.
    
    Client2 can call this to have backend verify the hash,
    but PRIMARY verification should be done CLIENT-SIDE for security reasons.
    
    ⚠️ SECURITY NOTE:
    If attacker modifies both message AND hash in transit,
    this endpoint could also be fooled. For true security,
    Client2 MUST verify independently (compute hash locally).
    
    This endpoint is useful for:
    - Audit logging
    - Compliance verification
    - Double-checking (Client2 can compare results)
    
    Request:
        POST /api/v1/messages/{message_id}/verify-integrity
        {
            "plaintext_received": "Hello"  # Plaintext Client2 decrypted
        }
    
    Response:
        {
            "verified": true,                               # Hash matches
            "message_hash": "802c21ae4d9853d40ef331b4bb2bb22c",
            "message": "Message integrity verified",
            "status": "verified"                            # or "mismatch" or "error"
        }
    """
    try:
        message_id_norm = normalize_uuid(message_id)
        message = db.query(Message).filter(Message.id == message_id_norm).first()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message không tồn tại",
            )
        
        # Verify user is member of room
        member = db.query(RoomMember).filter(
            (RoomMember.room_id == message.room_id) &
            (RoomMember.user_id == current_user.id)
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không phải member của room chứa message này",
            )
        
        # Get plaintext from request body
        plaintext_received = body.plaintext_received
        
        # Compute hash of received plaintext
        expected_hash = await crypto_bridge.hash_message_content(plaintext_received)
        
        # Compare with stored hash
        stored_hash = message.message_hash or ""
        verified = expected_hash == stored_hash
        
        status_msg = "verified" if verified else "mismatch"
        
        logger.info(
            f"Message {message_id_norm[:8]}... integrity check: {status_msg} "
            f"(received: {expected_hash}, stored: {stored_hash})"
        )
        
        return {
            "verified": verified,
            "message_hash": stored_hash,
            "computed_hash": expected_hash,
            "message": "Message integrity verified" if verified else "Hash mismatch - message may have been modified",
            "status": status_msg,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Message integrity verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Verification failed: {str(e)}",
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
                message_hash=msg.message_hash,
                created_at=msg.created_at,
                updated_at=msg.updated_at,
            )
            for msg in messages
        ],
    )
