#!/usr/bin/env python3
"""Detailed debugging of encryption/decryption"""

import asyncio
import sys
import os
import base64
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, '/home/user/LAB')

from app.core.crypto_bridge import crypto_bridge

async def test_with_debug():
    """Test encryption/decryption with detailed debug output"""
    
    test_message = "Hello"
    print(f"Original message: '{test_message}'")
    print(f"Message bytes: {test_message.encode()}")
    
    # Step 1: Pad the message
    plaintext_bytes = test_message.encode("utf-8")
    padded = crypto_bridge._pkcs7_pad(plaintext_bytes)
    print(f"\nAfter PKCS7 padding: {len(padded)} bytes")
    print(f"Padded bytes: {padded.hex()}")
    print(f"Last byte (padding indicator): {padded[-1]}")
    
    # Step 2: Get key and IV
    from app.core.crypto_bridge import CryptoBridge
    bridge = CryptoBridge()
    key = bridge._get_aes_key_from_env()
    iv = os.urandom(16)
    print(f"\nKey: {len(key)} bytes")
    print(f"IV: {len(iv)} bytes - {iv.hex()}")
    
    # Step 3: Encrypt with mock
    ciphertext = await bridge.encrypt_aes_with_driver(padded, key, iv)
    print(f"\nCiphertext: {len(ciphertext)} bytes")
    print(f"Ciphertext hex: {ciphertext.hex()}")
    
    # Step 4: Decrypt with mock
    decrypted_padded = await bridge.decrypt_aes_with_driver(ciphertext, key, iv)
    print(f"\nDecrypted (padded): {len(decrypted_padded)} bytes")
    print(f"Decrypted hex: {decrypted_padded.hex()}")
    
    # Check if they match
    if decrypted_padded == padded:
        print("✅ Decrypted matches original padded data!")
    else:
        print("❌ Decrypted does NOT match original!")
        print(f"   Expected: {padded.hex()}")
        print(f"   Got:      {decrypted_padded.hex()}")
        
        # Check byte by byte
        for i, (exp, got) in enumerate(zip(padded, decrypted_padded)):
            if exp != got:
                print(f"   Byte {i}: expected {exp:02x}, got {got:02x}")
    
    # Step 5: Try to unpad
    try:
        unpadded = bridge._pkcs7_unpad(decrypted_padded)
        print(f"\nUnpadded: {len(unpadded)} bytes")
        print(f"Unpadded hex: {unpadded.hex()}")
        print(f"Unpadded string: '{unpadded.decode('utf-8')}'")
    except Exception as e:
        print(f"\n❌ Error unpadding: {e}")
        print(f"   Decrypted last byte: {decrypted_padded[-1]}")
        print(f"   Length of decrypted: {len(decrypted_padded)}")

asyncio.run(test_with_debug())
