#!/usr/bin/env python3
"""Quick test to verify encryption/decryption works after bug fix"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, '/home/user/LAB')

from app.core.crypto_bridge import crypto_bridge

async def test_encryption():
    """Test if encryption and decryption chain works"""
    
    print("=" * 60)
    print("Testing Encryption/Decryption Chain")
    print("=" * 60)
    
    test_message = "Hello from secure chat! 🔐"
    print(f"\n1. Original message: {test_message}")
    
    try:
        # Test encryption
        encrypted_payload = await crypto_bridge.encrypt_message_payload(test_message)
        print(f"2. Encrypted payload (base64): {encrypted_payload[:50]}...")
        print(f"   Payload length: {len(encrypted_payload)} chars")
        
        # Decode to see actual bytes
        import base64
        payload_bytes = base64.b64decode(encrypted_payload)
        print(f"   Payload bytes length: {len(payload_bytes)} bytes")
        print(f"   IV (first 16 bytes): {payload_bytes[:16].hex()}")
        print(f"   Ciphertext length: {len(payload_bytes[16:])} bytes")
        
        if len(payload_bytes) == 16:
            print("   ❌ ERROR: Payload is only 16 bytes (IV only, no ciphertext)!")
        else:
            print("   ✅ Payload contains both IV and ciphertext")
        
        # Test decryption
        decrypted_message = await crypto_bridge.decrypt_message_payload(encrypted_payload)
        print(f"\n3. Decrypted message: {decrypted_message}")
        
        # Verify
        if decrypted_message == test_message:
            print("\n✅ SUCCESS: Encryption/Decryption working correctly!")
            return True
        else:
            print(f"\n❌ ERROR: Decrypted message doesn't match original")
            print(f"   Expected: {test_message}")
            print(f"   Got:      {decrypted_message}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_encryption())
    sys.exit(0 if result else 1)
