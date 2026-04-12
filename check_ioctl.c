#include <stdio.h>
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

int main() {
    unsigned int encrypt = _IOW(CRYPTO_IOCTL_MAGIC, 2, struct aes_buffer);
    unsigned int decrypt = _IOW(CRYPTO_IOCTL_MAGIC, 3, struct aes_buffer);
    
    printf("Struct size: %zu\n", sizeof(struct aes_buffer));
    printf("IOCTL_ENCRYPT_AES: 0x%08x\n", encrypt);
    printf("IOCTL_DECRYPT_AES: 0x%08x\n", decrypt);
    
    return 0;
}
