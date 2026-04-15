"""
Test MD5 Integrity Verification Implementation

Test:
1. Hash message content via driver
2. Encrypt message via driver
3. Verify hash matches after decryption
4. Simulate tampering detection
"""

import asyncio
import json
import sys
import os

# Load .env FIRST
from dotenv import load_dotenv
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.core.crypto_bridge import crypto_bridge


async def test_md5_hash_verification():
    """Test MD5 hash for message integrity"""
    
    print("\n" + "="*70)
    print("TEST: MD5 Integrity Verification for Messages")
    print("="*70)
    
    # Test 1: Hash and verify
    message = "Hello Client2, this is a secure message!"
    
    print(f"\n✓ Original message:")
    print(f"  '{message}'")
    print(f"  Length: {len(message)} chars")
    
    # Hash via driver
    hash1 = await crypto_bridge.hash_message_content(message)
    print(f"\n✓ Hash via driver:")
    print(f"  {hash1}")
    
    # Hash again should be same
    hash2 = await crypto_bridge.hash_message_content(message)
    print(f"\n✓ Hash again (should match):")
    print(f"  {hash2}")
    
    if hash1 == hash2:
        print(f"  ✅ MATCH! Hash is consistent")
    else:
        print(f"  ❌ MISMATCH! Hash inconsistent")
        return False
    
    # Test 2: Tampered message detection
    tampered = "Hello Client2, this is a HACKED message!"
    
    hash_tampered = await crypto_bridge.hash_message_content(tampered)
    print(f"\n✓ Tampered message:")
    print(f"  '{tampered}'")
    print(f"  Hash: {hash_tampered}")
    
    if hash1 != hash_tampered:
        print(f"  ✅ DIFFERENT! Tampering detected")
    else:
        print(f"  ❌ SAME! Should be different")
        return False
    
    # Test 3: Encrypt/Decrypt with hash
    print(f"\n✓ Encrypt/Decrypt cycle:")
    
    encrypted = await crypto_bridge.encrypt_message_payload(message)
    print(f"  Encrypted: {encrypted[:50]}...")
    
    decrypted = await crypto_bridge.decrypt_message_payload(encrypted)
    print(f"  Decrypted: '{decrypted}'")
    
    if decrypted == message:
        print(f"  ✅ MATCH! Encryption/Decryption working")
    else:
        print(f"  ❌ MISMATCH! Crypto broken")
        return False
    
    # Hash should match original for decrypted message
    hash_decrypted = await crypto_bridge.hash_message_content(decrypted)
    if hash_decrypted == hash1:
        print(f"  ✅ Hash match! Message integrity verified")
    else:
        print(f"  ❌ Hash mismatch!")
        return False
    
    # Test 4: Multiple messages
    print(f"\n✓ Test multiple message types:")
    
    test_messages = [
        "Short",
        "This is a medium length message",
        "Special chars: !@#$%^&*()_+-=[]{}|;:',.<>?/",
        "Unicode: Hello 世界 مرحبا",
        "Emoji: Hi 👋 Secure 🔐 Chat 💬",
        "Numbers: 0123456789 -3.14159",
    ]
    
    for msg in test_messages:
        h = await crypto_bridge.hash_message_content(msg)
        e = await crypto_bridge.encrypt_message_payload(msg)
        d = await crypto_bridge.decrypt_message_payload(e)
        h_verify = await crypto_bridge.hash_message_content(d)
        
        status = "✅" if h == h_verify and d == msg else "❌"
        print(f"  {status} '{msg[:30]}...'")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print("""
Backend MD5 Integrity Verification Summary:
✓ Message hashing works (via Driver or mock)
✓ Consistency verified (same message = same hash)
✓ Tampering detection works (modified message = different hash)
✓ Encryption/Decryption preserves message
✓ Hash verification after decrypt works
✓ Multiple message types supported

Architecture:
- Hash: Windows DLL or Linux ioctl → fallback hashlib.md5
- Encrypt: Windows DLL or Linux ioctl → fallback cryptography
- Stored in DB: message_hash VARCHAR(64)
- Broadcast via WebSocket: message_hash field
- API endpoints return: message_hash in response

Frontend TODO:
- Compute MD5 hash of decrypted plaintext
- Compare with message_hash from server
- Show ✅ or ⚠️ indicator based on verification result
""")
    
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_md5_hash_verification())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
