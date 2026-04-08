"""
NotificationManager - Quản lý WebSocket connections cho real-time notifications

Cung cấp broadcast notifications tới users khi có sự kiện friend (gửi lời mời, chấp nhận, từ chối, ...)
"""

import logging
from fastapi import WebSocket
from typing import Dict

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Quản lý WebSocket connections cho real-time notifications.
    
    Cấu trúc: {user_id: websocket}
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, user_id: str, websocket: WebSocket):
        """
        Khi user kết nối tới /ws/notifications
        """
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"✓ User {user_id[:8]}... connected to notifications")
    
    def disconnect(self, user_id: str):
        """
        Khi user disconnect khỏi /ws/notifications
        """
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"✓ User {user_id[:8]}... disconnected from notifications")
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """
        Gửi thông báo cho một user cụ thể (nếu đang online).
        
        Args:
            user_id: ID của user nhận notification
            message: JSON object chứa notification data
                {
                    "type": "friend_request|friend_request_accepted|...",
                    "from_user_id": "...",
                    "from_username": "...",
                    "user_id": "...",
                    "username": "...",
                    "request_id": "...",
                    "message": "...",
                    "timestamp": "2026-04-09T10:30:00"
                }
        """
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
                logger.info(f"✓ Notification ({message.get('type')}) sent to {user_id[:8]}...")
            except Exception as e:
                logger.error(f"Error sending notification to {user_id[:8]}...: {e}")
                # Disconnect user nếu có lỗi gửi
                self.disconnect(user_id)
        else:
            # User offline - notification bị miss
            logger.debug(f"User {user_id[:8]}... offline - notification skipped")
    
    async def broadcast_to_users(self, user_ids: list, message: dict):
        """
        Gửi thông báo cho nhiều users cùng lúc.
        
        Args:
            user_ids: List các user IDs
            message: JSON object chứa notification data
        """
        for user_id in user_ids:
            if user_id in self.active_connections:
                await self.broadcast_to_user(user_id, message)
    
    def is_user_online(self, user_id: str) -> bool:
        """Kiểm tra user đang online không"""
        return user_id in self.active_connections
    
    def get_online_users(self) -> list:
        """Trả về danh sách user IDs đang online"""
        return list(self.active_connections.keys())


# Global instance
notification_manager = NotificationManager()
