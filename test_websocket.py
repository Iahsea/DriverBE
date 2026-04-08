"""
Test WebSocket connection
Chạy file này để test xem WebSocket server có hoạt động không
"""

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("❌ websockets chưa cài. Cài bằng: pip install websockets")
    sys.exit(1)


async def test_websocket():
    """Test kết nối WebSocket"""
    uri = "ws://localhost:8000/ws/chat"
    
    try:
        print(f"🔌 Đang kết nối đến {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Kết nối WebSocket thành công!")
            print("-" * 50)
            
            # Gửi message đầu tiên
            message = "Hello from test client!"
            print(f"\n📤 Gửi: {message}")
            await websocket.send(message)
            
            # Nhận response từ server
            print("\n📥 Nhận response từ server:")
            print("-" * 50)
            
            count = 0
            while count < 5:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    data = json.loads(response)
                    
                    msg_type = data.get("type", "unknown")
                    msg_content = data.get("message", "")
                    timestamp = data.get("timestamp", "")
                    
                    print(f"\n[{msg_type.upper()}]")
                    print(f"  Content: {msg_content}")
                    print(f"  Time: {timestamp}")
                    
                    count += 1
                except asyncio.TimeoutError:
                    print("\n⏱️  Timeout: không nhận được message trong 3 giây")
                    break
            
            print("\n" + "=" * 50)
            print("✅ TEST THÀNH CÔNG - WebSocket hoạt động bình thường!")
            print("=" * 50)
            
    except ConnectionRefusedError:
        print("\n❌ LỖI: Không thể kết nối!")
        print("   Đảm bảo server đang chạy: python -m uvicorn main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ LỖI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 50)
    print("WebSocket Connection Test")
    print("=" * 50)
    asyncio.run(test_websocket())
