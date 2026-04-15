/**
 * MD5 Hash Utility for Message Integrity Verification
 * 
 * Usage:
 *   const hash = await computeMD5("Hello")
 *   // Returns: "8b1a9953c4611296aaf7a3c47f8a588f"
 */

// Using js-md5 library (npm install js-md5)
// Or implement with crypto-js (npm install crypto-js)

let md5Module = null

/**
 * Initialize MD5 module
 * Tries js-md5 first, then crypto-js as fallback
 */
async function initMD5() {
    if (md5Module) return md5Module

    try {
        // Try js-md5 library
        const md5_lib = await import('js-md5')
        md5Module = md5_lib.default || md5_lib
        console.log('✓ Using js-md5 library for MD5')
        return md5Module
    } catch (e1) {
        console.debug('js-md5 not available, trying crypto-js')
        try {
            // Try crypto-js library
            const CryptoJS = await import('crypto-js')
            md5Module = {
                hash: (text) => CryptoJS.MD5(text).toString()
            }
            console.log('✓ Using crypto-js library for MD5')
            return md5Module
        } catch (e2) {
            console.error('No MD5 library available!')
            throw new Error('MD5 library not found. Install: npm install js-md5')
        }
    }
}

/**
 * Compute MD5 hash of text (for message integrity verification)
 * 
 * @param {string} text - Text to hash
 * @returns {Promise<string>} - MD5 hash (32 hex characters)
 * 
 * @example
 *   const hash = await computeMD5("Hello Client2")
 *   // Returns: "802c21ae4d9853d40ef331b4bb2bb22c"
 */
export async function computeMD5(text) {
    try {
        const md5 = await initMD5()

        if (typeof text !== 'string') {
            throw new TypeError('Input must be a string')
        }

        const hash = md5(text)

        if (!hash || hash.length !== 32) {
            throw new Error('Invalid MD5 hash result')
        }

        return hash
    } catch (error) {
        console.error('MD5 computation failed:', error)
        throw error
    }
}

/**
 * Verify message integrity by comparing hashes
 * 
 * @param {string} plaintext - Decrypted plaintext message
 * @param {string} serverHash - Hash from server (message_hash field)
 * @returns {Promise<Object>} - Verification result
 * 
 * @example
 *   const result = await verifyMessageIntegrity(plaintext, serverHash)
 *   if (result.isValid) {
 *     console.log("✅ Message verified OK")
 *   } else {
 *     console.warn("⚠️ Message integrity check FAILED")
 *   }
 */
export async function verifyMessageIntegrity(plaintext, serverHash) {
    try {
        // 1. Compute hash của plaintext đã decrypt
        const computedHash = await computeMD5(plaintext)

        // 2. So sánh
        const isValid = computedHash === serverHash

        return {
            isValid,
            computedHash,
            serverHash,
            verified: isValid,
            indicator: isValid ? '✅' : '⚠️',
            message: isValid
                ? 'Message integrity verified'
                : 'Message integrity check FAILED - data may have been modified'
        }
    } catch (error) {
        console.error('Message verification failed:', error)
        return {
            isValid: false,
            verified: false,
            indicator: '❌',
            message: 'Verification error: ' + error.message,
            error
        }
    }
}

/**
 * Format verification result for display
 * 
 * @param {Object} verifyResult - Result from verifyMessageIntegrity()
 * @returns {Object} - Formatted result for UI
 */
export function formatVerificationResult(verifyResult) {
    return {
        status: verifyResult.isValid ? 'verified' : 'untrusted',
        icon: verifyResult.indicator,
        message: verifyResult.message,
        color: verifyResult.isValid ? 'green' : 'red',
        showWarning: !verifyResult.isValid
    }
}
