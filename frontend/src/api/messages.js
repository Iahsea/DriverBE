import { request } from './client.js'

/**
 * Giải mã (decrypt) một message đã mã hóa
 * 
 * @param {string} messageId - ID của message cần giải mã
 * @returns {Promise<{id, room_id, sender_id, content_plaintext, created_at, message}>}
 */
async function decryptMessage(messageId) {
    return request(`/api/v1/messages/${messageId}/decrypt`, {
        method: 'POST',
    })
}

/**
 * Lấy chi tiết message
 * 
 * @param {string} messageId - ID của message
 * @returns {Promise<{id, room_id, sender_id, content, content_encrypted, ...}>}
 */
async function getMessage(messageId) {
    return request(`/api/v1/messages/${messageId}`)
}

export { decryptMessage, getMessage }
