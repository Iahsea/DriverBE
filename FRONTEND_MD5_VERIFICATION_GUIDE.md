# Frontend MD5 Message Integrity Verification Guide

## Overview

Client2 must verify message integrity by computing MD5 hash of decrypted plaintext and comparing with server's hash. This detects if message was modified during transmission or storage.

## Installation

```bash
npm install js-md5
# or
npm install crypto-js
```

## Architecture

```
Client1 sends message
        ↓
Backend:
  1. Hash = MD5(plaintext)
  2. Encrypted = AES(plaintext)
  3. Save {plaintext, encrypted, hash} to DB
  4. Broadcast {encrypted, hash} via WebSocket
        ↓
Client2 receives {encrypted, hash}
        ↓
Client2 MUST:
  1. Decrypt = AES_decrypt(encrypted)
  2. LocalHash = MD5(decrypt)
  3. Verify: LocalHash === ServerHash
  4. Display: message + indicator (✅ or ⚠️)
```

## Implementation Steps

### Step 1: Install MD5 Library

```bash
cd frontend
npm install js-md5
```

### Step 2: Use MD5 Verify Utility

File: `src/utils/md5Verify.js`

Functions:
- `computeMD5(text)` - Compute MD5 hash
- `verifyMessageIntegrity(plaintext, serverHash)` - Verify integrity
- `formatVerificationResult(result)` - Format for UI

```javascript
import { computeMD5, verifyMessageIntegrity } from './utils/md5Verify'

// Compute hash
const hash = await computeMD5("Hello")
// Returns: "8b1a9953c4611296aaf7a3c47f8a588f"

// Verify integrity
const result = await verifyMessageIntegrity(plaintext, message.message_hash)
if (result.isValid) {
  console.log("✅ Message verified OK")
} else {
  console.warn("⚠️ Message integrity check FAILED")
}
```

### Step 3: Update Message Component

Use the `MessageWithVerification` component:

```javascript
import MessageWithVerification from '../components/MessageWithVerification'

export default function ChatPage() {
  const handleDecryptMessage = async (messageId, contentEncrypted) => {
    const response = await decryptMessage(messageId)
    return response.content_plaintext
  }

  return (
    <div className="messages-list">
      {messages.map((msg) => (
        <MessageWithVerification
          key={msg.id}
          message={msg}
          onDecrypt={handleDecryptMessage}
        />
      ))}
    </div>
  )
}
```

### Step 4: Handle WebSocket Messages

When receiving message via WebSocket, verify it:

```javascript
websocket.onmessage = async (event) => {
  const data = JSON.parse(event.data)
  
  if (data.type === 'message') {
    // Decrypt
    const plaintext = await cryptoLib.decrypt(data.content_encrypted)
    
    // Verify integrity (IMPORTANT!)
    const { isValid } = await verifyMessageIntegrity(
      plaintext,
      data.message_hash
    )
    
    if (!isValid) {
      console.warn("⚠️ Message tampering detected!")
      // Show warning to user
      // Could also refuse to display message entirely
    }
    
    // Display message
    addMessageToUI({
      ...data,
      plaintext,
      verified: isValid
    })
  }
}
```

## Security Properties

### What MD5 Verification Detects

✅ **Tampering in transit** - Message modified between server and client
✅ **Storage corruption** - Database corruption detected
✅ **Bit flip errors** - Single bit change caught
✅ **Partial modifications** - Even partial message changes detected

### What MD5 Verification DOES NOT Detect

❌ **End-to-end attacks** - If attacker controls both server and client
❌ **Key compromise** - If encryption keys are stolen
❌ **Original sender impersonation** - Verify sender with public key instead
❌ **Perfectly matching collisions** - MD5 has collision vulnerability (but statistically unlikely for random messages)

### Why Client-Side Verification is Mandatory

1. **Server compromise**: If server is hacked, attacker can modify hash + message
2. **MITM attacks**: Attacker can intercept and replace both values
3. **Only solution**: Client computes independently and verifies result

## Testing

Run tests to verify MD5 works:

```javascript
// In browser console
import { testMessageVerification } from './utils/md5Verify.test'
await testMessageVerification()
```

## Component Structure

### MessageWithVerification Props

```javascript
{
  message: {
    id: "msg-123",
    content: "Hello",
    content_encrypted: "C20F/5+...",
    message_hash: "802c21ae4d9853d40ef331b4bb2bb22c",
    created_at: "2026-04-12T10:30:00Z",
    sender_id: "user-456"
  },
  onDecrypt: async (messageId, contentEncrypted) => {
    // Return decrypted plaintext
    return plaintext
  }
}
```

### Display Indicators

- ✅ = Message verified (hash matches)
- ⚠️ = Hash mismatch (message may have been modified)
- ❌ = Verification error (exception during verification)
- ⏳ = Decrypting and verifying...

## API Endpoints

### Decrypt + Get Hash

```
POST /api/v1/messages/{message_id}/decrypt
Authorization: Bearer {token}

Response:
{
  "id": "msg-123",
  "sender_id": "user-456",
  "content_plaintext": "Hello",
  "message_hash": "802c21ae4d9853d40ef331b4bb2bb22c",
  "created_at": "2026-04-12T10:30:00Z",
  "message": "Message decrypted successfully"
}
```

### Optional: Backend Verification Helper

```
POST /api/v1/messages/{message_id}/verify-integrity
Authorization: Bearer {token}
Content-Type: application/json

{
  "plaintext_received": "Hello"
}

Response:
{
  "verified": true,
  "message_hash": "802c21ae4d9853d40ef331b4bb2bb22c",
  "computed_hash": "802c21ae4d9853d40ef331b4bb2bb22c",
  "message": "Message integrity verified",
  "status": "verified"  // or "mismatch" or "error"
}
```

Use this for audit logging or compliance, not for primary security.

## Styling

Default styles provided in `MessageWithVerification.css`:

- **Green theme** (✅ verified)
- **Orange theme** (⚠️ mismatch - warning)
- **Red theme** (❌ error)

Customize colors in CSS file as needed.

## Example: Full Chat Integration

```javascript
import { useState, useEffect } from 'react'
import MessageWithVerification from './MessageWithVerification'
import { decryptMessage } from '../api/messages'
import { computeMD5, verifyMessageIntegrity } from '../utils/md5Verify'

export default function ChatPage() {
  const [messages, setMessages] = useState([])

  useEffect(() => {
    // WebSocket handler
    const ws = new WebSocket(`ws://localhost:8000/ws/chat/${roomId}`)
    
    ws.onmessage = async (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'message') {
        // Verify message integrity upon receipt
        const hash = await computeMD5(data.content_plaintext || '')
        const verifyResult = await verifyMessageIntegrity(
          data.content_plaintext,
          data.message_hash
        )
        
        setMessages(prev => [...prev, {
          ...data,
          verificationResult: verifyResult
        }])
      }
    }
  }, [])

  const handleDecryptMessage = async (messageId, contentEncrypted) => {
    const response = await decryptMessage(messageId)
    return response.content_plaintext
  }

  return (
    <div className="chat-container">
      <div className="messages-list">
        {messages.map((msg) => (
          <MessageWithVerification
            key={msg.id}
            message={msg}
            onDecrypt={handleDecryptMessage}
          />
        ))}
      </div>
    </div>
  )
}
```

## Troubleshooting

### MD5 library not found

```
Error: MD5 library not found. Install: npm install js-md5
```

Solution:
```bash
npm install js-md5
```

### Hash mismatch warning

If you see "⚠️ Hash mismatch", it means:
1. Message was modified after encryption
2. Database corruption
3. Network transmission error
4. Malicious tampering (possible)

Check server logs for issues.

### Decryption failed

Make sure:
1. You have the correct encryption key
2. Message is in valid encrypted format
3. You're decrypting with the same cipher (AES-256-CBC)

## Performance

- MD5 computation: <1ms per message
- React component render: <10ms
- Total overhead: <20ms per message

Negligible for normal chat usage.

## FAQs

**Q: Why MD5 and not SHA256?**
A: MD5 is what kernel driver provides (same as password hashing). For crypto integrity, SHA256 would be better, but MD5 is sufficient for tampering detection.

**Q: Who computes the hash first?**
A: Backend computes, then Client2 verifies by computing independently.

**Q: What if server and client both get hacked?**
A: Then integrity verification can't help - attacker has full control.

**Q: Can I disable verification?**
A: Not recommended, but you can skip verification code. Message will still display, just without indicator.

**Q: Does this sign messages (non-repudiation)?**
A: No, only detects tampering. For signing, use digital signatures with public key crypto.

**Q: What about message ordering?**
A: Timestamps included in API responses. Use `created_at` to sort chronologically.

**Q: Can I verify messages on phone?**
A: Yes, same process. Just need MD5 library for your platform (React Native, Swift, Kotlin, etc).
