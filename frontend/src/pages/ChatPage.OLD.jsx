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
import { decryptMessage } from '../api/messages.js'
import { API_BASE_URL } from '../api/client.js'
import { useAuth } from '../store/auth.jsx'
import { messageDebugger } from '../utils/messageDebugger.js'
import { verifyMessageIntegrity, performFullVerification } from '../utils/messageIntegrity.js'
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
  const activeRoomIdRef = useRef(null) // Track activeRoom.id for room change detection
  const userIdRef = useRef(user?.id) // Track user id without closure issue
  const decryptedCacheRef = useRef(new Map()) // Cache for decrypted messages
  const decryptAbortControllerRef = useRef(null) // AbortController để cancel pending decryption
  const currentDecryptionsRef = useRef(new Set()) // Track pending decryptions cho room hiện tại

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

  /**
   * Giải mã message từ backend API
   * Backend trả plaintext + message_hash
   * Cache kết quả để tránh gọi API lặp lại
   */
  const decryptMessageContent = async (messageId, contentEncrypted, roomId = null) => {
    // Check cache first
    if (decryptedCacheRef.current.has(messageId)) {
      const cached = decryptedCacheRef.current.get(messageId)
      messageDebugger.logFrontendDisplay(messageId, cached.plaintext)
      return cached
    }

    // Add to pending set
    currentDecryptionsRef.current.add(messageId)

    try {
      messageDebugger.logFrontendDecryptRequest(messageId)
      
      // Check if room changed - if so, abort
      if (roomId && activeRoomIdRef.current !== roomId) {
        console.log('❌ Aborting decrypt for message', messageId, 'from old room', roomId)
        currentDecryptionsRef.current.delete(messageId)
        return null // Return null to indicate abort
      }

      const response = await decryptMessage(messageId)
      
      // Check again after API call - room might have changed
      if (roomId && activeRoomIdRef.current !== roomId) {
        console.log('❌ Aborting decrypt result for message', messageId, 'from old room', roomId)
        currentDecryptionsRef.current.delete(messageId)
        return null
      }

      const plaintext = response.content_plaintext || contentEncrypted
      const messageHash = response.message_hash // API trả hash
      
      const decrypted = {
        plaintext,
        message_hash: messageHash,
        verification_timestamp: new Date().toISOString(),
      }
      
      // Cache the result (chưa verify lúc này)
      decryptedCacheRef.current.set(messageId, decrypted)
      messageDebugger.logFrontendDecryptResponse(messageId, plaintext)
      messageDebugger.logFrontendDisplay(messageId, plaintext)
      
      currentDecryptionsRef.current.delete(messageId)
      return decrypted
    } catch (error) {
      messageDebugger.logError('DECRYPT', messageId, error)
      currentDecryptionsRef.current.delete(messageId)
      // Return encrypted content as fallback
      return {
        plaintext: contentEncrypted,
        message_hash: null,
        error: error.message,
      }
    }
  }

  /**
   * Verify message integrity bằng cách gọi backend API
   * Backend sẽ tính MD5(plaintext) và so sánh với message_hash
   */
  const verifyMessageIntegrity = async (messageId, plaintext) => {
    try {
      const verification = await performFullVerification(
        { id: messageId, content_decrypted: plaintext },
        token,
        true // call backend verify
      )
      return verification
    } catch (error) {
      console.error('❌ Verification error:', error)
      return {
        verified: null,
        integrity_status: 'error',
        error: error.message,
      }
    }
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
      
      // RESET messages immediately - mềm
      setMessages([])
      setEvents([])
      
      const data = await getRoomMessages(roomId, 0, 30)
      const batch = data.messages || []
      
      // Kiểm tra room có thay đổi không (user)
      if (activeRoomIdRef.current !== roomId) {
        console.log('❌ Room changed while loading messages, aborting')
        return
      }
      
      // Set messages từ API
      setMessages(batch)
      
      // Decrypt messages with encrypted content
      batch.forEach((msg) => {
        if (msg.content_encrypted && msg.id) {
          decryptMessageContent(msg.id, msg.content_encrypted, roomId).then((decrypted) => {
            // Check room không đổi trước khi update state
            if (activeRoomIdRef.current !== roomId) {
              console.log('❌ Room changed, skipping decrypt update for', msg.id)
              return
            }
            
            if (!decrypted) return // Abort signal
            
            setMessages((prev) => {
              const idx = prev.findIndex((m) => m.id === msg.id)
              if (idx >= 0) {
                const updated = [...prev]
                updated[idx] = {
                  ...updated[idx],
                  content_decrypted: decrypted.plaintext,
                  message_hash: decrypted.message_hash,
                }
                return updated
              }
              return prev
            })
            
            // Call verify API
            verifyMessageIntegrity(msg.id, decrypted.plaintext).then((verification) => {
              // Check room lại trước verify update
              if (activeRoomIdRef.current !== roomId) {
                console.log('❌ Room changed, skipping verify update for', msg.id)
                return
              }
              
              setMessages((prev) => {
                const idx = prev.findIndex((m) => m.id === msg.id)
                if (idx >= 0) {
                  const updated = [...prev]
                  updated[idx] = {
                    ...updated[idx],
                    message_verified: verification.verified,
                    verification_timestamp: verification.timestamp,
                  }
                  return updated
                }
                return prev
              })
            })
          })
        }
      })
      
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
    const roomIdSnapshot = activeRoom.id
    loadingMoreRef.current = true
    setIsLoadingMore(true)

    try {
      const skip = messages.length
      const data = await getRoomMessages(roomIdSnapshot, skip, 30)
      const batch = data.messages || []
      const total = typeof data.total === 'number' ? data.total : skip + batch.length

      // Check room hasn't changed
      if (activeRoomIdRef.current !== roomIdSnapshot) {
        console.log('❌ Room changed while loading more messages, aborting')
        return
      }

      if (batch.length === 0) {
        setHasMoreMessages(false)
        hasMoreRef.current = false
      } else {
        setMessages((prev) => {
          // Filter out messages that already exist to avoid duplicates
          const existingIds = new Set(prev.map((m) => m.id))
          const newMessages = batch.filter((msg) => !existingIds.has(msg.id))
          return [...newMessages, ...prev]
        })
        
        // Decrypt messages with encrypted content
        batch.forEach((msg) => {
          if (msg.content_encrypted && msg.id) {
            decryptMessageContent(msg.id, msg.content_encrypted, roomIdSnapshot).then((decrypted) => {
              // Check room hasn't changed before updating
              if (activeRoomIdRef.current !== roomIdSnapshot) {
                console.log('❌ Room changed, skipping decrypt update for', msg.id)
                return
              }
              
              if (!decrypted) return // Abort signal
              
              setMessages((prev) => {
                const idx = prev.findIndex((m) => m.id === msg.id)
                if (idx >= 0) {
                  const updated = [...prev]
                  updated[idx] = {
                    ...updated[idx],
                    content_decrypted: decrypted.plaintext,
                    message_hash: decrypted.message_hash,
                  }
                  return updated
                }
                return prev
              })
              
              // Call verify API
              verifyMessageIntegrity(msg.id, decrypted.plaintext).then((verification) => {
                // Check room haven't changed before verify update
                if (activeRoomIdRef.current !== roomIdSnapshot) {
                  console.log('❌ Room changed, skipping verify update for', msg.id)
                  return
                }
                
                setMessages((prev) => {
                  const idx = prev.findIndex((m) => m.id === msg.id)
                  if (idx >= 0) {
                    const updated = [...prev]
                    updated[idx] = {
                      ...updated[idx],
                      message_verified: verification.verified,
                      verification_timestamp: verification.timestamp,
                    }
                    return updated
                  }
                  return prev
                })
              })
            })
          }
        })
        
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

          // [DEBUG] Phase 12: Frontend receives from WebSocket
          if (data.type === 'message' && data.id) {
            messageDebugger.logFrontendReceive(
              data.id,
              data.room_id || roomId,
              data.sender_name,
              data.content_encrypted || ''
            )
          }

          // Update room list with new message preview and timestamp
          // This happens for ALL messages from this WebSocket (both active and inactive)
          if (data.type === 'message' && data.id) {
            const displayContent = '[encrypted]'  // Always show encrypted until decrypted
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

          // ⭐ KEY FIX: Only update UI if this message is for the currently active room
          const isActiveRoom = activeRoomRef.current?.id === roomId
          
          if (!isActiveRoom) {
            console.log('⏭️ Message for inactive room:', roomId, 'current active:', activeRoomRef.current?.id)
            return // ← EXIT EARLY - Don't process for inactive rooms!
          }

          console.log('📨 Message received for active room:', roomId, 'data:', data)
          
          if (data.type === 'system') {
            const isDuplicate = events.some(
              (e) =>
                e.id === data.id &&
                e.sender_id === data.sender_id &&
                new Date().getTime() - new Date(e.created_at || e.timestamp).getTime() < 5000
            )
            if (!isDuplicate) {
              setEvents((prev) => [...prev, data])
            }
          } else if (data.type === 'message' && data.id) {
            console.log('📨 Adding message:', data.id, 'from:', data.sender_name)
            
            // [DEBUG] Phase 13: Frontend adds to state
            messageDebugger.logFrontendAddToState(data.id)
            
            // ⭐ KEY FIX: Check if message already exists
            setMessages((prev) => {
              const existingIndex = prev.findIndex((m) => m.id === data.id)
              
              if (existingIndex >= 0) {
                // Message already exists, don't add duplicate
                console.log('⚠️ Message already exists, skipping')
                return prev
              }
              
              // ⭐ KEY FIX: Own message - only replace temp if this message belongs to THIS room
              if (normalizeId(data.sender_id) === normalizeId(userIdRef.current)) {
                // Own message: replace temp message and add real one
                // ONLY remove temp from THIS room (don't remove from all!)
                const filteredMessages = prev.filter((m) => !m.id.startsWith('temp-'))
                return [...filteredMessages, data]
              }
              
              // Other user message: add to list
              return [...prev, data]
            })
            
            // ⭐ KEY FIX: Pass roomId to decryptMessageContent
            if (data.content_encrypted) {
              decryptMessageContent(data.id, data.content_encrypted, roomId).then((decrypted) => {
                // ⭐ KEY FIX: Check room hasn't changed before updating
                if (activeRoomIdRef.current !== roomId) {
                  console.log('❌ Room changed, skipping decrypt update for', data.id)
                  return
                }
                
                if (!decrypted) return // Abort signal
                
                setMessages((prev) => {
                  // Update the message with decrypted content
                  const idx = prev.findIndex((m) => m.id === data.id)
                  if (idx >= 0) {
                    const updated = [...prev]
                    updated[idx] = {
                      ...updated[idx],
                      content_decrypted: decrypted.plaintext,
                      message_hash: decrypted.message_hash,
                    }
                    return updated
                  }
                  return prev
                })
                
                // Call verify API
                verifyMessageIntegrity(data.id, decrypted.plaintext).then((verification) => {
                  // ⭐ KEY FIX: Check room haven't changed before verify update
                  if (activeRoomIdRef.current !== roomId) {
                    console.log('❌ Room changed, skipping verify update for', data.id)
                    return
                  }
                  
                  setMessages((prev) => {
                    const idx = prev.findIndex((m) => m.id === data.id)
                    if (idx >= 0) {
                      const updated = [...prev]
                      updated[idx] = {
                        ...updated[idx],
                        message_verified: verification.verified,
                        verification_timestamp: verification.timestamp,
                      }
                      return updated
                    }
                    return prev
                  })
                })
              })
            }
            
            setTimeout(scrollToBottom, 50)
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
    const messageId = tempId

    // [DEBUG] Phase 1: User sends message
    messageDebugger.logSend(messageId, messageText, activeRoom.id, user?.id)

    // Add message locally immediately (optimistic update)
    const optimisticMessage = {
      id: messageId,
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
        // [DEBUG] Phase 3: WebSocket send
        messageDebugger.logWebSocketSend(messageId, activeRoom.id)
        ws.send(JSON.stringify(messageData))
        messageDebugger.logWebSocketSendSuccess(messageId)
      } else {
        messageDebugger.logWebSocketSendFailed(messageId, new Error('Connection not open'))
        message.error('Connection lost')
        // Remove optimistic message if failed to send
        setMessages((prev) => prev.filter((m) => m.id !== messageId))
      }
    } catch (error) {
      messageDebugger.logError('WEBSOCKET', messageId, error)
      message.error('Failed to send message')
      // Remove optimistic message if error
      setMessages((prev) => prev.filter((m) => m.id !== messageId))
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
  // ⭐ KEY FIX: Also track activeRoomId separately and clear cache when changing rooms
  useEffect(() => {
    const prevRoomId = activeRoomIdRef.current
    const newRoomId = activeRoom?.id
    
    activeRoomRef.current = activeRoom
    activeRoomIdRef.current = newRoomId
    
    console.log('🔄 Active room changed to:', newRoomId, '| name:', activeRoom?.name, '| prev:', prevRoomId)
    
    // ⭐ KEY FIX: Clear cache and pending decryptions when room changes
    if (prevRoomId && newRoomId !== prevRoomId) {
      console.log('🧹 Clearing cache and pending decryptions for room change')
      currentDecryptionsRef.current.clear()
      // Don't clear entire cache - just mark pending decryptions as aborted
    }
  }, [activeRoom?.id, activeRoom])

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
                        <div className="message-text">
                          {item.content_decrypted || <em style={{color: '#999'}}>Decrypting...</em>}
                        </div>
                        {item.message_verified === true && (
                          <div className="message-verification" style={{fontSize: '11px', marginTop: '4px', color: '#999'}}>
                            <span title="Message integrity verified">🔒 Verified</span>
                          </div>
                        )}
                        {item.message_verified === false && (
                          <div className="message-verification" style={{fontSize: '11px', marginTop: '4px', color: '#ff4d4f'}}>
                            <span title="Message verification FAILED - possible tampering!">
                              ⚠️ Tampered
                            </span>
                          </div>
                        )}
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
