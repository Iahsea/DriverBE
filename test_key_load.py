#!/usr/bin/env python3
"""Debug key loading and encryption"""

import os
from dotenv import load_dotenv

load_dotenv()

# Check what key is loaded
key_hex = os.getenv("AES_KEY_HEX")
print(f"AES_KEY_HEX from env: {key_hex}")
print(f"Length: {len(key_hex) if key_hex else 'None'}")

if key_hex:
    try:
        key_bytes = bytes.fromhex(key_hex)
        print(f"Converted to {len(key_bytes)} bytes")
        print(f"Key hex: {key_bytes.hex()}")
    except Exception as e:
        print(f"ERROR converting hex to bytes: {e}")
