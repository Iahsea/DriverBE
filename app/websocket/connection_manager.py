"""
WebSocket Connection Manager

Quản lý các kết nối WebSocket của clients, hỗ trợ:
- Thêm/xóa connections
- Gửi message broadcast đến tất cả clients
- Gửi message cá nhân cho một client cụ thể
"""

from fastapi import WebSocket
from typing import List


class ConnectionManager:
    """
    Quản lý các kết nối WebSocket đang hoạt động.
    
    Dùng async để xử lý concurrent connections từ nhiều clients.
    Mỗi connection được lưu trong danh sách active_connections.
    """

    def __init__(self) -> None:
        """Khởi tạo ConnectionManager với danh sách connections rỗng."""
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """
        Chấp nhận và đăng ký một kết nối WebSocket mới.
        
        Args:
            websocket: WebSocket connection object từ client
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[CONNECT] Client kết nối. Tổng: {len(self.active_connections)} connections")

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Gỡ bỏ một kết nối WebSocket khỏi danh sách active.
        
        Args:
            websocket: WebSocket connection object cần xóa
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[DISCONNECT] Client ngắt kết nối. Còn lại: {len(self.active_connections)} connections")

    async def broadcast(self, message: dict) -> None:
        """
        Gửi message đến tất cả clients đang kết nối (broadcast).
        
        Nếu một client gặp lỗi (connection mất), nó sẽ bị loại khỏi danh sách.
        
        Args:
            message: Dictionary chứa dữ liệu gửi đi, sẽ được convert thành JSON
        
        Example:
            await manager.broadcast({
                "type": "chat",
                "sender": "user1",
                "content": "Hello everyone!"
            })
        """
        # Danh sách lưu các connections bị lỗi để xóa sau
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                # Nếu gửi message thất bại, đánh dấu kết nối này đã mất
                print(f"[BROADCAST ERROR] Lỗi gửi message: {e}")
                disconnected.append(connection)
        
        # Xóa các connections bị lỗi khỏi danh sách
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

    async def send_personal_message(
        self, 
        message: dict, 
        websocket: WebSocket
    ) -> None:
        """
        Gửi message cá nhân cho một client cụ thể.
        
        Args:
            message: Dictionary chứa dữ liệu gửi đi
            websocket: WebSocket connection của client nhận message
        
        Example:
            await manager.send_personal_message(
                {"type": "error", "content": "Lỗi xác thực"},
                client_socket
            )
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"[SEND_PERSONAL ERROR] Lỗi gửi message cá nhân: {e}")
            # Loại bỏ connection nếu gặp lỗi
            self.disconnect(websocket)

    def get_connection_count(self) -> int:
        """
        Lấy số lượng clients đang kết nối.
        
        Returns:
            Số lượng WebSocket connections hoạt động
        """
        return len(self.active_connections)

    async def send_to_others(
        self, 
        message: dict, 
        exclude_websocket: WebSocket
    ) -> None:
        """
        Gửi message đến tất cả clients ngoại trừ một client cụ thể.
        
        Hữu ích khi client gửi message, ta gửi lại cho mọi người khác.
        
        Args:
            message: Dictionary chứa dữ liệu gửi đi
            exclude_websocket: WebSocket connection cần loại bỏ khỏi broadcast
        
        Example:
            await manager.send_to_others(
                {"type": "chat", "sender": "user1", "content": "Hello!"},
                current_client_socket
            )
        """
        disconnected = []
        
        for connection in self.active_connections:
            # Bỏ qua chính connection gửi message
            if connection == exclude_websocket:
                continue
            
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[SEND_TO_OTHERS ERROR] Lỗi gửi message: {e}")
                disconnected.append(connection)
        
        # Xóa các connections bị lỗi
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)
