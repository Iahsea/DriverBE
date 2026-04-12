#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <string.h>
#include <linux/ioctl.h>

#define CRYPTO_IOCTL_MAGIC 'c'

struct aes_buffer {
    unsigned int operation;
    unsigned int dataLen;
    unsigned char key[32];
    unsigned char iv[16];
    unsigned char data[512];
    unsigned char output[512];
};

#define IOCTL_ENCRYPT_AES _IOW(CRYPTO_IOCTL_MAGIC, 2, struct aes_buffer)
#define IOCTL_DECRYPT_AES _IOW(CRYPTO_IOCTL_MAGIC, 3, struct aes_buffer)

int main() {
    int fd = open("/dev/crypto_chat_driver", O_RDWR);
    if (fd < 0) {
        perror("open failed");
        return 1;
    }

    struct aes_buffer buf;
    memset(&buf, 0, sizeof(buf));
    
    // Plaintext
    char plaintext[] = "Hello world pad!";
    unsigned char key[] = {
        0xa1, 0xb2, 0xc3, 0xd4, 0xe5, 0xf6, 0x47, 0x48,
        0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x50, 0x51,
        0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
        0x5a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f, 0x60, 0x61
    };
    unsigned char iv[] = {
        0x33, 0x34, 0x76, 0x1e, 0x74, 0xfe, 0x6f, 0xf8,
        0x5a, 0x27, 0x20, 0xe9, 0x6a, 0xc4, 0x45, 0x45
    };
    
    buf.operation = 1;  // encrypt
    buf.dataLen = 16;
    memcpy(buf.data, plaintext, 16);
    memcpy(buf.key, key, 32);
    memcpy(buf.iv, iv, 16);
    
    printf("Before ioctl:\n");
    printf("dataLen: %u\n", buf.dataLen);
    printf("data: ");
    for (int i = 0; i < 16; i++) printf("%02x ", buf.data[i]);
    printf("\n");
    printf("output: ");
    for (int i = 0; i < 16; i++) printf("%02x ", buf.output[i]);
    printf("\n\n");
    
    if (ioctl(fd, IOCTL_ENCRYPT_AES, &buf) < 0) {
        perror("ioctl failed");
        close(fd);
        return 1;
    }
    
    printf("ioctl returned: %d\n", ioctl(fd, IOCTL_ENCRYPT_AES, &buf));
    
    printf("After ioctl:\n");
    printf("dataLen: %u\n", buf.dataLen);
    printf("output: ");
    for (int i = 0; i < 16; i++) printf("%02x ", buf.output[i]);
    printf("\n\n");
    
    // Test decryption
    printf("=== DECRYPTION TEST ===\n");
    struct aes_buffer buf_dec;
    memset(&buf_dec, 0, sizeof(buf_dec));
    memcpy(buf_dec.data, buf.output, 16);  // Use encrypted data
    memcpy(buf_dec.key, key, 32);
    memcpy(buf_dec.iv, iv, 16);
    buf_dec.operation = 2;  // decrypt
    buf_dec.dataLen = 16;
    
    printf("Before decrypt: ");
    for (int i = 0; i < 16; i++) printf("%02x ", buf_dec.data[i]);
    printf("\n");
    
    if (ioctl(fd, IOCTL_DECRYPT_AES, &buf_dec) < 0) {
        perror("decrypt ioctl failed");
        close(fd);
        return 1;
    }
    
    printf("After decrypt: ");
    for (int i = 0; i < 16; i++) printf("%02x ", buf_dec.output[i]);
    printf("\n");
    printf("As text: ");
    for (int i = 0; i < 16; i++) printf("%c", buf_dec.output[i]);
    printf("\n");
    
    close(fd);
    return 0;
}
