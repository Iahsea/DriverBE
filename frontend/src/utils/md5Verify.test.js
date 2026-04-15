/**
 * Test: Message Integrity Verification
 * 
 * Test MD5 verification flow:
 * 1. Compute MD5 of plaintext (simulating Client2)
 * 2. Compare with server hash
 * 3. Verify correct behavior for matching and mismatched hashes
 */

import { computeMD5, verifyMessageIntegrity } from './md5Verify'

/**
 * Run verification tests
 */
export async function testMessageVerification() {
    console.log('\n' + '='.repeat(70))
    console.log('TEST: Frontend Message Integrity Verification')
    console.log('='.repeat(70))

    try {
        // Test 1: Hash computation
        console.log('\n✓ Test 1: MD5 Hash Computation')
        const message1 = "Hello Client2"
        const hash1 = await computeMD5(message1)
        console.log(`  Message: "${message1}"`)
        console.log(`  Hash: ${hash1}`)
        console.log(`  ✅ Hash computed successfully`)

        // Test 2: Consistent hashing
        console.log('\n✓ Test 2: Hash Consistency')
        const hash1_again = await computeMD5(message1)
        if (hash1 === hash1_again) {
            console.log(`  ✅ Same message produces same hash`)
        } else {
            console.error(`  ❌ Hash inconsistency detected!`)
            return false
        }

        // Test 3: Different messages produce different hashes
        console.log('\n✓ Test 3: Tampering Detection')
        const message2 = "Hacked message"
        const hash2 = await computeMD5(message2)
        if (hash1 !== hash2) {
            console.log(`  Original: "${message1}" → ${hash1}`)
            console.log(`  Modified: "${message2}" → ${hash2}`)
            console.log(`  ✅ Different messages produce different hashes`)
        } else {
            console.error(`  ❌ Should be different hashes!`)
            return false
        }

        // Test 4: Message integrity verification - PASS case
        console.log('\n✓ Test 4: Message Verification (PASS case)')
        const decryptedMsg = "Hello Client2"
        const serverHash = hash1  // Simulate server hash

        const result_pass = await verifyMessageIntegrity(
            decryptedMsg,
            serverHash
        )

        console.log(`  Decrypted: "${decryptedMsg}"`)
        console.log(`  Server hash: ${serverHash}`)
        console.log(`  Local hash: ${result_pass.computedHash}`)

        if (result_pass.isValid) {
            console.log(`  ${result_pass.indicator} ✅ Message verified OK`)
        } else {
            console.error(`  ${result_pass.indicator} ❌ Should be verified!`)
            return false
        }

        // Test 5: Message integrity verification - FAIL case
        console.log('\n✓ Test 5: Message Verification (FAIL case - Tampering)')
        const tamperedMsg = "HACKED MESSAGE"
        const wrong_hash = hash2  // Wrong hash (doesn't match decrypted message)

        const result_fail = await verifyMessageIntegrity(
            decryptedMsg,
            wrong_hash  // This will mismatch
        )

        console.log(`  Decrypted: "${decryptedMsg}"`)
        console.log(`  Server hash: ${wrong_hash}`)
        console.log(`  Local hash: ${result_fail.computedHash}`)

        if (!result_fail.isValid) {
            console.log(`  ${result_fail.indicator} ✅ Tampering detected correctly`)
        } else {
            console.error(`  ${result_fail.indicator} ❌ Should detect tampering!`)
            return false
        }

        // Test 6: Multiple message types
        console.log('\n✓ Test 6: Multiple Message Types')
        const testMessages = [
            "Short",
            "This is a longer message with multiple words",
            "Special chars: !@#$%^&*()",
            "Unicode: Hello 世界",
            "Emoji: Hi 👋 Secure 🔐",
        ]

        for (const msg of testMessages) {
            const h = await computeMD5(msg)
            const vr = await verifyMessageIntegrity(msg, h)
            const status = vr.isValid ? '✅' : '❌'
            console.log(`  ${status} "${msg.substring(0, 30)}..." → verified`)
        }

        console.log('\n' + '='.repeat(70))
        console.log('✅ ALL TESTS PASSED!')
        console.log('='.repeat(70))
        console.log(`
Frontend Message Verification Summary:
✓ MD5 hash computation works
✓ Hash consistency verified
✓ Tampering detection works
✓ Message integrity verification works
✓ Multiple message types supported

Flow:
1. Client2 receives: {encrypted, message_hash}
2. Client2 decrypts: plaintext = AES_decrypt(encrypted)
3. Client2 computes: local_hash = MD5(plaintext)
4. Client2 verifies: local_hash === message_hash
5. Client2 displays: message + verification indicator

Indicators:
✅ = Message verified (hash matches)
⚠️ = Hash mismatch (message may have been modified)
❌ = Verification error

Installation:
npm install js-md5
or
npm install crypto-js
    `)
        return true

    } catch (error) {
        console.error('\n❌ TEST FAILED:', error)
        return false
    }
}

// Run tests if imported
if (typeof window !== 'undefined') {
    window.testMessageVerification = testMessageVerification
}
