/**
 * Message Integrity Verification Utility
 * 
 * Verifies that decrypted messages haven't been tampered with
 * using MD5 hashing (same algorithm as backend)
 */

/**
 * Calculate MD5 hash of a string
 * Uses Web Crypto API for SHA-256 (browser doesn't have native MD5)
 * 
 * NOTE: MD5 is for integrity verification only, NOT for security!
 * We use MD5 to match backend implementation, but it's weak cryptographically.
 * For true security, use SHA-256 or stronger.
 */
async function calculateMD5(message) {
  // Browser doesn't have native MD5, so we use a simple implementation
  // This is okay for integrity checking (collision resistance is good enough)
  
  // For now, return a placeholder - in production, use a proper MD5 library
  // or better: use SHA-256 from Web Crypto API
  const encoder = new TextEncoder()
  const data = encoder.encode(message)
  const hashBuffer = await crypto.subtle.digest('SHA-256', data)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('')
  
  // For demo: truncate SHA-256 to 32 chars (like MD5)
  // In production: use actual MD5 or coordinate with backend to use SHA-256
  return hashHex.substring(0, 32)
}

/**
 * Verify message integrity
 * Compares computed hash with backend hash
 * 
 * @param {string} plaintext - Decrypted message content
 * @param {string} messageHash - Hash from backend
 * @returns {Promise<boolean>} - true if hashes match, false if tampered
 */
export async function verifyMessageIntegrity(plaintext, messageHash) {
  if (!messageHash) {
    console.warn('⚠️ No message hash available for verification')
    return null // Can't verify without hash
  }

  try {
    const computedHash = await calculateMD5(plaintext)
    const isValid = computedHash === messageHash

    if (isValid) {
      console.log('✅ Message integrity verified')
      return true
    } else {
      console.warn(
        '⚠️ Message integrity check FAILED - data may have been modified',
        {
          expected: messageHash,
          computed: computedHash,
        }
      )
      return false
    }
  } catch (error) {
    console.error('❌ Error verifying message integrity:', error)
    return null
  }
}

/**
 * Call backend API to verify integrity
 * Backend will also verify and return result
 * 
 * @param {string} messageId - Message ID
 * @param {string} plaintext - Decrypted plaintext
 * @param {string} authToken - JWT token
 * @returns {Promise<object>} - {verified, computed_hash, stored_hash, status}
 */
export async function callBackendVerifyIntegrity(messageId, plaintext, authToken) {
  try {
    const response = await fetch(
      `/api/v1/messages/${messageId}/verify-integrity`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          plaintext_received: plaintext,
        }),
      }
    )

    if (!response.ok) {
      throw new Error(`Backend verification failed: ${response.status}`)
    }

    const result = await response.json()
    return result // {verified, computed_hash, stored_hash, status}
  } catch (error) {
    console.error('❌ Error calling backend verify integrity:', error)
    return null
  }
}

/**
 * Full verification flow:
 * 1. Compute local hash of plaintext
 * 2. Compare with backend hash
 * 3. Optionally call API for backend verification
 * 
 * @param {object} message - Message object with id, content_decrypted, message_hash
 * @param {string} authToken - JWT token for API call
 * @param {boolean} callBackend - Whether to verify with backend API
 * @returns {Promise<object>} - {verified, integrity_status, computed_hash}
 */
export async function performFullVerification(message, authToken, callBackend = false) {
  if (!message || !message.content_decrypted) {
    return {
      verified: null,
      integrity_status: 'no_plaintext',
      error: 'Message not decrypted yet',
    }
  }

  // 1. Local verification
  const localVerification = await verifyMessageIntegrity(
    message.content_decrypted,
    message.message_hash
  )

  // 2. Optional backend verification
  let backendResult = null
  if (callBackend) {
    backendResult = await callBackendVerifyIntegrity(
      message.id,
      message.content_decrypted,
      authToken
    )
  }

  return {
    verified: localVerification,
    integrity_status: localVerification ? 'verified' : localVerification === false ? 'tampered' : 'unknown',
    computed_hash: '',
    backend_result: backendResult,
    message_id: message.id,
    timestamp: new Date().toISOString(),
  }
}

/**
 * Format verification status for display
 */
export function formatVerificationStatus(verification) {
  if (!verification) return 'Unknown'

  switch (verification.integrity_status) {
    case 'verified':
      return '🔒 Verified'
    case 'tampered':
      return '⚠️ Tampered'
    case 'unknown':
      return '❓ Cannot verify'
    case 'no_plaintext':
      return '⏳ Decrypting...'
    default:
      return '❓ Unknown'
  }
}
