import { useEffect, useRef, useState } from 'react'
import {
  App as AntdApp,
  Avatar,
  Button,
  Input,
  Modal,
  Empty,
  Tooltip,
  Spin,
} from 'antd'
import { useNavigate } from 'react-router-dom'
import {
  SendOutlined,
  PlusOutlined,
  LockOutlined,
  DeleteOutlined,
  UserAddOutlined,
  PhoneOutlined,
  VideoCameraOutlined,
  InfoOutlined,
  SearchOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons'
import {
  listRooms,
  createRoom,
  getRoomMessages,
  getRoom,
  addRoomMember,
  removeRoomMember,
  deleteRoom,
} from '../api/rooms.js'
import { API_BASE_URL } from '../api/client.js'
import { useAuth } from '../store/auth.jsx'
import '../styles/ChatPage.css'

function normalizeId(value) {
  return value ? value.replace(/-/g, '').toLowerCase() : ''
}

function ChatPage() {
  const { message } = AntdApp.useApp()
  const { user, token } = useAuth()
  const navigate = useNavigate()
  const [rooms, setRooms] = useState([])
  const [activeRoom, setActiveRoom] = useState(null)
  const [messages, setMessages] = useState([])
  const [events, setEvents] = useState([])
  const [draft, setDraft] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [hasMoreMessages, setHasMoreMessages] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [roomForm, setRoomForm] = useState({ name: '', description: '' })
  const [roomDetails, setRoomDetails] = useState(null)
  const [memberModalOpen, setMemberModalOpen] = useState(false)
  const [memberForm, setMemberForm] = useState({ userId: '', role: 'member' })
  const [searchTerm, setSearchTerm] = useState('')
  const messagesEndRef = useRef(null)
  const messagesContainerRef = useRef(null)
  const sentinelRef = useRef(null)
  const hasMoreRef = useRef(true)
  const loadingMoreRef = useRef(false)
  const wsConnectionsRef = useRef(new Map()) // Store all room connections
  const activeRoomRef = useRef(null) // Track activeRoom without closure issue
  const userIdRef = useRef(user?.id) // Track user id without closure issue

  const currentUserId = normalizeId(user?.id)
  const members = roomDetails?.members || []
  const isDirectChat = activeRoom?.is_group === false
  const directPeer = isDirectChat
    ? members.find((member) => normalizeId(member.user_id) !== currentUserId)
    : null

  const filteredRooms = rooms.filter((room) =>
    room.name?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const combinedFeed = [
    ...events.map((e) => ({ ...e, type: 'system' })),
    ...messages,
  ].sort((a, b) => {
    const timeA = new Date(a.created_at || a.timestamp || 0).getTime()
    const timeB = new Date(b.created_at || b.timestamp || 0).getTime()
    return timeA - timeB
  })

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  async function loadRooms() {
    try {
      setIsLoading(true)
      const data = await listRooms()
      
      // Sort rooms by last message time or created time (descending order)
      const sortedRooms = (data || []).sort((a, b) => {
        // Use last_message_at if available, otherwise use created_at
        const timeA = a.last_message_at || a.created_at || 0
        const timeB = b.last_message_at || b.created_at || 0
        
        const dateA = new Date(timeA).getTime()
        const dateB = new Date(timeB).getTime()
        
        return dateB - dateA // Descending order (newest first)
      })
      
      setRooms(sortedRooms)
      if (sortedRooms?.length && !activeRoom) {
        setActiveRoom(sortedRooms[0])
      }
    } catch (error) {
      message.error(error.message || 'Failed to load rooms')
    } finally {
      setIsLoading(false)
    }
  }

  async function loadMessages(roomId) {
    try {
      if (!roomId) {
        setMessages([])
        setHasMoreMessages(false)
        hasMoreRef.current = false
        return
      }
      const data = await getRoomMessages(roomId, 0, 30)
      const batch = data.messages || []
      setMessages(batch)
      setEvents([])
      const total = typeof data.total === 'number' ? data.total : batch.length
      const hasMore = batch.length < total
      setHasMoreMessages(hasMore)
      hasMoreRef.current = hasMore
      setTimeout(scrollToBottom, 100)
    } catch (error) {
      console.error('Load messages error:', error)
      setMessages([])
      setHasMoreMessages(false)
      hasMoreRef.current = false
    }
  }

  async function loadMoreMessages() {
    if (!activeRoom || loadingMoreRef.current || !hasMoreRef.current) return
    const container = messagesContainerRef.current
    if (!container) return

    const previousScrollHeight = container.scrollHeight
    loadingMoreRef.current = true
    setIsLoadingMore(true)

    try {
      const skip = messages.length
      const data = await getRoomMessages(activeRoom.id, skip, 30)
      const batch = data.messages || []
      const total = typeof data.total === 'number' ? data.total : skip + batch.length

      if (batch.length === 0) {
        setHasMoreMessages(false)
        hasMoreRef.current = false
      } else {
        setMessages((prev) => [...batch, ...prev])
        const nextHasMore = skip + batch.length < total
        setHasMoreMessages(nextHasMore)
        hasMoreRef.current = nextHasMore

        requestAnimationFrame(() => {
          const newScrollHeight = container.scrollHeight
          container.scrollTop = newScrollHeight - previousScrollHeight
        })
      }
    } catch (error) {
      console.error('Load more messages error:', error)
    } finally {
      loadingMoreRef.current = false
      setIsLoadingMore(false)
    }
  }

  async function loadRoomDetails(roomId) {
    try {
      if (!roomId) {
        setRoomDetails(null)
        return
      }
      const data = await getRoom(roomId)
      setRoomDetails(data)
    } catch (error) {
      console.error('Load room details error:', error)
      setRoomDetails(null)
    }
  }

  async function connectToAllRooms(roomsToConnect) {
    const baseUrl = API_BASE_URL || window.location.origin
    const wsBase = baseUrl.replace('https://', 'wss://').replace('http://', 'ws://')
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : ''

    // Close existing connections
    wsConnectionsRef.current.forEach((ws) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close()
      }
    })
    wsConnectionsRef.current.clear()

    // Connect to each room
    roomsToConnect.forEach((room) => {
      const wsUrl = `${wsBase}/ws/chat/${room.id}${tokenParam}`
      const ws = new WebSocket(wsUrl)
      
      // Capture roomId to avoid closure issue
      const roomId = room.id
      const isGroupChat = room.is_group

      ws.onopen = () => {
        console.log('✅ WebSocket connected for room:', roomId, '| type:', isGroupChat ? 'GROUP' : '1-1')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          console.log('📥 WebSocket message received:', data.type, '| room:', roomId)

          // Update room list with new message preview and timestamp
          if (data.type === 'message' && data.id) {
            const displayContent = data.content_encrypted || data.content
            console.log('🔄 Updating room list with new message:', displayContent)
            setRooms((prevRooms) => {
              const updatedRooms = prevRooms.map((r) => {
                if (r.id === roomId) {
                  // For group chat, show "SenderName: message"
                  // For 1-1 chat, just show message
                  const preview = isGroupChat && data.sender_name
                    ? `${data.sender_name}: ${displayContent}`
                    : displayContent
                  
                  return {
                    ...r,
                    last_message_preview: preview,
                    last_message_at: data.created_at || new Date().toISOString(),
                    last_message_sender_name: data.sender_name || 'Unknown',
                    has_unread: r.id !== activeRoomRef.current?.id, // Mark as unread if not active
                  }
                }
                return r
              })
              // Move updated room to top of list
              return updatedRooms.sort((a, b) => {
                const timeA = new Date(a.last_message_at || 0).getTime()
                const timeB = new Date(b.last_message_at || 0).getTime()
                return timeB - timeA
              })
            })
          }

          // Only update UI if this message is for the currently active room
          if (activeRoomRef.current?.id === roomId) {
            console.log('📨 Message received for active room:', roomId, 'data:', data)
            
            if (data.type === 'system') {
              const isDuplicate = events.some(
                (e) =>
                  e.content === data.content &&
                  e.sender_id === data.sender_id &&
                  new Date().getTime() - new Date(e.created_at || e.timestamp).getTime() < 5000
              )
              if (!isDuplicate) {
                setEvents((prev) => [...prev, data])
              }
            } else if (data.type === 'message' && data.id) {
              console.log('📨 Adding message:', data.id, 'from:', data.sender_name)
              
              setMessages((prev) => {
                // Check if this message already exists (to avoid duplicates)
                const existingIndex = prev.findIndex((m) => m.id === data.id)
                
                if (existingIndex >= 0) {
                  console.log('⚠️ Message already exists, skipping')
                  return prev
                }
                
                // If sender is current user, remove temporary messages
                if (normalizeId(data.sender_id) === normalizeId(userIdRef.current)) {
                  console.log('✅ Own message, replacing temp message')
                  const filteredMessages = prev.filter((m) => !m.id.startsWith('temp-'))
                  return [...filteredMessages, data]
                }
                
                console.log('✅ Other user message, adding to list')
                return [...prev, data]
              })
              setTimeout(scrollToBottom, 50)
            }
          } else {
            console.log('⏭️ Message for inactive room:', roomId, 'current active:', activeRoomRef.current?.id)
          }
        } catch (e) {
          console.error('Parse message error:', e)
        }
      }

      ws.onerror = () => {
        console.error('WebSocket error for room:', roomId)
      }

      ws.onclose = () => {
        console.log('WebSocket closed for room:', roomId)
      }

      wsConnectionsRef.current.set(roomId, ws)
    })
  }

  async function handleSend() {
    if (!draft.trim() || !activeRoom) return

    const messageText = draft.trim()
    const tempId = `temp-${Date.now()}-${Math.random()}` // Temporary ID for optimistic update

    // Add message locally immediately (optimistic update)
    const optimisticMessage = {
      id: tempId,
      room_id: activeRoom.id,
      sender_id: normalizeId(user?.id),
      sender_name: user?.username,
      content: messageText,
      created_at: new Date().toISOString(),
      timestamp: new Date().toISOString(),
      is_read: false,
    }

    setMessages((prev) => [...prev, optimisticMessage])
    setDraft('')
    setTimeout(scrollToBottom, 50)

    const messageData = {
      room_id: activeRoom.id,
      content: messageText,
    }

    try {
      const ws = wsConnectionsRef.current.get(activeRoom.id)
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(messageData))
      } else {
        message.error('Connection lost')
        // Remove optimistic message if failed to send
        setMessages((prev) => prev.filter((m) => m.id !== tempId))
      }
    } catch (error) {
      message.error('Failed to send message')
      // Remove optimistic message if error
      setMessages((prev) => prev.filter((m) => m.id !== tempId))
    }
  }

  async function handleCreateRoom() {
    if (!roomForm.name.trim()) {
      message.warning('Room name required')
      return
    }

    setIsCreating(true)
    try {
      const newRoom = await createRoom({
        name: roomForm.name,
        description: roomForm.description,
      })
      setRoomForm({ name: '', description: '' })
      setModalOpen(false)
      
      // Reload rooms and reconnect to all including the new one
      const updatedRooms = await listRooms()
      setRooms(updatedRooms || [])
      await connectToAllRooms(updatedRooms || [])
      
      setActiveRoom(newRoom)
      message.success('Room created')
    } catch (error) {
      message.error(error.message || 'Failed to create room')
    } finally {
      setIsCreating(false)
    }
  }

  useEffect(() => {
    loadRooms()
  }, [])

  // Connect to all rooms after they are loaded
  useEffect(() => {
    if (rooms.length > 0) {
      connectToAllRooms(rooms)
    }

    // Cleanup: close all connections on unmount
    return () => {
      wsConnectionsRef.current.forEach((ws) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.close()
        }
      })
      wsConnectionsRef.current.clear()
    }
  }, [rooms, token])

  useEffect(() => {
    if (activeRoom) {
      setHasMoreMessages(true)
      hasMoreRef.current = true
      loadMessages(activeRoom.id)
      loadRoomDetails(activeRoom.id)
    }
  }, [activeRoom?.id])

  // Keep activeRoomRef in sync to avoid closure issues in websocket handlers
  useEffect(() => {
    activeRoomRef.current = activeRoom
    console.log('🔄 Active room changed to:', activeRoom?.id, '| name:', activeRoom?.name)
  }, [activeRoom])

  // Keep userIdRef in sync to avoid closure issues in websocket handlers
  useEffect(() => {
    userIdRef.current = user?.id
  }, [user?.id])

  useEffect(() => {
    const container = messagesContainerRef.current
    const sentinel = sentinelRef.current
    if (!container || !sentinel) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          loadMoreMessages()
        }
      },
      {
        root: container,
        threshold: 0.1,
      }
    )

    observer.observe(sentinel)

    return () => {
      observer.disconnect()
    }
  }, [activeRoom?.id, messages.length])

  return (
    <div className="messenger-container">
      <aside className="messenger-sidebar">
        <div className="sidebar-top">
          <h2 className="sidebar-title">Chats</h2>
          <Button
            type="text"
            icon={<PlusOutlined />}
            className="compose-btn"
            onClick={() => setModalOpen(true)}
          />
        </div>

        <Input
          placeholder="Search Messenger"
          prefix={<SearchOutlined />}
          className="search-box"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />

        <div className="conversations-list">
          {isLoading ? (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
              <Spin />
            </div>
          ) : filteredRooms.length === 0 ? (
            <Empty
              description={searchTerm ? 'No chats found' : 'No chats yet'}
              style={{ marginTop: '3rem' }}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            filteredRooms.map((room) => (
              <div
                key={room.id}
                className={`conversation-item ${room.id === activeRoom?.id ? 'active' : ''}`}
                onClick={() => setActiveRoom(room)}
              >
                <Avatar size={56} style={{ backgroundColor: '#1890ff' }}>
                  {(room.display_name || room.name)?.slice(0, 1).toUpperCase()}
                </Avatar>
                <div className="conv-info">
                  <div className="conv-name">{room.display_name || room.name}</div>
                  <div className={`conv-preview ${room.has_unread ? 'unread' : ''}`}>
                    {room.last_message_preview
                      ? room.last_message_preview
                      : room.is_group
                        ? <TeamOutlined />
                        : <UserOutlined />}
                  </div>
                </div>
                {room.has_unread && <div className="unread-badge"></div>}
                {room.last_message_at && (
                  <div className="conv-time">
                    {new Date(room.last_message_at).toLocaleDateString('vi-VN', {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </aside>

      <section className="messenger-main">
        {!activeRoom ? (
          <div className="empty-chat-state">
            <div className="empty-icon">💬</div>
            <h2>Select a conversation</h2>
            <p>No active chat selected</p>
            <Button type="primary" size="large" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
              Start New Chat
            </Button>
          </div>
        ) : (
          <>
            <div className="messenger-header">
              <div className="header-title-section">
                <div className="header-avatars">
                  <Avatar size={40} style={{ backgroundColor: '#1890ff' }}>
                    {(directPeer?.username || activeRoom?.display_name || activeRoom?.name)?.slice(0, 1).toUpperCase()}
                  </Avatar>
                  {members.length > 1 && <div className="avatar-count">+{members.length - 1}</div>}
                </div>
                <div className="header-title-info">
                  <h2 className="header-title">
                    {directPeer?.username || activeRoom?.display_name || activeRoom?.name}
                  </h2>
                  {!isDirectChat && (
                    <div className="header-members">
                      {members.slice(0, 2).map((m) => m.username).join(', ')}
                      {members.length > 2 && `, +${members.length - 2}`}
                    </div>
                  )}
                </div>
              </div>

              <div className="header-actions">
                <Tooltip title="Call">
                  <Button type="text" icon={<PhoneOutlined />} />
                </Tooltip>
                <Tooltip title="Video Call">
                  <Button type="text" icon={<VideoCameraOutlined />} />
                </Tooltip>
                <Tooltip title="Info">
                  <Button type="text" icon={<InfoOutlined />} />
                </Tooltip>
              </div>
            </div>

            <div className="messages-container" ref={messagesContainerRef}>
              {hasMoreMessages && (
                <div className="messages-sentinel" ref={sentinelRef}>
                  <div className={`messages-loader ${isLoadingMore ? '' : 'is-hidden'}`}>
                    Loading older messages...
                  </div>
                </div>
              )}
              {isLoadingMore && (
                <div className="system-message-wrapper">
                  <div className="system-msg">Loading more messages...</div>
                </div>
              )}
              {combinedFeed.length === 0 ? (
                <div className="no-messages">
                  <Avatar size={80} style={{ backgroundColor: '#1890ff' }}>
                    {(directPeer?.username || activeRoom?.display_name || activeRoom?.name)?.slice(0, 1).toUpperCase()}
                  </Avatar>
                  <h3>{directPeer?.username || activeRoom?.display_name || activeRoom?.name}</h3>
                  <p className="no-msg-desc">
                    {activeRoom?.is_group ? <TeamOutlined /> : <UserOutlined />}
                  </p>
                  <small>Messages are end-to-end encrypted</small>
                </div>
              ) : (
                combinedFeed.map((item, idx) => {
                  if (item.type === 'system') {
                    return (
                      <div className="system-message-wrapper" key={`sys-${idx}`}>
                        <div className="system-msg">
                          <LockOutlined className="system-icon" />
                          <span>{item.content}</span>
                        </div>
                      </div>
                    )
                  }

                  const isSelf = normalizeId(item.sender_id) === currentUserId
                  // Check if this is the latest message and it's from the current user
                  const isLatest = idx === combinedFeed.length - 1 && item.type !== 'system'
                  const showReadStatus = isSelf && isLatest

                  return (
                    <div className={`message-row ${isSelf ? 'outgoing' : 'incoming'}`} key={item.id}>
                      {!isSelf && (
                        <Avatar 
                          size={32} 
                          style={{ backgroundColor: '#1890ff', cursor: 'pointer' }}
                          onClick={() => navigate(`/profile/${item.sender_id}`)}
                        >
                          {item.sender_name?.slice(0, 1).toUpperCase() || 'U'}
                        </Avatar>
                      )}
                      <div className={`message-bubble ${isSelf ? 'sent' : 'received'}`}>
                        <div className="message-text">{item.content_encrypted || item.content}</div>
                        <div className="message-time">
                          {new Date(item.created_at || item.timestamp).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                          {showReadStatus && (
                            <span className="read-status">
                              {item.is_read ? '✓✓' : '✓'}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="message-input-area">
              <div className="input-actions">
                <Button type="text" icon={<PlusOutlined />} />
              </div>
              <Input
                placeholder="Aa"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onPressEnter={handleSend}
                className="msg-input"
              />
              <Button type="text" icon={<SendOutlined />} onClick={handleSend} className="send-msg-btn" />
            </div>
          </>
        )}
      </section>

      {activeRoom && members.length > 0 && (
        <aside className="messenger-info">
          <div className="info-header">
            <h3>Members ({members.length})</h3>
          </div>
          <div className="members-container">
            {members.map((member) => (
              <div className="member-row" key={member.id}>
                <Avatar size={40} style={{ backgroundColor: '#1890ff' }}>
                  {member.username?.slice(0, 1).toUpperCase()}
                </Avatar>
                <div className="member-info-detail">
                  <div className="member-name">{member.username}</div>
                  <div className="member-role">{member.role}</div>
                </div>
                {member.user_id !== currentUserId && (
                  <Button
                    type="text"
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={async () => {
                      try {
                        await removeRoomMember(activeRoom.id, member.user_id)
                        await loadRoomDetails(activeRoom.id)
                        message.success('Member removed')
                      } catch (error) {
                        message.error(error.message || 'Failed')
                      }
                    }}
                  />
                )}
              </div>
            ))}
          </div>

          <div className="info-actions">
            <Button block icon={<UserAddOutlined />} onClick={() => setMemberModalOpen(true)}>
              Add Members
            </Button>
            <Button
              block
              danger
              icon={<DeleteOutlined />}
              onClick={() => {
                Modal.confirm({
                  title: 'Delete Room',
                  content: 'Are you sure? This cannot be undone.',
                  okText: 'Delete',
                  okType: 'danger',
                  onOk: async () => {
                    try {
                      await deleteRoom(activeRoom.id)
                      message.success('Room deleted')
                      await loadRooms()
                      setActiveRoom(null)
                    } catch (error) {
                      message.error(error.message || 'Failed')
                    }
                  },
                })
              }}
            >
              Delete Room
            </Button>
          </div>
        </aside>
      )}

      <Modal
        title="Create Group"
        open={modalOpen}
        onOk={handleCreateRoom}
        onCancel={() => {
          setModalOpen(false)
          setRoomForm({ name: '', description: '' })
        }}
        okButtonProps={{ loading: isCreating }}
        width={500}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <Input
            placeholder="Group name"
            value={roomForm.name}
            onChange={(e) => setRoomForm({ ...roomForm, name: e.target.value })}
          />
          <Input.TextArea
            placeholder="Description"
            value={roomForm.description}
            onChange={(e) => setRoomForm({ ...roomForm, description: e.target.value })}
            rows={3}
          />
        </div>
      </Modal>

      <Modal
        title="Add Member"
        open={memberModalOpen}
        onOk={async () => {
          if (!memberForm.userId) {
            message.warning('User ID required')
            return
          }
          try {
            await addRoomMember(activeRoom.id, {
              user_id: memberForm.userId,
              role: memberForm.role,
            })
            setMemberModalOpen(false)
            setMemberForm({ userId: '', role: 'member' })
            await loadRoomDetails(activeRoom.id)
            message.success('Member added')
          } catch (error) {
            message.error(error.message || 'Failed')
          }
        }}
        onCancel={() => {
          setMemberModalOpen(false)
          setMemberForm({ userId: '', role: 'member' })
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <Input
            placeholder="User ID"
            value={memberForm.userId}
            onChange={(e) => setMemberForm({ ...memberForm, userId: e.target.value })}
          />
          <select
            value={memberForm.role}
            onChange={(e) => setMemberForm({ ...memberForm, role: e.target.value })}
            style={{
              width: '100%',
              padding: '8px',
              border: '1px solid #d9d9d9',
              borderRadius: '4px',
              fontSize: '14px',
            }}
          >
            <option value="member">Member</option>
            <option value="moderator">Moderator</option>
            <option value="admin">Admin</option>
          </select>
        </div>
      </Modal>
    </div>
  )
}

export default ChatPage
