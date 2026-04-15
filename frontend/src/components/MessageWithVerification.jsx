/**
 * Message Component with Integrity Verification
 * 
 * Displays message with verification indicator:
 * ✅ Message verified (hash matches)
 * ⚠️ Hash mismatch (message may have been modified)
 * ❌ Verification error
 */

import React, { useEffect, useState } from 'react'
import { computeMD5, verifyMessageIntegrity, formatVerificationResult } from '../utils/md5Verify'
import './MessageWithVerification.css'

export default function MessageWithVerification({ 
  message,
  onDecrypt = null 
}) {
  const [decrypted, setDecrypted] = useState(null)
  const [verification, setVerification] = useState(null)
  const [isDecrypting, setIsDecrypting] = useState(false)
  const [error, setError] = useState(null)

  /**
   * Decrypt message and verify integrity
   */
  useEffect(() => {
    const decryptAndVerify = async () => {
      try {
        setIsDecrypting(true)
        setError(null)

        // 1. Decrypt (sử dụng callback hoặc API)
        let plaintext
        if (onDecrypt) {
          plaintext = await onDecrypt(message.id, message.content_encrypted)
        } else {
          // Fallback: sử dụng plaintext từ message (nếu có)
          plaintext = message.content || message.content_encrypted
        }

        // 2. Verify integrity (IMPORTANT!)
        const verifyResult = await verifyMessageIntegrity(
          plaintext,
          message.message_hash
        )

        setDecrypted(plaintext)
        setVerification(verifyResult)

        // Log verification result
        console.log(
          `${verifyResult.indicator} Message ${message.id.substring(0, 8)}...`,
          verifyResult
        )

        // Show warning if mismatch
        if (!verifyResult.isValid) {
          console.warn(
            `⚠️ INTEGRITY CHECK FAILED for message ${message.id}`,
            {
              expected: verifyResult.serverHash,
              actual: verifyResult.computedHash
            }
          )
        }
      } catch (err) {
        console.error('Failed to decrypt/verify message:', err)
        setError(err.message)
        setVerification({
          isValid: false,
          verified: false,
          indicator: '❌',
          message: 'Error: ' + err.message
        })
      } finally {
        setIsDecrypting(false)
      }
    }

    if (message) {
      decryptAndVerify()
    }
  }, [message?.id, onDecrypt])

  // Loading state
  if (isDecrypting) {
    return (
      <div className="message-container loading">
        <span className="spinner">⏳</span>
        <span className="content">Đang giải mã và xác thực...</span>
      </div>
    )
  }

  // Error state
  if (error && !decrypted) {
    return (
      <div className="message-container error">
        <span className="indicator">❌</span>
        <span className="content">{error}</span>
      </div>
    )
  }

  // Normal state with verification
  const format = formatVerificationResult(verification || {})
  const content = decrypted || message.content

  return (
    <div className={`message-container ${format.status}`}>
      {/* Indicator */}
      <span className={`indicator ${format.status}`}>
        {format.icon}
      </span>

      {/* Message content */}
      <span className="content">
        {content}
      </span>

      {/* Verification warning */}
      {format.showWarning && (
        <div className="verification-warning">
          <span className="warning-icon">⚠️</span>
          <span className="warning-text">
            {format.message}
          </span>
          <details className="warning-details">
            <summary>Xem chi tiết</summary>
            <div className="hash-details">
              <p><strong>Expected hash:</strong></p>
              <code>{message.message_hash}</code>
              <p><strong>Actual hash:</strong></p>
              <code>{verification?.computedHash}</code>
            </div>
          </details>
        </div>
      )}

      {/* Metadata */}
      <span className="metadata">
        <span className="timestamp">
          {new Date(message.created_at).toLocaleTimeString()}
        </span>
        {message.sender_name && (
          <span className="sender">@{message.sender_name}</span>
        )}
        {verification?.isValid && (
          <span className="verified-badge">Đã xác minh</span>
        )}
      </span>
    </div>
  )
}
