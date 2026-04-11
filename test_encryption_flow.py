"""
Test Real-Time Message Encryption with AES_KEY_HEX from .env

Kiểm tra xem:
1. Biến AES_KEY_HEX có được load từ .env không
2. Quá trình mã hóa tin nhắn có hoạt động bình thường không
3. Giải mã tin nhắn có khôi phục đúng nội dung gốc không
"""

import asyncio
import os
from dotenv import load_dotenv

# Load .env FIRST
load_dotenv()

from app.core.crypto_bridge import crypto_bridge

async def test_encryption_flow():
    """Test the complete encryption/decryption flow"""
    
    print("=" * 70)
    print("🔐 TEST: Real-Time Message Encryption with AES_KEY_HEX")
    print("=" * 70)
    
    # Step 1: Kiểm tra AES_KEY_HEX
    print("\n[1️⃣] Kiểm tra biến AES_KEY_HEX từ .env...")
    aes_key_hex = os.getenv("AES_KEY_HEX")
    
    if aes_key_hex:
        print(f"    ✅ AES_KEY_HEX được load thành công")
        print(f"    📋 Độ dài: {len(aes_key_hex)} ký tự")
        print(f"    🔑 Giá trị: {aes_key_hex}")
        
        # Kiểm tra format
        if len(aes_key_hex) == 64:
            print(f"    ✅ Format đúng (64 hex chars = 32 bytes)")
        else:
            print(f"    ❌ Format sai! Cần đúng 64 ký tự hex, hiện có {len(aes_key_hex)}")
            return False
    else:
        print(f"    ❌ AES_KEY_HEX KHÔNG được load!")
        print(f"    💡 Kiểm tra file .env có chứa AES_KEY_HEX không")
        return False
    
    # Step 2: Test mã hóa tin nhắn đơn giản
    print("\n[2️⃣] Test mã hóa tin nhắn đơn giản...")
    plaintext_messages = [
        "Hello, this is a simple message!",
        "Xin chào từ Việt Nam",
        "Test with special chars: !@#$%^&*()",
        "Short msg",
        "A" * 100,  # Long message
    ]
    
    encryption_results = []
    
    for i, plaintext in enumerate(plaintext_messages, 1):
        try:
            print(f"\n    Test #{i}: {plaintext[:50]}{'...' if len(plaintext) > 50 else ''}")
            payload = await crypto_bridge.encrypt_message_payload(plaintext)
            encryption_results.append({
                'plaintext': plaintext,
                'payload': payload,
                'success': True
            })
            print(f"    ✅ Mã hóa thành công")
            print(f"       Ciphertext: {payload[:50]}...")
        except Exception as e:
            print(f"    ❌ Mã hóa thất bại: {e}")
            encryption_results.append({
                'plaintext': plaintext,
                'error': str(e),
                'success': False
            })
    
    # Step 3: Test giải mã
    print("\n[3️⃣] Test giải mã tin nhắn...")
    decryption_results = []
    
    for i, result in enumerate(encryption_results, 1):
        if result['success']:
            try:
                plaintext = result['plaintext']
                payload = result['payload']
                
                decrypted = await crypto_bridge.decrypt_message_payload(payload)
                
                # Kiểm tra xem decrypted có khớp gốc không
                if decrypted == plaintext:
                    print(f"\n    Test #{i}: ✅ PASS")
                    print(f"       Gốc: {plaintext[:50]}{'...' if len(plaintext) > 50 else ''}")
                    print(f"       Giải mã: {decrypted[:50]}{'...' if len(decrypted) > 50 else ''}")
                    decryption_results.append({'success': True, 'match': True})
                else:
                    print(f"\n    Test #{i}: ❌ FAIL - Nội dung không khớp!")
                    print(f"       Gốc: {plaintext}")
                    print(f"       Giải mã: {decrypted}")
                    decryption_results.append({'success': True, 'match': False})
            except Exception as e:
                print(f"\n    Test #{i}: ❌ FAIL - {e}")
                decryption_results.append({'success': False, 'error': str(e)})
    
    # Step 4: Tóm tắt kết quả
    print("\n" + "=" * 70)
    print("📊 KẾT QUẢ TỔNG KẾT")
    print("=" * 70)
    
    encryption_passed = sum(1 for r in encryption_results if r['success'])
    encryption_total = len(encryption_results)
    
    decryption_passed = sum(1 for r in decryption_results if r.get('match', False))
    decryption_total = len(decryption_results)
    
    print(f"\n✅ Mã hóa: {encryption_passed}/{encryption_total} thành công")
    print(f"✅ Giải mã: {decryption_passed}/{decryption_total} thành công")
    
    all_passed = encryption_passed == encryption_total and decryption_passed == decryption_total
    
    if all_passed:
        print(f"\n🎉 HOÀN TOÀN THÀNH CÔNG! Hệ thống mã hóa tin nhắn hoạt động bình thường.")
        print(f"   - AES_KEY_HEX được load từ .env ✅")
        print(f"   - Quá trình mã hóa hoạt động ✅")
        print(f"   - Quá trình giải mã hoạt động ✅")
    else:
        print(f"\n⚠️ CÓ LỖI! Vui lòng kiểm tra lại.")
    
    print("\n" + "=" * 70)
    
    return all_passed


async def test_driver_status():
    """Check CryptoBridge driver status"""
    print("\n[ℹ️] CryptoBridge Driver Status:")
    print(f"    Driver Available: {crypto_bridge.driver_available}")
    print(f"    OS: {crypto_bridge.os_name}")
    if crypto_bridge.driver_available:
        print(f"    ✅ Sử dụng REAL cryptography driver")
    else:
        print(f"    ⚠️  Sử dụng MOCK cryptography (development mode)")


if __name__ == "__main__":
    # Run tests
    try:
        asyncio.run(test_driver_status())
        result = asyncio.run(test_encryption_flow())
        exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ Lỗi không mong muốn: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
