"""
Cryptography Bridge: IOCTL Interface to Kernel Driver + Mock Implementation

Cây cầu giao tiếp giữa Python (User-mode) và Kernel Driver.
- IOCTL calls sang Kernel Driver để MD5 hash và AES encrypt/decrypt
- Mock implementation dùng thư viện cryptography cho development/testing
- Async wrapper để tránh tắc nghẽn event loop
"""

import ctypes
import hashlib
import logging
import os
from typing import Optional, Tuple
from enum import IntEnum
import asyncio
from concurrent.futures import ThreadPoolExecutor
import platform

logger = logging.getLogger(__name__)

# ==================== IOCTL Codes Definition ====================

class IOCTLOperation(IntEnum):
    """IOCTL operation codes (phải khớp với Kernel Driver)"""
    IOCTL_HASH_MD5 = 0x00000001
    IOCTL_ENCRYPT_AES = 0x00000002
    IOCTL_DECRYPT_AES = 0x00000003


# ==================== ctypes Structures (Data Alignment) ====================

class MD5HashBuffer(ctypes.Structure):
    """
    Buffer structure cho MD5 hashing.
    
    PHẢI khớp tuyệt đối với struct trong C driver:
        typedef struct _MD5HashBuffer {
            ULONG dataLen;
            UCHAR data[256];
            UCHAR hash[32];  // MD5 hash output
        } MD5HashBuffer;
    
    Data alignment:
    - ULONG (uint32): 4 bytes
    - UCHAR[256]: 256 bytes
    - UCHAR[32]: 32 bytes
    Total: 4 + 256 + 32 = 292 bytes
    """
    _fields_ = [
        ("dataLen", ctypes.c_uint32),
        ("data", ctypes.c_ubyte * 256),
        ("hash", ctypes.c_ubyte * 32),
    ]


class AESBuffer(ctypes.Structure):
    """
    Buffer structure cho AES encrypt/decrypt.
    
    PHẢI khớp với struct trong C driver:
        typedef struct _AESBuffer {
            ULONG operation;  // 1=encrypt, 2=decrypt
            ULONG dataLen;
            UCHAR key[32];    // AES-256 key
            UCHAR iv[16];     // IV
            UCHAR data[512];  // Input data
            UCHAR output[512]; // Output data
        } AESBuffer;
    """
    _fields_ = [
        ("operation", ctypes.c_uint32),
        ("dataLen", ctypes.c_uint32),
        ("key", ctypes.c_ubyte * 32),
        ("iv", ctypes.c_ubyte * 16),
        ("data", ctypes.c_ubyte * 512),
        ("output", ctypes.c_ubyte * 512),
    ]


# ==================== Crypto Bridge Class ====================

class CryptoBridge:
    """
    Cây cầu giao tiếp với Kernel Driver.
    
    Cơ chế hoạt động:
    1. Thử load Kernel Driver (Windows KMDF hoặc Linux LKM)
    2. Nếu thành công → Sử dụng driver thực
    3. Nếu thất bại → Fallback sang mock implementation
    
    Async support:
    - IOCTL calls là đồng bộ (blocking)
    - Dùng run_in_executor để không tắc event loop
    """

    def __init__(self) -> None:
        """Initialize CryptoBridge and attempt to load driver."""
        self.driver_available = False
        self.dll = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Lấy tên OS hiện tại
        self.os_name = platform.system()
        self.os_version = platform.version()
        
        logger.info(f"🖥️  Operating System: {self.os_name}")
        logger.info(f"📌 OS Version: {self.os_version}")
        
        # Try to load driver based on OS
        if self.os_name == "Windows":
            logger.info("🔧 Loading Windows KMDF driver...")
            self._load_windows_driver()
        elif self.os_name == "Linux":
            logger.info("🔧 Loading Linux LKM driver...")
            self._load_linux_driver()
        elif self.os_name == "Darwin":
            logger.warning("⚠️  macOS detected - driver support not implemented")
            self.driver_available = False
        else:
            logger.warning(f"⚠️  Unknown OS: {self.os_name}")
            self.driver_available = False
        
        if self.driver_available:
            logger.info("✅ Real cryptography driver loaded successfully!")
        else:
            logger.warning("⚠️  Using mock cryptography implementation (development only)")

    def _load_windows_driver(self) -> None:
        """
        Load Windows KMDF driver.
        
        Tên driver: CryptoChatDriver.dll hoặc crypto_chat_driver.sys
        Path: Có thể ở System32, local folder, hoặc registry location
        
        Windows-specific:
        - Sử dụng ctypes.CDLL() để load DLL
        - Gọi exported functions từ DLL
        - Sử dụng DeviceIoControl thông qua DLL wrapper
        """
        try:
            logger.info("   📍 Starting Windows driver search...")
            
            # Try load từ multiple paths
            possible_paths = [
                "CryptoChatDriver.dll",
                "crypto_chat_driver.dll",
                os.path.join(os.path.dirname(__file__), "CryptoChatDriver.dll"),
                "C:\\Windows\\System32\\CryptoChatDriver.dll",
                "C:\\Program Files\\CryptoChatDriver\\CryptoChatDriver.dll",
            ]
            
            for path in possible_paths:
                try:
                    logger.info(f"   ↳ Trying: {path}")
                    self.dll = ctypes.CDLL(path)
                    self.driver_available = True
                    logger.info(f"   ✅ Windows KMDF driver loaded from: {path}")
                    return
                except OSError as e:
                    logger.debug(f"   ✗ Not found: {path}")
                    continue
            
            logger.warning("   ❌ Windows KMDF driver not found on any path")
            logger.info("   💡 To use real driver, ensure CryptoChatDriver.dll is installed")
            
        except Exception as e:
            logger.warning(f"   ✗ Exception loading Windows driver: {e}")
            logger.info("   💡 Will use mock implementation instead")

    def _load_linux_driver(self) -> None:
        """
        Load Linux LKM (Loadable Kernel Module) driver.
        
        Device file: /dev/crypto_chat_driver
        Ioctl interface via device file
        
        Linux-specific:
        - Kiểm tra /dev/crypto_chat_driver device file
        - Sử dụng fcntl.ioctl() để gửi IOCTL commands
        - Các buffer struct tương tự Windows nhưng sử dụng ioctl syscall
        """
        try:
            logger.info("   📍 Starting Linux LKM driver search...")
            
            possible_devices = [
                "/dev/crypto_chat_driver",
                "/dev/crypto_driver",
                "/dev/crypto_chat",
            ]
            
            for device_path in possible_devices:
                logger.info(f"   ↳ Checking: {device_path}")
                if os.path.exists(device_path):
                    try:
                        # Test device file is accessible
                        with open(device_path, "rb") as f:
                            pass
                        self.driver_available = True
                        self.device_path = device_path
                        logger.info(f"   ✅ Linux LKM driver found at: {device_path}")
                        return
                    except PermissionError:
                        logger.warning(f"   ❌ Permission denied: {device_path}")
                        logger.info("   💡 Try: sudo chmod 666 /dev/crypto_chat_driver")
                    except Exception as e:
                        logger.warning(f"   ✗ Error accessing {device_path}: {e}")
                else:
                    logger.debug(f"   ✗ Device not found: {device_path}")
            
            logger.warning("   ❌ Linux LKM driver not found")
            logger.info("   💡 To use real driver:")
            logger.info("      1. Build and load kernel module: insmod crypto_chat_driver.ko")
            logger.info("      2. Device file should appear at /dev/crypto_chat_driver")
            logger.info("      3. Set permissions: sudo chmod 666 /dev/crypto_chat_driver")
            
        except Exception as e:
            logger.warning(f"   ✗ Exception loading Linux driver: {e}")
            logger.info("   💡 Will use mock implementation instead")

    async def hash_password_with_driver(self, password: str) -> str:
        """
        Hash password dùng Kernel Driver hoặc fallback sang mock.
        
        Args:
            password: Plain text password
        
        Returns:
            MD5 hash (32 hex characters)
        
        Process:
            1. Đã chuyển password sang bytes
            2. Gửi xuống Driver via IOCTL
            3. Driver trả về hash 32 bytes
            4. Convert thành hex string
            5. Return hex string
        """
        loop = asyncio.get_event_loop()
        
        if self.driver_available:
            try:
                password_bytes = password.encode("utf-8")
                hash_result = await loop.run_in_executor(
                    self.executor,
                    self._hash_via_driver,
                    password_bytes,
                )
                return hash_result
            except Exception as e:
                logger.warning(f"Driver hash failed: {e}, falling back to mock")
        
        # Fallback sang mock
        return await loop.run_in_executor(
            self.executor,
            self._hash_mock,
            password,
        )

    async def encrypt_aes_with_driver(
        self,
        plaintext: bytes,
        key: bytes,
        iv: bytes,
    ) -> bytes:
        """
        Encrypt dữ liệu dùng AES-256-CBC (Kernel Driver).
        
        Args:
            plaintext: Dữ liệu cần mã hóa
            key: AES key (32 bytes cho AES-256)
            iv: Initialization vector (16 bytes)
        
        Returns:
            Encrypted ciphertext
        """
        loop = asyncio.get_event_loop()
        
        if self.driver_available and len(plaintext) <= 512:
            try:
                result = await loop.run_in_executor(
                    self.executor,
                    self._encrypt_via_driver,
                    plaintext,
                    key,
                    iv,
                )
                return result
            except Exception as e:
                logger.warning(f"Driver encrypt failed: {e}, falling back to mock")
        
        # Fallback sang mock
        return await loop.run_in_executor(
            self.executor,
            self._encrypt_mock,
            plaintext,
            key,
            iv,
        )

    async def decrypt_aes_with_driver(
        self,
        ciphertext: bytes,
        key: bytes,
        iv: bytes,
    ) -> bytes:
        """
        Decrypt dữ liệu dùng AES-256-CBC (Kernel Driver).
        
        Args:
            ciphertext: Dữ liệu đã mã hóa
            key: AES key (32 bytes)
            iv: Initialization vector (16 bytes)
        
        Returns:
            Decrypted plaintext
        """
        loop = asyncio.get_event_loop()
        
        if self.driver_available and len(ciphertext) <= 512:
            try:
                result = await loop.run_in_executor(
                    self.executor,
                    self._decrypt_via_driver,
                    ciphertext,
                    key,
                    iv,
                )
                return result
            except Exception as e:
                logger.warning(f"Driver decrypt failed: {e}, falling back to mock")
        
        # Fallback sang mock
        return await loop.run_in_executor(
            self.executor,
            self._decrypt_mock,
            ciphertext,
            key,
            iv,
        )

    # ==================== Driver Implementation ====================

    def _hash_via_driver(self, password_bytes: bytes) -> str:
        """
        Thực tế gọi IOCTL xuống Kernel Driver để MD5 hash.
        
        Synchronous function sẽ được chạy trong executor.
        
        Windows: Gọi DLL exported function via ctypes
        Linux: Gọi device file ioctl
        """
        if not self.driver_available:
            raise RuntimeError("Driver not available")
        
        if self.os_name == "Windows":
            return self._hash_via_windows_driver(password_bytes)
        elif self.os_name == "Linux":
            return self._hash_via_linux_driver(password_bytes)
        else:
            raise RuntimeError(f"Unsupported OS: {self.os_name}")
    
    def _hash_via_windows_driver(self, password_bytes: bytes) -> str:
        """Windows-specific MD5 hash via KMDF driver DLL"""
        if not self.dll:
            raise RuntimeError("Driver DLL not loaded")
        
        # Tạo buffer structure
        buffer = MD5HashBuffer()
        buffer.dataLen = len(password_bytes)
        
        # Copy dữ liệu vào buffer
        if len(password_bytes) > 256:
            raise ValueError("Password too long (max 256 bytes)")
        
        for i, byte in enumerate(password_bytes):
            buffer.data[i] = byte
        
        # Gọi IOCTL via DLL function
        try:
            hash_func = self.dll.HashMD5
            hash_func.argtypes = [ctypes.POINTER(MD5HashBuffer)]
            hash_func.restype = ctypes.c_int
            
            logger.debug(f"[Windows] Calling HashMD5 for {len(password_bytes)} bytes")
            result = hash_func(ctypes.byref(buffer))
            
            if result != 0:
                raise RuntimeError(f"[Windows] Driver returned error code: {result}")
            
            hash_bytes = bytes(buffer.hash)
            logger.debug(f"[Windows] Hash result: {hash_bytes.hex()}")
            return hash_bytes.hex()
            
        except AttributeError:
            raise RuntimeError("[Windows] Driver function HashMD5 not found")
    
    def _hash_via_linux_driver(self, password_bytes: bytes) -> str:
        """Linux-specific MD5 hash via ioctl device file"""
        try:
            import fcntl
            
            if len(password_bytes) > 256:
                raise ValueError("Password too long (max 256 bytes)")
            
            # Tạo buffer
            buffer = MD5HashBuffer()
            buffer.dataLen = len(password_bytes)
            for i, byte in enumerate(password_bytes):
                buffer.data[i] = byte
            
            # Gọi ioctl
            logger.debug(f"[Linux] Calling ioctl IOCTL_HASH_MD5 for {len(password_bytes)} bytes")
            
            with open(self.device_path, "rb+") as f:
                fcntl.ioctl(f, IOCTLOperation.IOCTL_HASH_MD5, buffer)
            
            hash_bytes = bytes(buffer.hash)
            logger.debug(f"[Linux] Hash result: {hash_bytes.hex()}")
            return hash_bytes.hex()
            
        except ImportError:
            raise RuntimeError("[Linux] fcntl module not available")
        except Exception as e:
            raise RuntimeError(f"[Linux] ioctl failed: {e}")

    def _encrypt_via_driver(
        self,
        plaintext: bytes,
        key: bytes,
        iv: bytes,
    ) -> bytes:
        """
        Gọi IOCTL xuống Driver để AES encrypt.
        
        Windows: Gọi DLL function
        Linux: Gọi device file ioctl
        """
        if not self.driver_available:
            raise RuntimeError("Driver not available")
        
        if self.os_name == "Windows":
            return self._encrypt_via_windows_driver(plaintext, key, iv)
        elif self.os_name == "Linux":
            return self._encrypt_via_linux_driver(plaintext, key, iv)
        else:
            raise RuntimeError(f"Unsupported OS: {self.os_name}")
    
    def _encrypt_via_windows_driver(
        self,
        plaintext: bytes,
        key: bytes,
        iv: bytes,
    ) -> bytes:
        """Windows-specific AES encrypt via KMDF driver"""
        if not self.dll:
            raise RuntimeError("Driver DLL not loaded")
        
        buffer = AESBuffer()
        buffer.operation = 1  # 1=encrypt
        buffer.dataLen = len(plaintext)
        
        if len(plaintext) > 512 or len(key) != 32 or len(iv) != 16:
            raise ValueError("Invalid crypto parameters")
        
        for i, byte in enumerate(plaintext):
            buffer.data[i] = byte
        for i, byte in enumerate(key):
            buffer.key[i] = byte
        for i, byte in enumerate(iv):
            buffer.iv[i] = byte
        
        try:
            encrypt_func = self.dll.EncryptAES
            encrypt_func.argtypes = [ctypes.POINTER(AESBuffer)]
            encrypt_func.restype = ctypes.c_int
            
            logger.debug(f"[Windows] Calling EncryptAES for {len(plaintext)} bytes")
            result = encrypt_func(ctypes.byref(buffer))
            
            if result != 0:
                raise RuntimeError(f"[Windows] Driver returned error code: {result}")
            
            logger.debug(f"[Windows] Encryption successful")
            return bytes(buffer.output[:buffer.dataLen])
            
        except AttributeError:
            raise RuntimeError("[Windows] Driver function EncryptAES not found")
    
    def _encrypt_via_linux_driver(
        self,
        plaintext: bytes,
        key: bytes,
        iv: bytes,
    ) -> bytes:
        """Linux-specific AES encrypt via ioctl"""
        try:
            import fcntl
            
            if len(plaintext) > 512 or len(key) != 32 or len(iv) != 16:
                raise ValueError("Invalid crypto parameters")
            
            buffer = AESBuffer()
            buffer.operation = 1  # 1=encrypt
            buffer.dataLen = len(plaintext)
            
            for i, byte in enumerate(plaintext):
                buffer.data[i] = byte
            for i, byte in enumerate(key):
                buffer.key[i] = byte
            for i, byte in enumerate(iv):
                buffer.iv[i] = byte
            
            logger.debug(f"[Linux] Calling ioctl IOCTL_ENCRYPT_AES for {len(plaintext)} bytes")
            
            with open(self.device_path, "rb+") as f:
                fcntl.ioctl(f, IOCTLOperation.IOCTL_ENCRYPT_AES, buffer)
            
            logger.debug(f"[Linux] Encryption successful")
            return bytes(buffer.output[:buffer.dataLen])
            
        except ImportError:
            raise RuntimeError("[Linux] fcntl module not available")
        except Exception as e:
            raise RuntimeError(f"[Linux] ioctl failed: {e}")

    def _decrypt_via_driver(
        self,
        ciphertext: bytes,
        key: bytes,
        iv: bytes,
    ) -> bytes:
        """
        Gọi IOCTL xuống Driver để AES decrypt.
        
        Windows: Gọi DLL function
        Linux: Gọi device file ioctl
        """
        if not self.driver_available:
            raise RuntimeError("Driver not available")
        
        if self.os_name == "Windows":
            return self._decrypt_via_windows_driver(ciphertext, key, iv)
        elif self.os_name == "Linux":
            return self._decrypt_via_linux_driver(ciphertext, key, iv)
        else:
            raise RuntimeError(f"Unsupported OS: {self.os_name}")
    
    def _decrypt_via_windows_driver(
        self,
        ciphertext: bytes,
        key: bytes,
        iv: bytes,
    ) -> bytes:
        """Windows-specific AES decrypt via KMDF driver"""
        if not self.dll:
            raise RuntimeError("Driver DLL not loaded")
        
        buffer = AESBuffer()
        buffer.operation = 2  # 2=decrypt
        buffer.dataLen = len(ciphertext)
        
        if len(ciphertext) > 512 or len(key) != 32 or len(iv) != 16:
            raise ValueError("Invalid crypto parameters")
        
        for i, byte in enumerate(ciphertext):
            buffer.data[i] = byte
        for i, byte in enumerate(key):
            buffer.key[i] = byte
        for i, byte in enumerate(iv):
            buffer.iv[i] = byte
        
        try:
            decrypt_func = self.dll.DecryptAES
            decrypt_func.argtypes = [ctypes.POINTER(AESBuffer)]
            decrypt_func.restype = ctypes.c_int
            
            logger.debug(f"[Windows] Calling DecryptAES for {len(ciphertext)} bytes")
            result = decrypt_func(ctypes.byref(buffer))
            
            if result != 0:
                raise RuntimeError(f"[Windows] Driver returned error code: {result}")
            
            logger.debug(f"[Windows] Decryption successful")
            return bytes(buffer.output[:buffer.dataLen])
            
        except AttributeError:
            raise RuntimeError("[Windows] Driver function DecryptAES not found")
    
    def _decrypt_via_linux_driver(
        self,
        ciphertext: bytes,
        key: bytes,
        iv: bytes,
    ) -> bytes:
        """Linux-specific AES decrypt via ioctl"""
        try:
            import fcntl
            
            if len(ciphertext) > 512 or len(key) != 32 or len(iv) != 16:
                raise ValueError("Invalid crypto parameters")
            
            buffer = AESBuffer()
            buffer.operation = 2  # 2=decrypt
            buffer.dataLen = len(ciphertext)
            
            for i, byte in enumerate(ciphertext):
                buffer.data[i] = byte
            for i, byte in enumerate(key):
                buffer.key[i] = byte
            for i, byte in enumerate(iv):
                buffer.iv[i] = byte
            
            logger.debug(f"[Linux] Calling ioctl IOCTL_DECRYPT_AES for {len(ciphertext)} bytes")
            
            with open(self.device_path, "rb+") as f:
                fcntl.ioctl(f, IOCTLOperation.IOCTL_DECRYPT_AES, buffer)
            
            logger.debug(f"[Linux] Decryption successful")
            return bytes(buffer.output[:buffer.dataLen])
            
        except ImportError:
            raise RuntimeError("[Linux] fcntl module not available")
        except Exception as e:
            raise RuntimeError(f"[Linux] ioctl failed: {e}")

    # ==================== Mock Implementation ====================

    @staticmethod
    def _hash_mock(password: str) -> str:
        """
        Mock MD5 hash - dùng khi Driver không available.
        
        ⚠️ CHỈ DỮ CHO DEVELOPMENT/TESTING!
        KHÔNG dùng trong production mà không driver thực.
        """
        hash_obj = hashlib.md5(password.encode("utf-8"))
        return hash_obj.hexdigest()

    @staticmethod
    def _encrypt_mock(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
        """
        Mock AES encrypt - dùng library cryptography.
        
        ⚠️ CHỈ DỮ CHO DEVELOPMENT/TESTING!
        """
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            
            if len(key) != 32 or len(iv) != 16:
                raise ValueError("Key must be 32 bytes, IV must be 16 bytes")
            
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend(),
            )
            encryptor = cipher.encryptor()
            
            # Add PKCS7 padding
            from cryptography.hazmat.primitives import padding
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(plaintext) + padder.finalize()
            
            return encryptor.update(padded_data) + encryptor.finalize()
        except ImportError:
            raise RuntimeError("cryptography library not installed")

    @staticmethod
    def _decrypt_mock(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        """
        Mock AES decrypt.
        """
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            
            if len(key) != 32 or len(iv) != 16:
                raise ValueError("Key must be 32 bytes, IV must be 16 bytes")
            
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend(),
            )
            decryptor = cipher.decryptor()
            
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove PKCS7 padding
            from cryptography.hazmat.primitives import padding
            unpadder = padding.PKCS7(128).unpadder()
            
            return unpadder.update(padded_data) + unpadder.finalize()
        except ImportError:
            raise RuntimeError("cryptography library not installed")

    def shutdown(self) -> None:
        """Cleanup resources."""
        self.executor.shutdown(wait=True)


# Global instance
crypto_bridge = CryptoBridge()
