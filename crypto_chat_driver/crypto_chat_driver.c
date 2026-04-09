// SPDX-License-Identifier: GPL-2.0
#include <linux/module.h>
#include <linux/init.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/device.h>
#include <linux/uaccess.h>
#include <linux/string.h>
#include <linux/types.h>

#define DEVICE_NAME "crypto_chat_driver"

#define IOCTL_HASH_MD5    1
#define IOCTL_ENCRYPT_AES 2
#define IOCTL_DECRYPT_AES 3

struct md5_hash_buffer {
    u32 dataLen;
    u8 data[256];
    u8 hash[32];
};

struct aes_buffer {
    u32 operation; /* 1=encrypt, 2=decrypt */
    u32 dataLen;
    u8 key[32];
    u8 iv[16];
    u8 data[512];
    u8 output[512];
};

static dev_t dev_num;
static struct cdev crypto_cdev;
static struct class *crypto_class;

/* ==================== MD5 (manual implementation) ==================== */

struct md5_ctx {
    u32 state[4];
    u64 bitcount;
    u8 buffer[64];
};

static const u32 md5_k[64] = {
    0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee,
    0xf57c0faf, 0x4787c62a, 0xa8304613, 0xfd469501,
    0x698098d8, 0x8b44f7af, 0xffff5bb1, 0x895cd7be,
    0x6b901122, 0xfd987193, 0xa679438e, 0x49b40821,
    0xf61e2562, 0xc040b340, 0x265e5a51, 0xe9b6c7aa,
    0xd62f105d, 0x02441453, 0xd8a1e681, 0xe7d3fbc8,
    0x21e1cde6, 0xc33707d6, 0xf4d50d87, 0x455a14ed,
    0xa9e3e905, 0xfcefa3f8, 0x676f02d9, 0x8d2a4c8a,
    0xfffa3942, 0x8771f681, 0x6d9d6122, 0xfde5380c,
    0xa4beea44, 0x4bdecfa9, 0xf6bb4b60, 0xbebfbc70,
    0x289b7ec6, 0xeaa127fa, 0xd4ef3085, 0x04881d05,
    0xd9d4d039, 0xe6db99e5, 0x1fa27cf8, 0xc4ac5665,
    0xf4292244, 0x432aff97, 0xab9423a7, 0xfc93a039,
    0x655b59c3, 0x8f0ccc92, 0xffeff47d, 0x85845dd1,
    0x6fa87e4f, 0xfe2ce6e0, 0xa3014314, 0x4e0811a1,
    0xf7537e82, 0xbd3af235, 0x2ad7d2bb, 0xeb86d391
};

static const u8 md5_s[64] = {
    7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
    5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20,
    4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
    6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21
};

static inline u32 md5_rotl(u32 x, u8 n)
{
    return (x << n) | (x >> (32 - n));
}

static void md5_transform(u32 state[4], const u8 block[64])
{
    u32 a = state[0];
    u32 b = state[1];
    u32 c = state[2];
    u32 d = state[3];
    u32 m[16];
    int i;

    for (i = 0; i < 16; i++) {
        int j = i * 4;
        m[i] = (u32)block[j] | ((u32)block[j + 1] << 8) |
               ((u32)block[j + 2] << 16) | ((u32)block[j + 3] << 24);
    }

    for (i = 0; i < 64; i++) {
        u32 f, g;

        if (i < 16) {
            f = (b & c) | (~b & d);
            g = i;
        } else if (i < 32) {
            f = (d & b) | (~d & c);
            g = (5 * i + 1) & 0x0f;
        } else if (i < 48) {
            f = b ^ c ^ d;
            g = (3 * i + 5) & 0x0f;
        } else {
            f = c ^ (b | ~d);
            g = (7 * i) & 0x0f;
        }

        f = f + a + md5_k[i] + m[g];
        a = d;
        d = c;
        c = b;
        b = b + md5_rotl(f, md5_s[i]);
    }

    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
}

static void md5_init(struct md5_ctx *ctx)
{
    ctx->state[0] = 0x67452301;
    ctx->state[1] = 0xefcdab89;
    ctx->state[2] = 0x98badcfe;
    ctx->state[3] = 0x10325476;
    ctx->bitcount = 0;
}

static void md5_update(struct md5_ctx *ctx, const u8 *data, u32 len)
{
    u32 index = (u32)((ctx->bitcount >> 3) & 0x3f);
    u32 part_len = 64 - index;
    u32 i = 0;

    ctx->bitcount += ((u64)len << 3);

    if (len >= part_len) {
        memcpy(&ctx->buffer[index], data, part_len);
        md5_transform(ctx->state, ctx->buffer);
        for (i = part_len; i + 63 < len; i += 64)
            md5_transform(ctx->state, &data[i]);
        index = 0;
    }

    memcpy(&ctx->buffer[index], &data[i], len - i);
}

static void md5_final(struct md5_ctx *ctx, u8 out[16])
{
    u8 padding[64] = { 0x80 };
    u8 length[8];
    u32 index = (u32)((ctx->bitcount >> 3) & 0x3f);
    u32 pad_len = (index < 56) ? (56 - index) : (120 - index);
    u64 bits = ctx->bitcount;
    int i;

    for (i = 0; i < 8; i++) {
        length[i] = (u8)(bits & 0xff);
        bits >>= 8;
    }

    md5_update(ctx, padding, pad_len);
    md5_update(ctx, length, 8);

    for (i = 0; i < 4; i++) {
        out[i * 4] = (u8)(ctx->state[i] & 0xff);
        out[i * 4 + 1] = (u8)((ctx->state[i] >> 8) & 0xff);
        out[i * 4 + 2] = (u8)((ctx->state[i] >> 16) & 0xff);
        out[i * 4 + 3] = (u8)((ctx->state[i] >> 24) & 0xff);
    }
}

static int do_md5(const u8 *data, u32 len, u8 *out32)
{
    struct md5_ctx ctx;

    md5_init(&ctx);
    md5_update(&ctx, data, len);
    md5_final(&ctx, out32);

    memset(out32 + 16, 0, 16);
    return 0;
}

/* ==================== AES-256-CBC (manual implementation) ==================== */

static const u8 aes_sbox[256] = {
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16
};

static const u8 aes_inv_sbox[256] = {
    0x52,0x09,0x6a,0xd5,0x30,0x36,0xa5,0x38,0xbf,0x40,0xa3,0x9e,0x81,0xf3,0xd7,0xfb,
    0x7c,0xe3,0x39,0x82,0x9b,0x2f,0xff,0x87,0x34,0x8e,0x43,0x44,0xc4,0xde,0xe9,0xcb,
    0x54,0x7b,0x94,0x32,0xa6,0xc2,0x23,0x3d,0xee,0x4c,0x95,0x0b,0x42,0xfa,0xc3,0x4e,
    0x08,0x2e,0xa1,0x66,0x28,0xd9,0x24,0xb2,0x76,0x5b,0xa2,0x49,0x6d,0x8b,0xd1,0x25,
    0x72,0xf8,0xf6,0x64,0x86,0x68,0x98,0x16,0xd4,0xa4,0x5c,0xcc,0x5d,0x65,0xb6,0x92,
    0x6c,0x70,0x48,0x50,0xfd,0xed,0xb9,0xda,0x5e,0x15,0x46,0x57,0xa7,0x8d,0x9d,0x84,
    0x90,0xd8,0xab,0x00,0x8c,0xbc,0xd3,0x0a,0xf7,0xe4,0x58,0x05,0xb8,0xb3,0x45,0x06,
    0xd0,0x2c,0x1e,0x8f,0xca,0x3f,0x0f,0x02,0xc1,0xaf,0xbd,0x03,0x01,0x13,0x8a,0x6b,
    0x3a,0x91,0x11,0x41,0x4f,0x67,0xdc,0xea,0x97,0xf2,0xcf,0xce,0xf0,0xb4,0xe6,0x73,
    0x96,0xac,0x74,0x22,0xe7,0xad,0x35,0x85,0xe2,0xf9,0x37,0xe8,0x1c,0x75,0xdf,0x6e,
    0x47,0xf1,0x1a,0x71,0x1d,0x29,0xc5,0x89,0x6f,0xb7,0x62,0x0e,0xaa,0x18,0xbe,0x1b,
    0xfc,0x56,0x3e,0x4b,0xc6,0xd2,0x79,0x20,0x9a,0xdb,0xc0,0xfe,0x78,0xcd,0x5a,0xf4,
    0x1f,0xdd,0xa8,0x33,0x88,0x07,0xc7,0x31,0xb1,0x12,0x10,0x59,0x27,0x80,0xec,0x5f,
    0x60,0x51,0x7f,0xa9,0x19,0xb5,0x4a,0x0d,0x2d,0xe5,0x7a,0x9f,0x93,0xc9,0x9c,0xef,
    0xa0,0xe0,0x3b,0x4d,0xae,0x2a,0xf5,0xb0,0xc8,0xeb,0xbb,0x3c,0x83,0x53,0x99,0x61,
    0x17,0x2b,0x04,0x7e,0xba,0x77,0xd6,0x26,0xe1,0x69,0x14,0x63,0x55,0x21,0x0c,0x7d
};

static const u8 aes_rcon[15] = {
    0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36,0x6c,0xd8,0xab,0x4d
};

static inline u8 aes_xtime(u8 x)
{
    return (u8)((x << 1) ^ ((x & 0x80) ? 0x1b : 0x00));
}

static u8 aes_gf_mul(u8 a, u8 b)
{
    u8 res = 0;
    while (b) {
        if (b & 1)
            res ^= a;
        a = aes_xtime(a);
        b >>= 1;
    }
    return res;
}

static void aes_sub_bytes(u8 *state)
{
    int i;
    for (i = 0; i < 16; i++)
        state[i] = aes_sbox[state[i]];
}

static void aes_inv_sub_bytes(u8 *state)
{
    int i;
    for (i = 0; i < 16; i++)
        state[i] = aes_inv_sbox[state[i]];
}

static void aes_shift_rows(u8 *s)
{
    u8 t;

    t = s[1];  s[1]  = s[5];  s[5]  = s[9];  s[9]  = s[13]; s[13] = t;
    t = s[2];  s[2]  = s[10]; s[10] = t;     t = s[6];     s[6]  = s[14]; s[14] = t;
    t = s[3];  s[3]  = s[15]; s[15] = s[11]; s[11] = s[7]; s[7]  = t;
}

static void aes_inv_shift_rows(u8 *s)
{
    u8 t;

    t = s[13]; s[13] = s[9];  s[9]  = s[5];  s[5]  = s[1];  s[1]  = t;
    t = s[2];  s[2]  = s[10]; s[10] = t;     t = s[6];     s[6]  = s[14]; s[14] = t;
    t = s[3];  s[3]  = s[7];  s[7]  = s[11]; s[11] = s[15]; s[15] = t;
}

static void aes_mix_columns(u8 *s)
{
    int i;
    for (i = 0; i < 4; i++) {
        int idx = i * 4;
        u8 a0 = s[idx];
        u8 a1 = s[idx + 1];
        u8 a2 = s[idx + 2];
        u8 a3 = s[idx + 3];

        s[idx]     = (u8)(aes_gf_mul(a0, 2) ^ aes_gf_mul(a1, 3) ^ a2 ^ a3);
        s[idx + 1] = (u8)(a0 ^ aes_gf_mul(a1, 2) ^ aes_gf_mul(a2, 3) ^ a3);
        s[idx + 2] = (u8)(a0 ^ a1 ^ aes_gf_mul(a2, 2) ^ aes_gf_mul(a3, 3));
        s[idx + 3] = (u8)(aes_gf_mul(a0, 3) ^ a1 ^ a2 ^ aes_gf_mul(a3, 2));
    }
}

static void aes_inv_mix_columns(u8 *s)
{
    int i;
    for (i = 0; i < 4; i++) {
        int idx = i * 4;
        u8 a0 = s[idx];
        u8 a1 = s[idx + 1];
        u8 a2 = s[idx + 2];
        u8 a3 = s[idx + 3];

        s[idx]     = (u8)(aes_gf_mul(a0, 14) ^ aes_gf_mul(a1, 11) ^ aes_gf_mul(a2, 13) ^ aes_gf_mul(a3, 9));
        s[idx + 1] = (u8)(aes_gf_mul(a0, 9)  ^ aes_gf_mul(a1, 14) ^ aes_gf_mul(a2, 11) ^ aes_gf_mul(a3, 13));
        s[idx + 2] = (u8)(aes_gf_mul(a0, 13) ^ aes_gf_mul(a1, 9)  ^ aes_gf_mul(a2, 14) ^ aes_gf_mul(a3, 11));
        s[idx + 3] = (u8)(aes_gf_mul(a0, 11) ^ aes_gf_mul(a1, 13) ^ aes_gf_mul(a2, 9)  ^ aes_gf_mul(a3, 14));
    }
}

static void aes_add_round_key(u8 *state, const u8 *round_key)
{
    int i;
    for (i = 0; i < 16; i++)
        state[i] ^= round_key[i];
}

static void aes_key_expand_256(const u8 *key, u8 *round_keys)
{
    int i;
    u8 temp[4];
    int bytes = 32;
    int rcon_iter = 1;

    memcpy(round_keys, key, 32);

    while (bytes < 240) {
        temp[0] = round_keys[bytes - 4];
        temp[1] = round_keys[bytes - 3];
        temp[2] = round_keys[bytes - 2];
        temp[3] = round_keys[bytes - 1];

        if ((bytes % 32) == 0) {
            u8 t = temp[0];
            temp[0] = temp[1];
            temp[1] = temp[2];
            temp[2] = temp[3];
            temp[3] = t;

            temp[0] = aes_sbox[temp[0]];
            temp[1] = aes_sbox[temp[1]];
            temp[2] = aes_sbox[temp[2]];
            temp[3] = aes_sbox[temp[3]];

            temp[0] ^= aes_rcon[rcon_iter++];
        } else if ((bytes % 32) == 16) {
            temp[0] = aes_sbox[temp[0]];
            temp[1] = aes_sbox[temp[1]];
            temp[2] = aes_sbox[temp[2]];
            temp[3] = aes_sbox[temp[3]];
        }

        for (i = 0; i < 4; i++) {
            round_keys[bytes] = round_keys[bytes - 32] ^ temp[i];
            bytes++;
        }
    }
}

static void aes_encrypt_block(const u8 *in, u8 *out, const u8 *round_keys)
{
    u8 state[16];
    int round;

    memcpy(state, in, 16);
    aes_add_round_key(state, round_keys);

    for (round = 1; round < 14; round++) {
        aes_sub_bytes(state);
        aes_shift_rows(state);
        aes_mix_columns(state);
        aes_add_round_key(state, round_keys + (round * 16));
    }

    aes_sub_bytes(state);
    aes_shift_rows(state);
    aes_add_round_key(state, round_keys + (14 * 16));

    memcpy(out, state, 16);
}

static void aes_decrypt_block(const u8 *in, u8 *out, const u8 *round_keys)
{
    u8 state[16];
    int round;

    memcpy(state, in, 16);
    aes_add_round_key(state, round_keys + (14 * 16));

    for (round = 13; round > 0; round--) {
        aes_inv_shift_rows(state);
        aes_inv_sub_bytes(state);
        aes_add_round_key(state, round_keys + (round * 16));
        aes_inv_mix_columns(state);
    }

    aes_inv_shift_rows(state);
    aes_inv_sub_bytes(state);
    aes_add_round_key(state, round_keys);

    memcpy(out, state, 16);
}

static int do_aes_cbc(const u8 *in, u32 len, const u8 *key, const u8 *iv,
                      u8 *out, bool encrypt)
{
    u8 round_keys[240];
    u8 prev[16];
    u8 block[16];
    u32 i;
    int j;

    if (len % 16 != 0)
        return -EINVAL;

    aes_key_expand_256(key, round_keys);
    memcpy(prev, iv, 16);

    if (encrypt) {
        for (i = 0; i < len; i += 16) {
            for (j = 0; j < 16; j++)
                block[j] = in[i + j] ^ prev[j];
            aes_encrypt_block(block, out + i, round_keys);
            memcpy(prev, out + i, 16);
        }
    } else {
        for (i = 0; i < len; i += 16) {
            aes_decrypt_block(in + i, block, round_keys);
            for (j = 0; j < 16; j++)
                out[i + j] = block[j] ^ prev[j];
            memcpy(prev, in + i, 16);
        }
    }

    return 0;
}

static long crypto_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
    if (cmd == IOCTL_HASH_MD5) {
        struct md5_hash_buffer buf;
        int ret;

        if (copy_from_user(&buf, (void __user *)arg, sizeof(buf)))
            return -EFAULT;
        if (buf.dataLen > 256)
            return -EINVAL;

        ret = do_md5(buf.data, buf.dataLen, buf.hash);
        if (ret)
            return ret;

        if (copy_to_user((void __user *)arg, &buf, sizeof(buf)))
            return -EFAULT;
        return 0;
    }

    if (cmd == IOCTL_ENCRYPT_AES || cmd == IOCTL_DECRYPT_AES) {
        struct aes_buffer buf;
        int ret;
        bool encrypt = (cmd == IOCTL_ENCRYPT_AES);

        if (copy_from_user(&buf, (void __user *)arg, sizeof(buf)))
            return -EFAULT;
        if (buf.dataLen > 512)
            return -EINVAL;

        ret = do_aes_cbc(buf.data, buf.dataLen, buf.key, buf.iv, buf.output, encrypt);
        if (ret)
            return ret;

        if (copy_to_user((void __user *)arg, &buf, sizeof(buf)))
            return -EFAULT;
        return 0;
    }

    return -ENOTTY;
}

static int crypto_open(struct inode *inode, struct file *file)
{
    return 0;
}

static int crypto_release(struct inode *inode, struct file *file)
{
    return 0;
}

static const struct file_operations crypto_fops = {
    .owner = THIS_MODULE,
    .open = crypto_open,
    .release = crypto_release,
    .unlocked_ioctl = crypto_ioctl,
};

static int __init crypto_init(void)
{
    int ret;
    struct device *dev_ret;

    ret = alloc_chrdev_region(&dev_num, 0, 1, DEVICE_NAME);
    if (ret)
        return ret;

    cdev_init(&crypto_cdev, &crypto_fops);
    ret = cdev_add(&crypto_cdev, dev_num, 1);
    if (ret)
        goto unregister_region;

    crypto_class = class_create(DEVICE_NAME);
    if (IS_ERR(crypto_class)) {
        ret = PTR_ERR(crypto_class);
        goto del_cdev;
    }

    dev_ret = device_create(crypto_class, NULL, dev_num, NULL, DEVICE_NAME);
    if (IS_ERR(dev_ret)) {
        ret = PTR_ERR(dev_ret);
        goto destroy_class;
    }

    pr_info("crypto_chat_driver loaded: /dev/%s\n", DEVICE_NAME);
    return 0;

destroy_class:
    class_destroy(crypto_class);
del_cdev:
    cdev_del(&crypto_cdev);
unregister_region:
    unregister_chrdev_region(dev_num, 1);
    return ret;
}

static void __exit crypto_exit(void)
{
    device_destroy(crypto_class, dev_num);
    class_destroy(crypto_class);
    cdev_del(&crypto_cdev);
    unregister_chrdev_region(dev_num, 1);
    pr_info("crypto_chat_driver unloaded\n");
}

module_init(crypto_init);
module_exit(crypto_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Generated by GitHub Copilot");
MODULE_DESCRIPTION("Crypto Chat LKM with MD5 and AES-256-CBC IOCTLs");
