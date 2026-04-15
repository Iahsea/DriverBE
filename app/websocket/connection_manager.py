"""
WebSocket Connection Manager - Per-Room Implementation

Quản lý các kết nối WebSocket của clients theo từng phòng chat:
- Per-room connection management: {room_id: {user_id: websocket}}
- Broadcast tin nhắn trong một phòng cụ thể
- Gửi message cá nhân
- Tracking member count per room
"""

from fastapi import WebSocket
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Quản lý các kết nối WebSocket theo từng phòng chat.
    
    Structure:
    {
        room_id: {
            user_id: websocket,
            user_id: websocket,
            ...
        },
        room_id: {...},
        ...
    }
    
    Dùng async để xử lý concurrent connections từ nhiều clients
    trong nhiều phòng khác nhau.
    """

    def __init__(self) -> None:
        """Khởi tạo ConnectionManager với cấu trúc per-room."""
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, room_id: str, user_id: str, websocket: WebSocket) -> None:
        """
        Chấp nhận và đăng ký một kết nối WebSocket mới cho một phòng.
        
        Args:
            room_id: ID của phòng chat
            user_id: ID của user
            websocket: WebSocket connection object từ client
        """
        await websocket.accept()
        
        # Tạo phòng nếu chưa tồn tại
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        
        # Thêm user vào phòng
        self.active_connections[room_id][user_id] = websocket
        logger.info(f"[CONNECT] User {user_id[:8]}... vào room {room_id[:8]}... ({len(self.active_connections[room_id])} members)")

    def disconnect(self, room_id: str, user_id: str) -> None:
        """
        Gỡ bỏ một kết nối WebSocket khỏi phòng.
        
        Args:
            room_id: ID của phòng chat
            user_id: ID của user
        """
        if room_id in self.active_connections:
            if user_id in self.active_connections[room_id]:
                del self.active_connections[room_id][user_id]
                logger.info(f"[DISCONNECT] User {user_id[:8]}... rời room {room_id[:8]}... ({len(self.active_connections[room_id])} members còn lại)")
            
            # Xóa phòng nếu không còn member nào
            if len(self.active_connections[room_id]) == 0:
                del self.active_connections[room_id]
                logger.info(f"[ROOM EMPTY] Room {room_id[:8]}... đã trở thành trống")

    async def broadcast_to_room(self, room_id: str, message: dict) -> None:
        """
        Gửi message đến tất cả clients trong một phòng cụ thể (broadcast).
        
        Nếu một client gặp lỗi (connection mất), nó sẽ bị loại khỏi danh sách.
        
        Args:
            room_id: ID của phòng chat
            message: Dictionary chứa dữ liệu gửi đi, sẽ được convert thành JSON
        
        Example:
            await manager.broadcast_to_room(room_id, {
                "type": "message",
                "sender_id": "user1",
                "content": "Hello everyone!",
                "timestamp": "2026-04-09T..."
            })
        """
        if room_id not in self.active_connections:
            logger.debug(f"[BROADCAST] Room {room_id[:8]}... không có members nào")
            return
        
        # Danh sách lưu các user bị lỗi để xóa sau
        disconnected_users = []
        
        for user_id, connection in self.active_connections[room_id].items():
            try:
                await connection.send_json(message)
            except Exception as e:
                # Nếu gửi message thất bại, đánh dấu user này đã mất kết nối
                logger.warning(f"[BROADCAST ERROR] Lỗi gửi tới user {user_id[:8]}...: {e}")
                disconnected_users.append(user_id)
        
        # Xóa các connections bị lỗi khỏi danh sách
        for user_id in disconnected_users:
            if user_id in self.active_connections[room_id]:
                del self.active_connections[room_id][user_id]
                logger.info(f"[BROADCAST CLEANUP] Removed user {user_id[:8]}... from room {room_id[:8]}...")

    async def send_personal_message(
        self, 
        room_id: str,
        user_id: str,
        message: dict
    ) -> None:
        """
        Gửi message cá nhân cho một user cụ thể trong một phòng.
        
        Args:
            room_id: ID của phòng chat
            user_id: ID của user nhận message
            message: Dictionary chứa dữ liệu gửi đi
        
        Example:
            await manager.send_personal_message(room_id, user_id, {
                "type": "error",
                "content": "Lỗi xác thực"
            })
        """
        if room_id not in self.active_connections:
            logger.warning(f"[SEND_PERSONAL] Room {room_id[:8]}... không tồn tại")
            return
        
        if user_id not in self.active_connections[room_id]:
            logger.warning(f"[SEND_PERSONAL] User {user_id[:8]}... không trong room {room_id[:8]}...")
            return
        
        try:
            websocket = self.active_connections[room_id][user_id]
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"[SEND_PERSONAL ERROR] Lỗi gửi tới user {user_id}: {e}")
            # Loại bỏ user nếu gặp lỗi
            self.disconnect(room_id, user_id)

    def get_room_member_count(self, room_id: str) -> int:
        """
        Lấy số lượng members đang kết nối trong một phòng.
        
        Args:
            room_id: ID của phòng chat
        
        Returns:
            Số lượng WebSocket connections hoạt động trong phòng
        """
        return len(self.active_connections.get(room_id, {}))

    def get_connection_count(self) -> int:
        """
        Lấy tổng số lượng connections tất cả clients đang kết nối (all rooms).
        
        Returns:
            Tổng số lượng WebSocket connections hoạt động
        """
        total = 0
        for room_id, members in self.active_connections.items():
            total += len(members)
        return total

    async def send_to_others_in_room(
        self, 
        room_id: str,
        message: dict, 
        exclude_user_id: str
    ) -> None:
        """
        Gửi message đến tất cả users trong phòng ngoại trừ một user cụ thể.
        
        Args:
            room_id: ID của phòng chat
            message: Dictionary chứa dữ liệu gửi đi
            exclude_user_id: ID của user cần loại bỏ khỏi broadcast
        
        Example:
            await manager.send_to_others_in_room(room_id, message, current_user_id)
        """
        if room_id not in self.active_connections:
            return
        
        disconnected_users = []
        
        for user_id, connection in self.active_connections[room_id].items():
            # Bỏ qua user gửi message
            if user_id == exclude_user_id:
                continue
            
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"[SEND_TO_OTHERS ERROR] Lỗi gửi tới user {user_id[:8]}...: {e}")
                disconnected_users.append(user_id)
        
        # Xóa các connections bị lỗi
        for user_id in disconnected_users:
            if user_id in self.active_connections[room_id]:
                del self.active_connections[room_id][user_id]

    def get_room_ids(self) -> List[str]:
        """
        Lấy danh sách tất cả room IDs hiện có connections.
        
        Returns:
            List of room IDs
        """
        return list(self.active_connections.keys())

    def get_room_members(self, room_id: str) -> List[str]:
        """
        Lấy danh sách user IDs đang kết nối trong một phòng.
        
        Args:
            room_id: ID của phòng chat
        
        Returns:
            List of user IDs
        """
        return list(self.active_connections.get(room_id, {}).keys())



# Shared singleton instance for use across the app
connection_manager = ConnectionManager()
