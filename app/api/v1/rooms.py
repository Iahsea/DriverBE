"""
Room Management API Routes

Endpoints:
- GET /api/v1/rooms - Lấy danh sách phòng của user
- POST /api/v1/rooms - Tạo phòng chat mới
- GET /api/v1/rooms/{id} - Lấy chi tiết phòng
- DELETE /api/v1/rooms/{id} - Xóa phòng (admin only)
- POST /api/v1/rooms/{id}/members - Thêm thành viên
- DELETE /api/v1/rooms/{id}/members/{user_id} - Xóa thành viên
- GET /api/v1/rooms/{id}/messages - Lấy history tin nhắn
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.schemas.room import (
    RoomCreate,
    RoomResponse,
    RoomListResponse,
    RoomMemberAddRequest,
    RoomMemberDetailResponse,
)
from app.schemas.message import MessageResponse, MessageListResponse
from app.core.security import verify_access_token, get_token_from_header
from app.database.models import User, Room, RoomMember, Message
from app.database.database import get_db
from datetime import datetime
from uuid import UUID
import logging

router = APIRouter(prefix="/rooms", tags=["Rooms"])
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
        user_id_str = payload.get("user_id")
        if not user_id_str:
            raise ValueError("Invalid token payload")
        
        user = db.query(User).filter(User.id == user_id_str).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User không tìm thấy",
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ==================== GET /api/v1/rooms ====================

@router.get(
    "",
    response_model=list[RoomListResponse],
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách phòng của user",
)
async def list_rooms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RoomListResponse]:
    """
    Lấy danh sách tất cả phòng mà user tham gia.
    """
    try:
        # Lấy tất cả room memberships của user
        memberships = db.query(RoomMember).filter(RoomMember.user_id == current_user.id).all()
        
        rooms = []
        for membership in memberships:
            room = membership.room
            # Lấy last message
            last_message = db.query(Message).filter(
                Message.room_id == room.id
            ).order_by(desc(Message.created_at)).first()
            
            room_list = RoomListResponse(
                id=room.id,
                name=room.name,
                is_group=room.is_group,
                member_count=len(room.members) if room.members else 0,
                last_message_at=last_message.created_at if last_message else None,
            )
            rooms.append(room_list)
        
        logger.info(f"✓ Listed {len(rooms)} rooms for user {current_user.username}")
        return rooms
    
    except Exception as e:
        logger.error(f"Unexpected error in list_rooms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== POST /api/v1/rooms ====================

@router.post(
    "",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo phòng chat mới",
)
async def create_room(
    room_data: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoomResponse:
    """
    Tạo phòng chat mới (1-to-1 hoặc Group).
    User tạo phòng sẽ là admin.
    """
    try:
        # Tạo Room mới
        new_room = Room(
            name=room_data.name,
            description=room_data.description,
            is_group=room_data.is_group,
            created_by_id=current_user.id,
        )
        
        db.add(new_room)
        db.flush()  # Để lấy room.id
        
        # Thêm creator vào RoomMembers với role admin
        creator_member = RoomMember(
            room_id=new_room.id,
            user_id=current_user.id,
            role="admin",
        )
        
        db.add(creator_member)
        db.commit()
        db.refresh(new_room)
        
        logger.info(f"✓ Room created: {room_data.name} (ID: {new_room.id[:8]}...)")
        
        return RoomResponse.from_orm(new_room)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in create_room: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== GET /api/v1/rooms/{room_id} ====================

@router.get(
    "/{room_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Lấy chi tiết phòng",
)
async def get_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Lấy chi tiết phòng kèm danh sách thành viên.
    User phải là member của phòng.
    """
    try:
        # Kiểm tra room tồn tại
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phòng không tìm thấy",
            )
        
        # Kiểm tra user là member
        member = db.query(RoomMember).filter(
            (RoomMember.room_id == room_id) & 
            (RoomMember.user_id == current_user.id)
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập phòng này",
            )
        
        # Lấy danh sách members
        members = []
        for room_member in room.members:
            members.append({
                "id": room_member.id,
                "user_id": room_member.user_id,
                "username": room_member.user.username,
                "email": room_member.user.email,
                "role": room_member.role,
                "joined_at": room_member.joined_at.isoformat(),
            })
        
        return {
            "id": room.id,
            "name": room.name,
            "description": room.description,
            "is_group": room.is_group,
            "created_by_id": room.created_by_id,
            "created_at": room.created_at.isoformat(),
            "updated_at": room.updated_at.isoformat(),
            "member_count": len(room.members),
            "members": members,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_room: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== DELETE /api/v1/rooms/{room_id} ====================

@router.delete(
    "/{room_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa phòng (admin only)",
)
async def delete_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Xóa phòng. Chỉ admin mới có thể xóa.
    """
    try:
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phòng không tìm thấy",
            )
        
        # Kiểm tra user là admin
        member = db.query(RoomMember).filter(
            (RoomMember.room_id == room_id) & 
            (RoomMember.user_id == current_user.id)
        ).first()
        
        if not member or member.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ admin mới có thể xóa phòng",
            )
        
        db.delete(room)
        db.commit()
        
        logger.info(f"✓ Room deleted: {room.name} (ID: {room.id[:8]}...)")
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in delete_room: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== POST /api/v1/rooms/{room_id}/members ====================

@router.post(
    "/{room_id}/members",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm thành viên vào phòng",
)
async def add_member(
    room_id: str,
    member_data: RoomMemberAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Thêm user vào phòng. Admin hoặc moderator mới có thể thêm.
    """
    try:
        # Kiểm tra room tồn tại
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phòng không tìm thấy",
            )
        
        # Kiểm tra current user là admin/moderator
        current_member = db.query(RoomMember).filter(
            (RoomMember.room_id == room_id) & 
            (RoomMember.user_id == current_user.id)
        ).first()
        
        if not current_member or current_member.role not in ["admin", "moderator"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ admin/moderator mới có thể thêm thành viên",
            )
        
        # Kiểm tra user cần thêm tồn tại
        new_user = db.query(User).filter(User.id == member_data.user_id).first()
        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User không tìm thấy",
            )
        
        # Kiểm tra user đã là member chưa
        existing = db.query(RoomMember).filter(
            (RoomMember.room_id == room_id) & 
            (RoomMember.user_id == member_data.user_id)
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User đã là thành viên của phòng",
            )
        
        # Thêm member mới
        new_member = RoomMember(
            room_id=room_id,
            user_id=member_data.user_id,
            role=member_data.role,
        )
        
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
        
        logger.info(f"✓ Member {new_user.username} added to room {room.name}")
        
        return {
            "id": new_member.id,
            "room_id": new_member.room_id,
            "user_id": new_member.user_id,
            "username": new_user.username,
            "role": new_member.role,
            "joined_at": new_member.joined_at.isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in add_member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== DELETE /api/v1/rooms/{room_id}/members/{user_id} ====================

@router.delete(
    "/{room_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa thành viên khỏi phòng",
)
async def remove_member(
    room_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Xóa user khỏi phòng. Admin/moderator mới có thể xóa.
    """
    try:
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phòng không tìm thấy",
            )
        
        # Kiểm tra current user là admin/moderator
        current_member = db.query(RoomMember).filter(
            (RoomMember.room_id == room_id) & 
            (RoomMember.user_id == current_user.id)
        ).first()
        
        if not current_member or current_member.role not in ["admin", "moderator"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ admin/moderator mới có thể xóa thành viên",
            )
        
        # Tìm member cần xóa
        member = db.query(RoomMember).filter(
            (RoomMember.room_id == room_id) & 
            (RoomMember.user_id == user_id)
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thành viên không tìm thấy",
            )
        
        db.delete(member)
        db.commit()
        
        logger.info(f"✓ Member {user_id} removed from room {room.name}")
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in remove_member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== GET /api/v1/rooms/{room_id}/messages ====================

@router.get(
    "/{room_id}/messages",
    response_model=MessageListResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy history tin nhắn",
)
async def get_messages(
    room_id: str,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageListResponse:
    """
    Lấy history tin nhắn của phòng.
    User phải là member của phòng.
    """
    try:
        # Kiểm tra user là member
        member = db.query(RoomMember).filter(
            (RoomMember.room_id == room_id) & 
            (RoomMember.user_id == current_user.id)
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập phòng này",
            )
        
        # Lấy tin nhắn
        total = db.query(Message).filter(Message.room_id == room_id).count()
        messages_db = db.query(Message).filter(
            Message.room_id == room_id
        ).order_by(desc(Message.created_at)).offset(skip).limit(limit).all()
        
        messages = []
        for msg in messages_db:
            messages.append(MessageResponse(
                id=msg.id,
                room_id=msg.room_id,
                sender_id=msg.sender_id,
                sender_name=msg.sender.username,
                content=msg.content,
                content_encrypted=msg.content_encrypted,
                created_at=msg.created_at,
                updated_at=msg.updated_at,
            ))
        
        # Reverse để sắp xếp từ cũ nhất đến mới nhất
        messages.reverse()
        
        logger.debug(f"Retrieved {len(messages)} messages from room {room_id}")
        
        return MessageListResponse(total=total, messages=messages)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )
