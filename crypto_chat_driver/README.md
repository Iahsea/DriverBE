# Crypto Chat Driver (Linux)

Linux kernel module exposes a char device `/dev/crypto_chat_driver`.
It handles IOCTL commands for MD5 hashing and AES-256-CBC encrypt/decrypt.

## IOCTL Commands

- `IOCTL_HASH_MD5 = 1`
- `IOCTL_ENCRYPT_AES = 2`
- `IOCTL_DECRYPT_AES = 3`

## Structs (must match Python ctypes)

```
struct md5_hash_buffer {
    u32 dataLen;
    u8  data[256];
    u8  hash[32];
};

struct aes_buffer {
    u32 operation; /* 1=encrypt, 2=decrypt */
    u32 dataLen;
    u8  key[32];
    u8  iv[16];
    u8  data[512];
    u8  output[512];
};
```

Notes:
- MD5 digest is 16 bytes; the driver zero-fills the remaining 16 bytes.
- AES input length must be a multiple of 16 bytes; no padding in kernel.

## Build

```
make
```

## Load

```
sudo insmod crypto_chat_driver.ko
sudo chmod 666 /dev/crypto_chat_driver
```

## Unload

```
sudo rmmod crypto_chat_driver
```
