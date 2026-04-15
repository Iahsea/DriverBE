/**
 * Message Flow Debugger
 * Tracks: Send → Encrypt → WebSocket → Receive → Decrypt → Display
 */

const DebugColors = {
  SEND: '#FF6B6B',      // Red
  ENCRYPT: '#4ECDC4',   // Teal  
  WEBSOCKET: '#45B7D1', // Blue
  RECEIVE: '#96CEB4',   // Green
  DECRYPT: '#FFEAA7',   // Yellow
  DISPLAY: '#DDA0DD',   // Plum
  ERROR: '#FF0000',     // Bright Red
  API: '#FFA500',       // Orange
}

class MessageDebugger {
  constructor() {
    this.messageFlows = new Map() // messageId -> flow steps
    this.startTime = Date.now()
  }

  /**
   * Format timestamp with ms precision
   */
  getTimestamp() {
    const elapsed = Date.now() - this.startTime
    return `[${elapsed.toString().padStart(6, '0')}ms]`
  }

  /**
   * Log with color and formatted timestamp
   */
  log(phase, messageId, text, data = null) {
    const timestamp = this.getTimestamp()
    const color = DebugColors[phase] || '#999'
    const prefix = `%c[${phase}]`
    const msgIdShort = messageId?.substring(0, 8) || 'UNKNOWN'

    // Initialize flow record if needed
    if (messageId && !this.messageFlows.has(messageId)) {
      this.messageFlows.set(messageId, [])
    }

    // Record step
    if (messageId) {
      this.messageFlows.get(messageId).push({
        phase,
        time: Date.now() - this.startTime,
        text,
        data,
      })
    }

    // Console output with styling
    if (data !== null && typeof data === 'object') {
      console.log(
        `${prefix} ${timestamp} ${text} (${msgIdShort})`,
        `color: ${color}; font-weight: bold; font-size: 12px`,
        data
      )
    } else {
      console.log(
        `${prefix} ${timestamp} ${text} (${msgIdShort})`,
        `color: ${color}; font-weight: bold; font-size: 12px`
      )
    }
  }

  /**
   * PHASE 1: User sends message
   */
  logSend(messageId, content, roomId, userId) {
    this.log('SEND', messageId, `📝 USER SENDS MESSAGE`, {
      messageId,
      roomId: roomId?.substring(0, 8),
      userId: userId?.substring(0, 8),
      contentLength: content.length,
      content: content.substring(0, 50),
    })
  }

  /**
   * PHASE 2: Message encrypted (placeholder before actual encryption)
   */
  logEncryptPending(messageId, roomId) {
    this.log('ENCRYPT', messageId, `🔐 ENCRYPTION PENDING (should receive from driver)`, {
      messageId,
      status: 'waiting_for_driver',
    })
  }

  /**
   * PHASE 3: WebSocket send
   */
  logWebSocketSend(messageId, roomId) {
    this.log('WEBSOCKET', messageId, `📤 SENDING TO WEBSOCKET`, {
      messageId,
      roomId: roomId?.substring(0, 8),
      target: `/ws/chat/${roomId?.substring(0, 8)}`,
      status: 'attempting',
    })
  }

  /**
   * PHASE 4: WebSocket sent successfully
   */
  logWebSocketSendSuccess(messageId) {
    this.log('WEBSOCKET', messageId, `✅ SENT TO WEBSOCKET`, {
      messageId,
      status: 'success',
    })
  }

  /**
   * PHASE 5: WebSocket send failed
   */
  logWebSocketSendFailed(messageId, error) {
    this.log('WEBSOCKET', messageId, `❌ WEBSOCKET SEND FAILED`, {
      messageId,
      error: error.message || error,
      status: 'failed',
    })
  }

  /**
   * PHASE 6: Backend receives from WebSocket
   */
  logBackendReceive(messageId, roomId, userId) {
    this.log('WEBSOCKET', messageId, `📥 BACKEND RECEIVES FROM WEBSOCKET`, {
      messageId,
      roomId: roomId?.substring(0, 8),
      userId: userId?.substring(0, 8),
      status: 'received_by_backend',
    })
  }

  /**
   * PHASE 7: Backend encrypts with driver
   */
  logBackendEncrypt(messageId, originalContent) {
    this.log('ENCRYPT', messageId, `🔐 BACKEND ENCRYPTING WITH DRIVER`, {
      messageId,
      originalContentLength: originalContent.length,
      content: originalContent.substring(0, 50),
      status: 'calling_driver',
    })
  }

  /**
   * PHASE 8: Backend encryption success
   */
  logBackendEncryptSuccess(messageId, encryptedContent) {
    this.log('ENCRYPT', messageId, `✅ BACKEND ENCRYPTION SUCCESS`, {
      messageId,
      encryptedLength: encryptedContent.length,
      encryptedFirstChars: encryptedContent.substring(0, 50),
      status: 'encrypted',
    })
  }

  /**
   * PHASE 9: Backend saves to DB
   */
  logBackendSaveDB(messageId, content, contentEncrypted) {
    this.log('ENCRYPT', messageId, `💾 BACKEND SAVING TO DATABASE`, {
      messageId,
      plaintext: content.substring(0, 50),
      encrypted: contentEncrypted.substring(0, 50),
      status: 'saving',
    })
  }

  /**
   * PHASE 10: Backend saves to DB success
   */
  logBackendSaveDBSuccess(messageId) {
    this.log('ENCRYPT', messageId, `✅ BACKEND DATABASE SAVED`, {
      messageId,
      status: 'saved',
    })
  }

  /**
   * PHASE 11: Backend broadcasts to room
   */
  logBackendBroadcast(messageId, roomId, encryptedContent) {
    this.log('WEBSOCKET', messageId, `📡 BACKEND BROADCASTING TO ROOM`, {
      messageId,
      roomId: roomId?.substring(0, 8),
      encryptedLength: encryptedContent.length,
      status: 'broadcasting',
    })
  }

  /**
   * PHASE 12: Frontend receives from WebSocket
   */
  logFrontendReceive(messageId, roomId, senderName, encryptedContent) {
    this.log('RECEIVE', messageId, `📥 FRONTEND RECEIVES FROM WEBSOCKET`, {
      messageId,
      roomId: roomId?.substring(0, 8),
      senderName,
      encryptedLength: encryptedContent.length,
      status: 'received_by_frontend',
    })
  }

  /**
   * PHASE 13: Frontend adds to state (temporary, before decryption)
   */
  logFrontendAddToState(messageId) {
    this.log('RECEIVE', messageId, `📋 FRONTEND ADDING TO MESSAGE LIST`, {
      messageId,
      status: 'added_to_state',
    })
  }

  /**
   * PHASE 14: Frontend calls decrypt API
   */
  logFrontendDecryptRequest(messageId) {
    this.log('DECRYPT', messageId, `🔑 FRONTEND CALLING DECRYPT API`, {
      messageId,
      endpoint: `POST /api/v1/messages/${messageId?.substring(0, 8)}/decrypt`,
      status: 'api_request',
    })
  }

  /**
   * PHASE 15: Backend receives decrypt request
   */
  logBackendDecryptRequest(messageId) {
    this.log('DECRYPT', messageId, `🔑 BACKEND DECRYPT REQUEST RECEIVED`, {
      messageId,
      endpoint: '/api/v1/messages/{message_id}/decrypt',
      status: 'processing',
    })
  }

  /**
   * PHASE 16: Backend decrypts
   */
  logBackendDecrypt(messageId, encryptedContent) {
    this.log('DECRYPT', messageId, `🔓 BACKEND DECRYPTING`, {
      messageId,
      encryptedLength: encryptedContent.length,
      encrypted: encryptedContent.substring(0, 50),
      status: 'decrypting',
    })
  }

  /**
   * PHASE 17: Backend decrypt success
   */
  logBackendDecryptSuccess(messageId, plaintext) {
    this.log('DECRYPT', messageId, `✅ BACKEND DECRYPT SUCCESS`, {
      messageId,
      plaintextLength: plaintext.length,
      plaintext: plaintext.substring(0, 50),
      status: 'decrypted',
    })
  }

  /**
   * PHASE 18: Backend sends decrypt response
   */
  logBackendDecryptResponse(messageId, plaintext) {
    this.log('API', messageId, `📤 BACKEND SENDING DECRYPT RESPONSE`, {
      messageId,
      plaintextLength: plaintext.length,
      plaintext: plaintext.substring(0, 50),
      httpStatus: 200,
    })
  }

  /**
   * PHASE 19: Frontend receives decrypt response
   */
  logFrontendDecryptResponse(messageId, plaintext) {
    this.log('DECRYPT', messageId, `✅ FRONTEND RECEIVES DECRYPTED CONTENT`, {
      messageId,
      plaintextLength: plaintext.length,
      plaintext: plaintext.substring(0, 50),
      status: 'decrypted_received',
    })
  }

  /**
   * PHASE 20: Frontend updates UI with decrypted content
   */
  logFrontendDisplay(messageId, decryptedContent) {
    this.log('DISPLAY', messageId, `📺 FRONTEND DISPLAYING DECRYPTED MESSAGE`, {
      messageId,
      content: decryptedContent.substring(0, 100),
      status: 'displayed',
    })
  }

  /**
   * Error logging
   */
  logError(phase, messageId, error) {
    console.error(
      `%c[${phase}] ERROR (${messageId?.substring(0, 8)})`,
      `color: ${DebugColors.ERROR}; font-weight: bold; font-size: 12px`,
      error
    )
    
    if (messageId && this.messageFlows.has(messageId)) {
      this.messageFlows.get(messageId).push({
        phase: `${phase}_ERROR`,
        time: Date.now() - this.startTime,
        error: error.message || error,
      })
    }
  }

  /**
   * Print flow timeline for a message
   */
  printFlowTimeline(messageId) {
    if (!this.messageFlows.has(messageId)) {
      console.log(`No debug info found for message ${messageId}`)
      return
    }

    const flow = this.messageFlows.get(messageId)
    console.group(`📊 Flow Timeline for ${messageId.substring(0, 8)}`)
    console.table(flow)
    console.groupEnd()
  }

  /**
   * Print all flows
   */
  printAllFlows() {
    console.group('📊 All Message Flows')
    this.messageFlows.forEach((flow, messageId) => {
      console.group(`Message ${messageId.substring(0, 8)}`)
      console.table(flow)
      console.groupEnd()
    })
    console.groupEnd()
  }

  /**
   * Get metrics for a message flow
   */
  getFlowMetrics(messageId) {
    if (!this.messageFlows.has(messageId)) {
      return null
    }

    const flow = this.messageFlows.get(messageId)
    const totalTime = flow[flow.length - 1]?.time || 0
    const phaseCount = flow.length
    
    // Calculate time per phase
    const phaseTimings = []
    for (let i = 0; i < flow.length; i++) {
      const current = flow[i]
      const prev = i > 0 ? flow[i - 1] : null
      const phaseDuration = prev ? current.time - prev.time : current.time
      phaseTimings.push({
        phase: current.phase,
        duration: phaseDuration,
        cumulativeTime: current.time,
      })
    }

    return {
      messageId: messageId.substring(0, 8),
      totalTime,
      phaseCount,
      phaseTimings,
      avgPhaseTime: totalTime / phaseCount,
    }
  }

  /**
   * Get all message metrics
   */
  getAllMetrics() {
    const metrics = []
    this.messageFlows.forEach((flow, messageId) => {
      metrics.push(this.getFlowMetrics(messageId))
    })
    return metrics
  }

  /**
   * Print flow metrics in table format
   */
  printMetrics(messageId) {
    const metrics = this.getFlowMetrics(messageId)
    if (!metrics) {
      console.log(`No metrics found for message ${messageId}`)
      return
    }

    console.group(`📊 Metrics for ${metrics.messageId}`)
    console.log(`Total Time: ${metrics.totalTime}ms`)
    console.log(`Total Phases: ${metrics.phaseCount}`)
    console.log(`Avg Phase Time: ${metrics.avgPhaseTime.toFixed(2)}ms`)
    console.table(metrics.phaseTimings)
    console.groupEnd()
  }

  /**
   * Get the status of a message
   */
  getMessageStatus(messageId) {
    if (!this.messageFlows.has(messageId)) {
      return 'NOT_FOUND'
    }

    const flow = this.messageFlows.get(messageId)
    const lastPhase = flow[flow.length - 1]

    if (lastPhase.phase.includes('ERROR')) {
      return 'ERROR'
    }

    if (lastPhase.phase === 'DISPLAY') {
      return 'DISPLAYED'
    }

    if (lastPhase.phase === 'DECRYPT' || lastPhase.phase === 'API') {
      return 'DECRYPTING'
    }

    if (lastPhase.phase === 'WEBSOCKET') {
      return 'SENDING'
    }

    return 'PROCESSING'
  }

  /**
   * Get all messages grouped by status
   */
  getMessagesByStatus() {
    const grouped = {
      SENT: [],
      SENDING: [],
      DECRYPTING: [],
      DISPLAYED: [],
      ERROR: [],
      NOT_FOUND: [],
    }

    this.messageFlows.forEach((flow, messageId) => {
      const status = this.getMessageStatus(messageId)
      grouped[status]?.push(messageId.substring(0, 8))
    })

    return grouped
  }

  /**
   * Find bottlenecks in flow
   */
  findBottlenecks() {
    const bottlenecks = []

    this.messageFlows.forEach((flow, messageId) => {
      const timings = []
      for (let i = 1; i < flow.length; i++) {
        const duration = flow[i].time - flow[i - 1].time
        if (duration > 100) {
          timings.push({
            messageId: messageId.substring(0, 8),
            between: `${flow[i - 1].phase} → ${flow[i].phase}`,
            duration: `${duration}ms`,
            description: this._getBottleneckDescription(
              flow[i - 1].phase,
              flow[i].phase,
              duration
            ),
          })
        }
      }
      bottlenecks.push(...timings)
    })

    return bottlenecks
  }

  _getBottleneckDescription(fromPhase, toPhase, duration) {
    if (fromPhase === 'WEBSOCKET' && toPhase === 'RECEIVE') {
      return 'Network latency'
    }
    if (
      (fromPhase === 'WEBSOCKET' && toPhase === 'ENCRYPT') ||
      (fromPhase === 'ENCRYPT' && toPhase === 'API')
    ) {
      return 'Encryption processing'
    }
    if (fromPhase === 'API' && toPhase === 'DECRYPT') {
      return 'API response time'
    }
    if (
      (fromPhase === 'DECRYPT' && toPhase === 'DISPLAY') ||
      (fromPhase.includes('DECRYPT') && toPhase === 'DISPLAY')
    ) {
      return 'UI rendering'
    }
    return 'Unknown delay'
  }

  /**
   * Print analysis report
   */
  printAnalysisReport() {
    console.group('🔍 Message Flow Analysis Report')

    console.group('📊 Summary')
    const allMetrics = this.getAllMetrics()
    if (allMetrics.length > 0) {
      const avgTime = (
        allMetrics.reduce((sum, m) => sum + m.totalTime, 0) / allMetrics.length
      ).toFixed(2)
      console.log(`Total Messages: ${allMetrics.length}`)
      console.log(`Average Flow Time: ${avgTime}ms`)
      console.log(`Fastest: ${Math.min(...allMetrics.map((m) => m.totalTime))}ms`)
      console.log(`Slowest: ${Math.max(...allMetrics.map((m) => m.totalTime))}ms`)
    }
    console.groupEnd()

    console.group('📍 Message Status')
    const byStatus = this.getMessagesByStatus()
    console.table(byStatus)
    console.groupEnd()

    console.group('⚠️ Bottlenecks')
    const bottlenecks = this.findBottlenecks()
    if (bottlenecks.length > 0) {
      console.table(bottlenecks)
    } else {
      console.log('✅ No significant bottlenecks detected')
    }
    console.groupEnd()

    console.groupEnd()
  }
}

export const messageDebugger = new MessageDebugger()
