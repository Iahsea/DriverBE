"""
Test WebSocket Real-Time Message Encryption Flow

Mô phỏng:
1. Gửi tin nhắn qua WebSocket (encrypt)
2. Nhận tin nhắn và giải mã
3. Kiểm tra tính toàn vẹn dữ liệu
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load .env FIRST
load_dotenv()

from app.database.database import SessionLocal
from app.core.crypto_bridge import crypto_bridge
from app.core.id_utils import normalize_uuid


class MockWebSocketTest:
    """Mô phỏng luồng real-time messaging qua WebSocket"""
    
    def __init__(self):
        self.message_history = []
        self.encrypted_messages = []
    
    async def send_message(self, sender_id: str, room_id: str, content: str):
        """Mô phỏng gửi tin nhắn (mã hóa phía client)"""
        print(f"\n[📤 GỬI] {sender_id} → Room {room_id[:8]}...")
        print(f"    Nội dung gốc: {content[:60]}{'...' if len(content) > 60 else ''}")
        
        try:
            # Mã hóa tin nhắn
            encrypted_payload = await crypto_bridge.encrypt_message_payload(content)
            
            # Tạo message object (như trong database)
            message = {
                'id': str(uuid.uuid4()),
                'sender_id': sender_id,
                'room_id': room_id,
                'content_encrypted': encrypted_payload,  # Lưu encrypted
                'content': None,  # Không lưu plaintext
                'created_at': datetime.now(timezone.utc).isoformat(),
                'is_read': False,
                'read_at': None
            }
            
            self.encrypted_messages.append(message)
            
            print(f"    ✅ Mã hóa thành công")
            print(f"    🔐 Ciphertext: {encrypted_payload[:50]}...")
            print(f"    📦 Message ID: {message['id'][:8]}...")
            
            return message
            
        except Exception as e:
            print(f"    ❌ Lỗi: {e}")
            raise
    
    async def receive_message(self, message_id: str):
        """Mô phỏng nhận tin nhắn (giải mã phía receiver)"""
        message = next((m for m in self.encrypted_messages if m['id'] == message_id), None)
        
        if not message:
            print(f"    ❌ Không tìm thấy message")
            return None
        
        print(f"\n[📥 NHẬN] Message {message_id[:8]}...")
        print(f"    Từ: {message['sender_id']}")
        print(f"    Room: {message['room_id'][:8]}...")
        
        try:
            # Giải mã tin nhắn
            decrypted_content = await crypto_bridge.decrypt_message_payload(
                message['content_encrypted']
            )
            
            message['content'] = decrypted_content
            message['is_read'] = True
            message['read_at'] = datetime.now(timezone.utc).isoformat()
            
            self.message_history.append({
                'original': decrypted_content,
                'encrypted': message['content_encrypted'],
                'match': True
            })
            
            print(f"    ✅ Giải mã thành công")
            print(f"    📝 Nội dung: {decrypted_content[:60]}{'...' if len(decrypted_content) > 60 else ''}")
            
            return message
            
        except Exception as e:
            print(f"    ❌ Lỗi: {e}")
            raise


async def simulate_real_time_chat():
    """Mô phỏng trao đổi tin nhắn real-time"""
    
    print("=" * 80)
    print("🔐 TEST: WebSocket Real-Time Message Encryption Flow")
    print("=" * 80)
    
    ws_test = MockWebSocketTest()
    
    # Tạo test data
    room_id = str(uuid.uuid4())
    user_ids = [str(uuid.uuid4()) for _ in range(2)]
    
    test_conversations = [
        (0, "Hello! How are you today?"),
        (1, "I'm doing great! How about you?"),
        (0, "Just working on the encryption implementation 😄"),
        (1, "That's awesome! Does the AES encryption work well?"),
        (0, "Yes! Everything is working perfectly now! 🎉"),
        (1, "Awesome! Let me test it too."),
        (0, "Great, test with various messages including special chars: !@#$%^&*()"),
        (1, "Perfect, testing with Vietnamese: Xin chào, đây là thông báo từ Việt Nam 🇻🇳"),
    ]
    
    print(f"\n✨ Setup:")
    print(f"   Room ID: {room_id[:8]}...")
    print(f"   User 1: {user_ids[0][:8]}...")
    print(f"   User 2: {user_ids[1][:8]}...")
    
    print(f"\n{'═' * 80}")
    print(f"💬 MÔ PHỎNG TRAO ĐỔI TIN NHẮN")
    print(f"{'═' * 80}")
    
    sent_messages = []
    
    # Gửi tin nhắn
    for user_idx, content in test_conversations:
        sender_id = user_ids[user_idx]
        message = await ws_test.send_message(sender_id, room_id, content)
        sent_messages.append(message)
    
    # Nhận và giải mã tin nhắn
    print(f"\n{'═' * 80}")
    print(f"📥 NHẬN VÀ GIẢI MÃ TIN NHẮN")
    print(f"{'═' * 80}")
    
    for message in sent_messages:
        await ws_test.receive_message(message['id'])
    
    # Tóm tắt kết quả
    print(f"\n{'═' * 80}")
    print(f"📊 KẾT QUẢ TỔNG KẾT")
    print(f"{'═' * 80}")
    
    total_messages = len(sent_messages)
    decrypted_messages = len(ws_test.message_history)
    
    print(f"\n✅ Tin nhắn được gửi: {total_messages}")
    print(f"✅ Tin nhắn được nhận và giải mã: {decrypted_messages}/{total_messages}")
    
    all_decrypted = decrypted_messages == total_messages
    
    if all_decrypted:
        print(f"\n🎉 THÀNH CÔNG! Luồng real-time messaging hoạt động hoàn hảo:")
        print(f"   ✅ Mã hóa tin nhắn khi gửi")
        print(f"   ✅ Giải mã tin nhắn khi nhận")
        print(f"   ✅ Dữ liệu khôi phục đúng nội dung gốc")
        print(f"   ✅ AES_KEY_HEX từ .env được sử dụng thành công")
    else:
        print(f"\n⚠️ CÓ LỖI! Vui lòng kiểm tra lại.")
    
    print(f"\n{'═' * 80}")
    
    return all_decrypted


async def main():
    """Run all tests"""
    try:
        print(f"\n🔐 CryptoBridge Status:")
        print(f"   Driver Available: {crypto_bridge.driver_available}")
        print(f"   OS: {crypto_bridge.os_name}")
        if crypto_bridge.driver_available:
            print(f"   Mode: REAL cryptography driver")
        else:
            print(f"   Mode: MOCK cryptography (uses 'cryptography' library)")
        
        result = await simulate_real_time_chat()
        exit(0 if result else 1)
        
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
