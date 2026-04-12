#!/usr/bin/env python3
"""Check what crypto mode is being used"""

import sys
sys.path.insert(0, '/home/user/LAB')

from app.core.crypto_bridge import crypto_bridge

print(f"Driver available: {crypto_bridge.driver_available}")
print(f"OS: {crypto_bridge.os_name}")
if hasattr(crypto_bridge, 'device_path'):
    print(f"Device path: {crypto_bridge.device_path}")
