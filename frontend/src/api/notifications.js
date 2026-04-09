import { API_BASE_URL } from './client.js'

function createNotificationSocket(token, handlers = {}) {
  if (!token) {
    return null
  }

  const wsUrl = API_BASE_URL.replace('http', 'ws')
  const socket = new WebSocket(`${wsUrl}/ws/notifications?token=${token}`)

  socket.onopen = () => handlers.onOpen?.()
  socket.onerror = (event) => handlers.onError?.(event)
  socket.onclose = (event) => handlers.onClose?.(event)

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data)
      handlers.onMessage?.(payload)
    } catch (error) {
      handlers.onMessage?.({ type: 'error', message: 'Invalid notification payload' })
    }
  }

  return socket
}

export { createNotificationSocket }
