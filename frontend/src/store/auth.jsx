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
  const reconnectRef = useRef({ active: false, retries: 0 })
  const [notifications, setNotifications] = useState([])
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
      reconnectRef.current.active = false
      reconnectRef.current.retries = 0
      if (socketRef.current) {
        socketRef.current.close()
        socketRef.current = null
      }
      setNotifications([])
      return
    }

    reconnectRef.current.active = true
    reconnectRef.current.retries = 0

    const connect = () => {
      if (!reconnectRef.current.active) {
        return
      }

      const socket = createNotificationSocket(token, {
        onMessage: (payload) => {
          if (!payload) {
            return
          }
          setNotifications((prev) => [payload, ...prev].slice(0, 30))

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
        onError: () => {
          if (reconnectRef.current.retries === 0) {
            message.warning('Notification socket disconnected')
          }
        },
        onClose: () => {
          if (!reconnectRef.current.active) {
            return
          }
          reconnectRef.current.retries += 1
          const retryDelay = Math.min(5000, 1000 * reconnectRef.current.retries)
          setTimeout(connect, retryDelay)
        },
      })

      socketRef.current = socket
    }

    connect()

    return () => {
      reconnectRef.current.active = false
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

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      notifications,
      login,
      register,
      logout,
    }),
    [user, token, loading, notifications]
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
