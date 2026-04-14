import { API_BASE_URL } from './client.js'

function createNotificationSocket(token, handlers = {}) {
  if (!token) {
    return null
  }

  const wsUrl = API_BASE_URL.replace('http', 'ws')
  let socket = null
  let reconnectTimeout = null
  let reconnectAttempts = 0
  const MAX_RECONNECT_ATTEMPTS = 5
  const INITIAL_RECONNECT_DELAY = 1000 // ms
  const MAX_RECONNECT_DELAY = 30000 // ms

  function calculateBackoffDelay() {
    const delay = INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttempts)
    return Math.min(delay, MAX_RECONNECT_DELAY)
  }

  function connect() {
    try {
      socket = new WebSocket(`${wsUrl}/ws/notifications?token=${encodeURIComponent(token)}`)

      socket.onopen = () => {
        reconnectAttempts = 0 // Reset on successful connection
        console.log('[Notification] Connected')
        handlers.onOpen?.()

        // Start sending heartbeat ping every 30 seconds
        const heartbeatInterval = setInterval(() => {
          if (socket && socket.readyState === WebSocket.OPEN) {
            try {
              socket.send('ping')
            } catch (error) {
              console.error('[Notification] Heartbeat send error:', error)
              clearInterval(heartbeatInterval)
            }
          }
        }, 30000)

        // Store interval for cleanup
        socket.heartbeatInterval = heartbeatInterval
      }

      socket.onerror = (event) => {
        console.error('[Notification] Error:', event)
        handlers.onError?.(event)
      }

      socket.onclose = (event) => {
        console.warn('[Notification] Closed:', event.code, event.reason)

        // Clear heartbeat interval
        if (socket?.heartbeatInterval) {
          clearInterval(socket.heartbeatInterval)
        }

        handlers.onClose?.(event)

        // Attempt reconnection if not a deliberate close
        if (event.code !== 1000 && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          const delay = calculateBackoffDelay()
          console.log(`[Notification] Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`)
          
          reconnectTimeout = setTimeout(() => {
            reconnectAttempts++
            connect()
          }, delay)
        } else if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
          console.error('[Notification] Max reconnection attempts reached')
          handlers.onError?.({ message: 'Failed to reconnect after multiple attempts' })
        }
      }

      socket.onmessage = (event) => {
        try {
          // Handle ping/pong text messages (not JSON)
          if (event.data === 'ping' || event.data === 'pong') {
            if (event.data === 'ping') {
              // Server sent ping, reply with pong
              if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send('pong')
              }
            }
            // Ignore pong from server (heartbeat response)
            return
          }

          // Only parse JSON if it's not a ping/pong message
          const payload = JSON.parse(event.data)
          handlers.onMessage?.(payload)
        } catch (error) {
          console.error('[Notification] Message parse error:', error)
          // Don't call onMessage for parse errors
        }
      }
    } catch (error) {
      console.error('[Notification] Connection error:', error)
      handlers.onError?.(error)

      // Retry connection
      if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        const delay = calculateBackoffDelay()
        reconnectTimeout = setTimeout(() => {
          reconnectAttempts++
          connect()
        }, delay)
      }
    }
  }

  // Initial connection
  connect()

  // Return object with methods to manage the socket
  return {
    socket: () => socket,
    close: () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      if (socket?.heartbeatInterval) clearInterval(socket.heartbeatInterval)
      if (socket) socket.close(1000, 'Client initiated close')
    },
    send: (data) => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(data)
      }
    },
    isConnected: () => socket && socket.readyState === WebSocket.OPEN,
  }
}

export { createNotificationSocket }
