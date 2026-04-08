#!/usr/bin/env python
"""
Debug Script - Kiểm tra Crypto Bridge và OS Configuration

Sử dụng: python check_crypto_config.py
"""

import platform
import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def check_os_info():
    """Check OS information"""
    print_header("🖥️  Operating System Information")
    
    print(f"  System: {platform.system()}")
    print(f"  Release: {platform.release()}")
    print(f"  Version: {platform.version()}")
    print(f"  Machine: {platform.machine()}")
    print(f"  Python: {platform.python_version()}")
    
    os_name = platform.system()
    if os_name == "Windows":
        print(f"\n  ✅ Windows detected - Will use KMDF driver (.dll)")
    elif os_name == "Linux":
        print(f"\n  ✅ Linux detected - Will use LKM driver (/dev device)")
    elif os_name == "Darwin":
        print(f"\n  ⚠️  macOS detected - Driver support not implemented")
    else:
        print(f"\n  ❌ Unknown OS - Driver may not work")

def check_windows_driver():
    """Check for Windows KMDF driver"""
    print_header("🔍 Windows KMDF Driver Search")
    
    possible_paths = [
        "CryptoChatDriver.dll",
        "crypto_chat_driver.dll",
        os.path.join(os.path.dirname(__file__), "app", "core", "CryptoChatDriver.dll"),
        "C:\\Windows\\System32\\CryptoChatDriver.dll",
        "C:\\Program Files\\CryptoChatDriver\\CryptoChatDriver.dll",
    ]
    
    print("\n  Searching in these paths:\n")
    found = False
    
    for path in possible_paths:
        exists = os.path.exists(path)
        status = "✅ FOUND" if exists else "❌ NOT FOUND"
        print(f"    {status}: {path}")
        if exists:
            found = True
            size = os.path.getsize(path)
            print(f"             Size: {size} bytes")
    
    if not found:
        print("\n  💡 Driver not found. To install:")
        print("     1. Build CryptoChatDriver.dll from C++ project")
        print("     2. Copy to one of the search paths above")
        print("     3. Restart the application")
    else:
        print("\n  ✅ Driver found! Will use real cryptography.")

def check_linux_driver():
    """Check for Linux LKM driver"""
    print_header("🔍 Linux LKM Driver Search")
    
    possible_devices = [
        "/dev/crypto_chat_driver",
        "/dev/crypto_driver",
        "/dev/crypto_chat",
    ]
    
    print("\n  Searching for device files:\n")
    found = False
    
    for device in possible_devices:
        exists = os.path.exists(device)
        status = "✅ FOUND" if exists else "❌ NOT FOUND"
        print(f"    {status}: {device}")
        
        if exists:
            try:
                # Check permissions
                stat_info = os.stat(device)
                mode = stat_info.st_mode
                readable = bool(mode & 0o400)
                writable = bool(mode & 0o200)
                
                print(f"             Readable: {'✅' if readable else '❌'}")
                print(f"             Writable: {'✅' if writable else '❌'}")
                
                if readable and writable:
                    found = True
                else:
                    print(f"             Fix: sudo chmod 666 {device}")
            except Exception as e:
                print(f"             Error checking: {e}")
    
    if not found:
        print("\n  💡 Driver not found. To install:")
        print("     1. Build kernel module from C source")
        print("     2. Load: sudo insmod crypto_chat_driver.ko")
        print("     3. Set permissions: sudo chmod 666 /dev/crypto_chat_driver")
        print("     4. Restart the application")
    else:
        print("\n  ✅ Driver found! Will use real cryptography.")

def check_crypto_bridge():
    """Test CryptoBridge initialization"""
    print_header("🔐 CryptoBridge Initialization Test")
    
    try:
        print("\n  Loading CryptoBridge...\n")
        from app.core.crypto_bridge import crypto_bridge
        
        print(f"  OS Detected: {crypto_bridge.os_name}")
        print(f"  Driver Available: {'✅ YES' if crypto_bridge.driver_available else '❌ NO'}")
        print(f"  Using: {'🎖️  Real Driver' if crypto_bridge.driver_available else '📝 Mock Implementation'}")
        
        if crypto_bridge.os_name == "Windows" and not crypto_bridge.driver_available:
            print("\n  💡 Switch to real driver by installing CryptoChatDriver.dll")
        elif crypto_bridge.os_name == "Linux" and not crypto_bridge.driver_available:
            print("\n  💡 Switch to real driver by loading kernel module")
        
        return True
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        return False

def main():
    """Main function"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "  Crypto Bridge Configuration Checker".center(68) + "║")
    print("║" + "  Backend Secure Chat System".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    sys.path.insert(0, script_dir)
    
    # Run checks
    check_os_info()
    
    os_name = platform.system()
    if os_name == "Windows":
        check_windows_driver()
    elif os_name == "Linux":
        check_linux_driver()
    
    check_crypto_bridge()
    
    print_header("📋 Summary")
    print("""
  Windows Development:
    ✓ Uses KMDF driver (.dll) from Windows Driver Kit
    ✓ CryptoChatDriver.dll should be in search paths
    ✓ Falls back to mock implementation if driver missing
  
  Linux Deployment:
    ✓ Uses LKM driver kernel module
    ✓ Device file: /dev/crypto_chat_driver
    ✓ Falls back to mock implementation if module missing
  
  Mock Implementation:
    ✓ Uses Python cryptography library
    ✓ For development/testing only
    ✓ MD5 via hashlib
    ✓ AES-256-CBC via cryptography.hazmat
  
  Next Steps:
    1. Check that CryptoBridge detected your OS correctly
    2. If driver not found, ensure it's installed
    3. Run the backend server: python -m uvicorn main:app --reload
    4. Check server logs for driver status messages
""")
    
    print("\n")

if __name__ == "__main__":
    main()
