import { useEffect, useState } from 'react'
import { Empty, Button, Spin } from 'antd'
import { DeleteOutlined, CheckOutlined } from '@ant-design/icons'
import { useAuth } from '../store/auth.jsx'
import '../styles/notification-panel.css'

function NotificationPanel({ onClose }) {
  const { notifications, markNotificationAsRead, markAllNotificationsAsRead, clearNotifications } =
    useAuth()
  const [newNotifs, setNewNotifs] = useState(new Set())
  const [collapsingNotifs, setCollapsingNotifs] = useState(new Set())

  // Track newly added notifications for animation
  useEffect(() => {
    if (notifications.length > 0) {
      const latestId = notifications[0].id
      setNewNotifs((prev) => new Set(prev).add(latestId))

      const timer = setTimeout(() => {
        setNewNotifs((prev) => {
          const updated = new Set(prev)
          updated.delete(latestId)
          return updated
        })
      }, 3000) // Animation lasts 3 seconds

      return () => clearTimeout(timer)
    }
  }, [notifications.length])

  const unreadCount = notifications.filter((n) => !n.read).length
  const hasNotifications = notifications.length > 0

  const getNotificationType = (type) => {
    const types = {
      friend_request: { icon: '👥', label: 'Friend Request' },
      friend_request_accepted: { icon: '✅', label: 'Friend Accepted' },
      friend_request_rejected: { icon: '❌', label: 'Request Rejected' },
      friend_request_canceled: { icon: '⚠️', label: 'Request Canceled' },
      friend_deleted: { icon: '🚫', label: 'Friend Removed' },
    }
    return types[type] || { icon: '📌', label: 'Notification' }
  }

  const formatTime = (timestamp) => {
    try {
      const date = new Date(timestamp)
      const now = new Date()
      const diffMs = now - date
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)
      const diffDays = Math.floor(diffMs / 86400000)

      if (diffMins < 1) return 'Just now'
      if (diffMins < 60) return `${diffMins}m ago`
      if (diffHours < 24) return `${diffHours}h ago`
      if (diffDays < 7) return `${diffDays}d ago`

      return date.toLocaleDateString()
    } catch {
      return 'Recently'
    }
  }

  const handleMarkAsRead = (notificationId, isAlreadyRead) => {
    if (!isAlreadyRead) {
      // Add collapse animation
      setCollapsingNotifs((prev) => new Set(prev).add(notificationId))

      // Mark as read after animation starts
      setTimeout(() => {
        markNotificationAsRead(notificationId)
        // Remove from collapsing set after animation completes
        setTimeout(() => {
          setCollapsingNotifs((prev) => {
            const updated = new Set(prev)
            updated.delete(notificationId)
            return updated
          })
        }, 500)
      }, 100)
    }
  }

  return (
    <div className="notification-panel">
      <div className="notification-panel-header">
        <div className="notification-panel-title">
          <h3>Notifications</h3>
          {unreadCount > 0 && <span className="unread-badge">{unreadCount}</span>}
        </div>
        <div className="notification-panel-actions">
          {unreadCount > 0 && (
            <Button
              type="text"
              size="small"
              icon={<CheckOutlined />}
              onClick={markAllNotificationsAsRead}
              title="Mark all as read"
            />
          )}
          {hasNotifications && (
            <Button
              type="text"
              size="small"
              icon={<DeleteOutlined />}
              onClick={clearNotifications}
              danger
              title="Clear all"
            />
          )}
        </div>
      </div>

      <div className="notification-panel-list">
        {!hasNotifications && <Empty description="No notifications yet" />}

        {hasNotifications &&
          notifications.map((notification) => {
            const notifType = getNotificationType(notification.type)
            const isNew = newNotifs.has(notification.id)
            const isRead = notification.read
            const isCollapsing = collapsingNotifs.has(notification.id)

            return (
              <div
                key={notification.id}
                className={`notification-item ${isNew ? 'animate-in' : ''} ${
                  isCollapsing ? 'animate-out' : ''
                } ${isRead ? 'read' : 'unread'}`}
                onClick={() => handleMarkAsRead(notification.id, isRead)}
              >
                <div className="notification-item-indicator">
                  {!isRead && <div className="unread-dot"></div>}
                </div>

                <div className="notification-item-content">
                  <div className="notification-item-header">
                    <span className="notification-icon">{notifType.icon}</span>
                    <span className={`notification-type ${isRead ? '' : 'font-bold'}`}>
                      {notifType.label}
                    </span>
                  </div>

                  <div className={`notification-message ${isRead ? '' : 'font-bold'}`}>
                    {notification.message || 'You have a notification'}
                  </div>

                  <div className="notification-time">{formatTime(notification.receivedAt)}</div>
                </div>
              </div>
            )
          })}
      </div>
    </div>
  )
}

export default NotificationPanel
