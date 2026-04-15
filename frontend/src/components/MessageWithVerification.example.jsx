/**
 * Example: How to integrate message verification in ChatPage
 * 
 * This shows how to use MessageWithVerification component
 */

import MessageWithVerification from './MessageWithVerification'
import { decryptMessage } from '../api/messages'

/**
 * Updated ChatPage fragment
 */
export function ChatPageExample() {
  // ... existing state ...

  /**
   * Decrypt and verify message integrity
   * 
   * IMPORTANT: This function combines decryption + verification
   */
  const decryptAndVerifyMessage = async (messageId, contentEncrypted) => {
    try {
      // 1. Call backend decrypt API
      const response = await decryptMessage(messageId)
      const plaintext = response.content_plaintext
      
      // 2. Frontend will compute MD5 again via MessageWithVerification component
      // 3. Component will verify: MD5(plaintext) === message_hash
      
      return plaintext
    } catch (error) {
      console.error('Decrypt failed:', error)
      return contentEncrypted
    }
  }

  return (
    <div className="chat-messages">
      {messages.map((msg) => (
        <MessageWithVerification
          key={msg.id}
          message={msg}
          onDecrypt={decryptAndVerifyMessage}
        />
      ))}
    </div>
  )
}

/**
 * Full example implementation in ChatPage.jsx
 * 
 * Add this to replace existing message display:
 */

/*
import MessageWithVerification from '../components/MessageWithVerification'

export default function ChatPage() {
  // ... existing code ...

  const decryptMessageCallback = async (messageId, contentEncrypted) => {
    try {
      const response = await decryptMessage(messageId)
      return response.content_plaintext || contentEncrypted
    } catch (error) {
      console.error('Decrypt error:', error)
      return contentEncrypted
    }
  }

  return (
    <div className="chat-container">
      {/* Header, input, etc... */}

      {/* Messages with verification */}
      <div className="messages-list">
        {messages.map((msg) => (
          <MessageWithVerification
            key={msg.id}
            message={msg}
            onDecrypt={decryptMessageCallback}
          />
        ))}
      </div>
    </div>
  )
}
*/
