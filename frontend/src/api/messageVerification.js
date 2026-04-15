/**
 * Message Integrity Verification API
 * 
 * Optional backend helper endpoints for Client2 to verify message integrity
 */

import { client } from './client'

/**
 * Verify message integrity via backend
 * 
 * Backend will:
 * 1. Get message from DB
 * 2. Compute hash of plaintext
 * 3. Compare with stored hash
 * 4. Return verification result
 * 
 * @param {string} messageId - Message ID to verify
 * @param {string} plaintext - Decrypted plaintext from Client2
 * @returns {Promise<Object>} - Verification result
 * 
 * @example
 *   const result = await verifyMessageViaBackend('msg-123', 'Hello')
 *   if (result.verified) {
 *     console.log("✅ Backend confirmed message is intact")
 *   }
 */
export async function verifyMessageViaBackend(messageId, plaintext) {
    try {
        const response = await client.post(
            `/api/v1/messages/${messageId}/verify-integrity`,
            {
                plaintext_received: plaintext
            }
        )

        return {
            verified: response.data.verified,
            serverHash: response.data.message_hash,
            message: response.data.message,
            status: response.data.status // 'verified' | 'mismatch' | 'error'
        }
    } catch (error) {
        console.error('Backend verification failed:', error)
        return {
            verified: false,
            message: 'Backend verification error: ' + error.message,
            status: 'error'
        }
    }
}

/**
 * Get message with hash for local verification
 * 
 * @param {string} messageId - Message ID
 * @returns {Promise<Object>} - Message with hash
 */
export async function getMessageHash(messageId) {
    try {
        const response = await client.get(`/api/v1/messages/${messageId}`)
        return {
            id: response.data.id,
            content: response.data.content,
            content_encrypted: response.data.content_encrypted,
            message_hash: response.data.message_hash,
            created_at: response.data.created_at
        }
    } catch (error) {
        console.error('Failed to get message hash:', error)
        throw error
    }
}
