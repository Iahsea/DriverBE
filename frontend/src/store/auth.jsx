import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { App as AntdApp } from 'antd'
import { login as loginApi, register as registerApi, getMe } from '../api/auth.js'
import { createNotificationSocket } from '../api/notifications.js'

const AuthContext = createContext(null)

function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('access_token') || '')
  const [loading, setLoading] = useState(true)
  const socketRef = useRef(null)
  
  // Load notifications from localStorage on mount
  const [notifications, setNotifications] = useState(() => {
    try {
      const saved = localStorage.getItem('notifications')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })
  
  const { message } = AntdApp.useApp()

  useEffect(() => {
    let active = true
    async function loadProfile() {
      if (!token) {
        setLoading(false)
        return
      }
      try {
        const profile = await getMe()
        if (active) {
          setUser(profile)
        }
      } catch (error) {
        if (active) {
          setUser(null)
          setToken('')
          localStorage.removeItem('access_token')
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }
    loadProfile()
    return () => {
      active = false
    }
  }, [token])

  useEffect(() => {
    if (!token) {
      if (socketRef.current) {
        socketRef.current.close()
        socketRef.current = null
      }
      setNotifications([])
      return
    }

    const socketManager = createNotificationSocket(token, {
      onMessage: (payload) => {
        if (!payload) {
          return
        }
        
        // Add id and read status to notification
        const notification = {
          ...payload,
          id: Math.random().toString(36).substr(2, 9) + Date.now(),
          read: false,
          receivedAt: new Date().toISOString(),
        }
        
        setNotifications((prev) => {
          const updated = [notification, ...prev].slice(0, 50)
          // Save to localStorage
          try {
            localStorage.setItem('notifications', JSON.stringify(updated))
          } catch {
            console.warn('Failed to save notifications to localStorage')
          }
          return updated
        })

        if (payload.type === 'friend_request') {
          message.info(payload.message || 'New friend request')
        } else if (payload.type === 'friend_request_accepted') {
          message.success(payload.message || 'Friend request accepted')
        } else if (payload.type === 'friend_request_rejected') {
          message.warning(payload.message || 'Friend request rejected')
        } else if (payload.type === 'friend_request_canceled') {
          message.warning(payload.message || 'Friend request canceled')
        } else if (payload.type === 'friend_deleted') {
          message.warning(payload.message || 'Friend removed')
        }
      },
      onOpen: () => {
        console.log('Notification socket connected')
      },
      onError: (error) => {
        console.error('Notification socket error:', error)
      },
      onClose: (event) => {
        console.warn('Notification socket closed:', event.code, event.reason)
        // Reconnect logic is now handled inside createNotificationSocket
        // with exponential backoff retry
      },
    })

    socketRef.current = socketManager

    return () => {
      if (socketRef.current) {
        socketRef.current.close()
        socketRef.current = null
      }
    }
  }, [token])

  async function login(username, password) {
    const data = await loginApi(username, password)
    localStorage.setItem('access_token', data.access_token)
    setToken(data.access_token)
    setUser(data.user)
    return data
  }

  async function register(username, email, password) {
    const data = await registerApi(username, email, password)
    return data
  }

  function logout() {
    localStorage.removeItem('access_token')
    setToken('')
    setUser(null)
  }

  function markNotificationAsRead(notificationId) {
    setNotifications((prev) => {
      const updated = prev.map((n) =>
        n.id === notificationId ? { ...n, read: true } : n
      )
      localStorage.setItem('notifications', JSON.stringify(updated))
      return updated
    })
  }

  function markAllNotificationsAsRead() {
    setNotifications((prev) => {
      const updated = prev.map((n) => ({ ...n, read: true }))
      localStorage.setItem('notifications', JSON.stringify(updated))
      return updated
    })
  }

  function clearNotifications() {
    setNotifications([])
    localStorage.removeItem('notifications')
  }

  const unreadCount = notifications.filter((n) => !n.read).length

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      notifications,
      unreadCount,
      login,
      register,
      logout,
      markNotificationAsRead,
      markAllNotificationsAsRead,
      clearNotifications,
    }),
    [user, token, loading, notifications, unreadCount]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used inside AuthProvider')
  }
  return ctx
}

export { AuthProvider, useAuth }
