"""
Friendship Management API Routes

Endpoints:
- GET /api/v1/friends - Lấy danh sách bạn bè
- GET /api/v1/friends/requests - Lấy danh sách lời mời kết bạn đang chờ
- POST /api/v1/friends/request - Gửi lời mời kết bạn
- POST /api/v1/friends/request/{request_id}/accept - Chấp nhận lời mời
- POST /api/v1/friends/request/{request_id}/reject - Từ chối lời mời
- POST /api/v1/friends/request/{request_id}/cancel - Hủy lời mời (người gửi)
- DELETE /api/v1/friends/{user_id} - Xóa bạn/hủy quan hệ bạn bè
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.schemas.friend import (
    FriendRequestCreate,
    FriendRequestResponse,
    FriendResponse,
    FriendRequestListResponse,
    FriendListResponse,
)
from app.core.security import verify_access_token, get_token_from_header
from app.database.models import User, FriendRequest, Friendship
from app.database.database import get_db
from datetime import datetime
import logging

router = APIRouter(prefix="/friends", tags=["Friends"])
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
            raise ValueError("Invalid token payload: no user_id")
        
        # Query user by ID (String format)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User not found: {user_id}")
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


# ==================== GET /api/v1/friends ====================

@router.get(
    "",
    response_model=FriendListResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách bạn bè",
)
async def get_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FriendListResponse:
    """
    Lấy danh sách bạn bè đã chấp nhận (không có pending requests).
    """
    try:
        # Lấy tất cả friendships của user (ở vị trí user_id_1 hoặc user_id_2)
        friendships = db.query(Friendship).filter(
            or_(
                Friendship.user_id_1 == current_user.id,
                Friendship.user_id_2 == current_user.id,
            )
        ).all()
        
        friends = []
        for friendship in friendships:
            # Lấy user của bạn (phía bên kia)
            friend_id = friendship.user_id_2 if friendship.user_id_1 == current_user.id else friendship.user_id_1
            friend = db.query(User).filter(User.id == friend_id).first()
            
            if friend:
                friends.append(FriendResponse(
                    id=friend.id,
                    username=friend.username,
                    email=friend.email,
                    created_at=friend.created_at,
                ))
        
        logger.info(f"✓ Retrieved {len(friends)} friends for user {current_user.username}")
        return FriendListResponse(total=len(friends), friends=friends)
    
    except Exception as e:
        logger.error(f"Unexpected error in get_friends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== GET /api/v1/friends/requests ====================

@router.get(
    "/requests",
    response_model=FriendRequestListResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách lời mời kết bạn đang chờ",
)
async def get_friend_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FriendRequestListResponse:
    """
    Lấy danh sách lời mời kết bạn pending đến user hiện tại.
    """
    try:
        # Lấy tất cả pending requests đến user hiện tại
        requests = db.query(FriendRequest).filter(
            and_(
                FriendRequest.to_user_id == current_user.id,
                FriendRequest.status == "pending",
            )
        ).all()
        
        request_responses = []
        for req in requests:
            from_user = db.query(User).filter(User.id == req.from_user_id).first()
            to_user = db.query(User).filter(User.id == req.to_user_id).first()
            
            if from_user and to_user:
                request_responses.append(FriendRequestResponse(
                    id=req.id,
                    from_user_id=req.from_user_id,
                    from_username=from_user.username,
                    to_user_id=req.to_user_id,
                    to_username=to_user.username,
                    status=req.status,
                    created_at=req.created_at,
                    updated_at=req.updated_at,
                ))
        
        logger.info(f"✓ Retrieved {len(request_responses)} pending requests for user {current_user.username}")
        return FriendRequestListResponse(total=len(request_responses), requests=request_responses)
    
    except Exception as e:
        logger.error(f"Unexpected error in get_friend_requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== POST /api/v1/friends/request ====================

@router.post(
    "/request",
    response_model=FriendRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gửi lời mời kết bạn",
)
async def send_friend_request(
    request_data: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FriendRequestResponse:
    """
    Gửi lời mời kết bạn đến user khác.
    
    Kiểm tra:
    1. from_user và to_user không trùng nhau
    2. Chưa là bạn (không có friendship)
    3. Chưa có pending request
    """
    try:
        # Kiểm tra to_user != current_user
        if request_data.to_user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể gửi lời mời cho chính mình",
            )
        
        # Kiểm tra to_user tồn tại
        to_user = db.query(User).filter(User.id == request_data.to_user_id).first()
        if not to_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User không tìm thấy",
            )
        
        # Kiểm tra đã là bạn chưa
        user_id_1 = min(current_user.id, request_data.to_user_id)
        user_id_2 = max(current_user.id, request_data.to_user_id)
        
        existing_friendship = db.query(Friendship).filter(
            and_(
                Friendship.user_id_1 == user_id_1,
                Friendship.user_id_2 == user_id_2,
            )
        ).first()
        
        if existing_friendship:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Đã là bạn bè rồi",
            )
        
        # Kiểm tra có pending request chưa (cả chiều)
        existing_request = db.query(FriendRequest).filter(
            or_(
                and_(
                    FriendRequest.from_user_id == current_user.id,
                    FriendRequest.to_user_id == request_data.to_user_id,
                    FriendRequest.status == "pending",
                ),
                and_(
                    FriendRequest.from_user_id == request_data.to_user_id,
                    FriendRequest.to_user_id == current_user.id,
                    FriendRequest.status == "pending",
                ),
            )
        ).first()
        
        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Đã có lời mời kết bạn pending",
            )
        
        # Tạo friend request mới
        new_request = FriendRequest(
            from_user_id=current_user.id,
            to_user_id=request_data.to_user_id,
            status="pending",
        )
        
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        
        logger.info(f"✓ Friend request sent: {current_user.username} → {to_user.username}")
        
        return FriendRequestResponse(
            id=new_request.id,
            from_user_id=new_request.from_user_id,
            from_username=current_user.username,
            to_user_id=new_request.to_user_id,
            to_username=to_user.username,
            status=new_request.status,
            created_at=new_request.created_at,
            updated_at=new_request.updated_at,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in send_friend_request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== POST /api/v1/friends/request/{request_id}/accept ====================

@router.post(
    "/request/{request_id}/accept",
    response_model=FriendRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Chấp nhận lời mời kết bạn",
)
async def accept_friend_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FriendRequestResponse:
    """
    Chấp nhận lời mời kết bạn.
    
    Quy trình:
    1. Tìm request (phải là người nhận)
    2. Update status = accepted
    3. Tạo friendship record
    """
    try:
        # Tìm request
        friend_request = db.query(FriendRequest).filter(FriendRequest.id == request_id).first()
        if not friend_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lời mời không tìm thấy",
            )
        
        # Verify current_user là người nhận
        if friend_request.to_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ người nhận mới có thể chấp nhận lời mời",
            )
        
        # Verify request status = pending
        if friend_request.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lời mời đã {friend_request.status} rồi",
            )
        
        # Update status
        friend_request.status = "accepted"
        friend_request.updated_at = datetime.utcnow()
        
        # Tạo friendship record (user_id_1 < user_id_2)
        user_id_1 = min(friend_request.from_user_id, friend_request.to_user_id)
        user_id_2 = max(friend_request.from_user_id, friend_request.to_user_id)
        
        new_friendship = Friendship(
            user_id_1=user_id_1,
            user_id_2=user_id_2,
        )
        
        db.add(new_friendship)
        db.commit()
        db.refresh(friend_request)
        
        from_user = db.query(User).filter(User.id == friend_request.from_user_id).first()
        to_user = db.query(User).filter(User.id == friend_request.to_user_id).first()
        
        logger.info(f"✓ Friend request accepted: {from_user.username} ↔ {to_user.username}")
        
        return FriendRequestResponse(
            id=friend_request.id,
            from_user_id=friend_request.from_user_id,
            from_username=from_user.username,
            to_user_id=friend_request.to_user_id,
            to_username=to_user.username,
            status=friend_request.status,
            created_at=friend_request.created_at,
            updated_at=friend_request.updated_at,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in accept_friend_request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== POST /api/v1/friends/request/{request_id}/reject ====================

@router.post(
    "/request/{request_id}/reject",
    response_model=FriendRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Từ chối lời mời kết bạn",
)
async def reject_friend_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FriendRequestResponse:
    """
    Từ chối lời mời kết bạn.
    
    Update status = rejected (người nhận only)
    """
    try:
        # Tìm request
        friend_request = db.query(FriendRequest).filter(FriendRequest.id == request_id).first()
        if not friend_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lời mời không tìm thấy",
            )
        
        # Verify current_user là người nhận
        if friend_request.to_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ người nhận mới có thể từ chối lời mời",
            )
        
        # Verify request status = pending
        if friend_request.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lời mời đã {friend_request.status} rồi",
            )
        
        # Update status
        friend_request.status = "rejected"
        friend_request.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(friend_request)
        
        from_user = db.query(User).filter(User.id == friend_request.from_user_id).first()
        to_user = db.query(User).filter(User.id == friend_request.to_user_id).first()
        
        logger.info(f"✓ Friend request rejected: {from_user.username} ← {to_user.username}")
        
        return FriendRequestResponse(
            id=friend_request.id,
            from_user_id=friend_request.from_user_id,
            from_username=from_user.username,
            to_user_id=friend_request.to_user_id,
            to_username=to_user.username,
            status=friend_request.status,
            created_at=friend_request.created_at,
            updated_at=friend_request.updated_at,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in reject_friend_request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== POST /api/v1/friends/request/{request_id}/cancel ====================

@router.post(
    "/request/{request_id}/cancel",
    response_model=FriendRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Hủy lời mời kết bạn",
)
async def cancel_friend_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FriendRequestResponse:
    """
    Hủy lời mời kết bạn (người gửi only).
    
    Update status = canceled
    """
    try:
        # Tìm request
        friend_request = db.query(FriendRequest).filter(FriendRequest.id == request_id).first()
        if not friend_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lời mời không tìm thấy",
            )
        
        # Verify current_user là người gửi
        if friend_request.from_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ người gửi mới có thể hủy lời mời",
            )
        
        # Verify request status = pending
        if friend_request.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lời mời đã {friend_request.status} rồi",
            )
        
        # Update status
        friend_request.status = "canceled"
        friend_request.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(friend_request)
        
        from_user = db.query(User).filter(User.id == friend_request.from_user_id).first()
        to_user = db.query(User).filter(User.id == friend_request.to_user_id).first()
        
        logger.info(f"✓ Friend request canceled: {from_user.username} ↛ {to_user.username}")
        
        return FriendRequestResponse(
            id=friend_request.id,
            from_user_id=friend_request.from_user_id,
            from_username=from_user.username,
            to_user_id=friend_request.to_user_id,
            to_username=to_user.username,
            status=friend_request.status,
            created_at=friend_request.created_at,
            updated_at=friend_request.updated_at,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in cancel_friend_request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )


# ==================== DELETE /api/v1/friends/{user_id} ====================

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa bạn/hủy quan hệ bạn bè",
)
async def delete_friend(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Xóa bạn/hủy quan hệ bạn bè với user khác.
    """
    try:
        # Kiểm tra user_id != current_user.id
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể xóa chính mình",
            )
        
        # Kiểm tra user tồn tại
        friend_user = db.query(User).filter(User.id == user_id).first()
        if not friend_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User không tìm thấy",
            )
        
        # Tìm friendship (user_id_1 < user_id_2)
        user_id_1 = min(current_user.id, user_id)
        user_id_2 = max(current_user.id, user_id)
        
        friendship = db.query(Friendship).filter(
            and_(
                Friendship.user_id_1 == user_id_1,
                Friendship.user_id_2 == user_id_2,
            )
        ).first()
        
        if not friendship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không phải bạn bè, không thể xóa",
            )
        
        # Xóa friendship
        db.delete(friendship)
        db.commit()
        
        logger.info(f"✓ Friendship deleted: {current_user.username} ↛ {friend_user.username}")
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in delete_friend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống",
        )
