#!/usr/bin/env python3
"""Test kernel driver directly"""

import os
import fcntl
import ctypes
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AESBuffer(ctypes.Structure):
    _fields_ = [
        ("operation", ctypes.c_uint32),
        ("dataLen", ctypes.c_uint32),
        ("key", ctypes.c_ubyte * 32),
        ("iv", ctypes.c_ubyte * 16),
        ("data", ctypes.c_ubyte * 512),
        ("output", ctypes.c_ubyte * 512),
    ]

IOCTL_ENCRYPT_AES = 0x00000002
IOCTL_DECRYPT_AES = 0x00000003

# Test data
plaintext = b"Hello world pad!"  # Exactly 16 bytes
key = bytes.fromhex("a1b2c3d4e5f647484a4b4c4d4e4f505152535455565758595a5b5c5d5e5f6061")
iv = bytes.fromhex("3334761e74fe6ff85a2720e96ac44545")

print(f"Testing kernel driver AES encryption")
print(f"Plaintext: {plaintext.hex()} ({len(plaintext)} bytes)")
print(f"Key: {key.hex()[:32]}... ({len(key)} bytes)")
print(f"IV: {iv.hex()} ({len(iv)} bytes)")

try:
    buffer = AESBuffer()
    buffer.operation = 1  # 1=encrypt
    buffer.dataLen = len(plaintext)
    
    for i, byte in enumerate(plaintext):
        buffer.data[i] = byte
    for i, byte in enumerate(key):
        buffer.key[i] = byte
    for i, byte in enumerate(iv):
        buffer.iv[i] = byte
    
    print("\nCalling ioctl IOCTL_ENCRYPT_AES...")
    fd = os.open("/dev/crypto_chat_driver", os.O_RDWR)
    try:
        fcntl.ioctl(fd, IOCTL_ENCRYPT_AES, buffer)
    finally:
        os.close(fd)
    
    print("✅ IOCTL succeeded")
    ciphertext = bytes(buffer.output[:buffer.dataLen])
    print(f"Ciphertext: {ciphertext.hex()}")
    
    if ciphertext == b'\x00' * len(plaintext):
        print("❌ ERROR: Ciphertext is all zeros!")
    else:
        print("✅ Ciphertext looks valid")
        
        # Try to decrypt
        buffer2 = AESBuffer()
        buffer2.operation = 2  # 2=decrypt
        buffer2.dataLen = len(ciphertext)
        
        for i, byte in enumerate(ciphertext):
            buffer2.data[i] = byte
        for i, byte in enumerate(key):
            buffer2.key[i] = byte
        for i, byte in enumerate(iv):
            buffer2.iv[i] = byte
        
        print("\nCalling ioctl IOCTL_DECRYPT_AES...")
        fd = os.open("/dev/crypto_chat_driver", os.O_RDWR)
        try:
            fcntl.ioctl(fd, IOCTL_DECRYPT_AES, buffer2)
        finally:
            os.close(fd)
        
        print("✅ IOCTL succeeded")
        decrypted = bytes(buffer2.output[:buffer2.dataLen])
        print(f"Decrypted: {decrypted.hex()}")
        
        if decrypted == plaintext:
            print("✅ Decryption successful!")
        else:
            print("❌ Decryption failed!")
            
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
