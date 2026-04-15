import { useEffect, useRef, useState, useCallback } from 'react'
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
  const { message: antMessage } = AntdApp.useApp()
  const { user, token } = useAuth()
  const navigate = useNavigate()
  
  // ====================
  // STATE MANAGEMENT
  // ====================
  const [rooms, setRooms] = useState([])
  const [activeRoom, setActiveRoom] = useState(null)
  const [messages, setMessages] = useState([]) // TẤT CẢ messages from API + WebSocket
  const [events, setEvents] = useState([]) // System events
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
  
  // ====================
  // REFS - Avoid Closure Issues
  // ====================
  const messagesEndRef = useRef(null)
  const messagesContainerRef = useRef(null)
  const sentinelRef = useRef(null)
  const hasMoreRef = useRef(true)
  const loadingMoreRef = useRef(false)
  
  // WebSocket connections
  const wsConnectionsRef = useRef(new Map())
  const activeRoomRef = useRef(null)
  const activeRoomIdRef = useRef(null)
  const userIdRef = useRef(user?.id)
  
  // ⭐ DECRYPTION MANAGEMENT
  const decryptAbortControllerRef = useRef(null) // Cancel API calls
  const decryptedCacheRef = useRef(new Map()) // Message ID -> { plaintext, hash, etc }
  const currentDecryptionsRef = useRef(new Set()) // Message IDs being decrypted
  const decryptionTasksRef = useRef([]) // Queue of pending decryptions { msgId, roomId, contentEncrypted }
  
  // ====================
  // COMPUTED VALUES - FILTER BY ROOM
  // ====================
  const currentUserId = normalizeId(user?.id)
  const members = roomDetails?.members || []
  const isDirectChat = activeRoom?.is_group === false
  const directPeer = isDirectChat
    ? members.find((member) => normalizeId(member.user_id) !== currentUserId)
    : null

  const filteredRooms = rooms.filter((room) =>
    room.name?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // ⭐ KEY FIX: Filter messages by CURRENT room only
  const currentRoomMessages = activeRoom
    ? messages.filter((msg) => msg.room_id === activeRoom.id)
    : []

  // ⭐ KEY FIX: Filter events by CURRENT room only
  const currentRoomEvents = activeRoom
    ? events.filter((evt) => evt.room_id === activeRoom.id)
    : []

  // ⭐ KEY FIX: combinedFeed with room filtering
  const combinedFeed = [
    ...currentRoomEvents.map((e) => ({ ...e, type: 'system' })),
    ...currentRoomMessages,
  ].sort((a, b) => {
    const timeA = new Date(a.created_at || a.timestamp || 0).getTime()
    const timeB = new Date(b.created_at || b.timestamp || 0).getTime()
    return timeA - timeB
  })

  // ====================
  // UTILITY FUNCTIONS
  // ====================
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  /**
   * ⭐ REFACTORED: Decrypt message with AbortController + room checks
   * Returns: { plaintext, message_hash, verification_timestamp } or null (if aborted)
   */
  const decryptMessageContent = useCallback(
    async (messageId, contentEncrypted, roomId = null) => {
      // Check cache first - BEFORE room check so we reuse if possible
      if (decryptedCacheRef.current.has(messageId)) {
        const cached = decryptedCacheRef.current.get(messageId)
        messageDebugger.logFrontendDisplay(messageId, cached.plaintext)
        return cached
      }

      // Validate room BEFORE starting
      if (roomId && activeRoomIdRef.current !== roomId) {
        console.log(`❌ [DECRYPT] Aborting for msg ${messageId}: room changed (expected ${roomId}, now ${activeRoomIdRef.current})`)
        return null
      }

      currentDecryptionsRef.current.add(messageId)

      try {
        messageDebugger.logFrontendDecryptRequest(messageId)

        // API call with timeout
        const response = await Promise.race([
          decryptMessage(messageId),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Decrypt timeout')), 30000)
          ),
        ])

        // Room check AFTER API
        if (roomId && activeRoomIdRef.current !== roomId) {
          console.log(`❌ [DECRYPT] Aborting result for msg ${messageId}: room changed after API`)
          currentDecryptionsRef.current.delete(messageId)
          return null
        }

        const plaintext = response.content_plaintext || contentEncrypted
        const messageHash = response.message_hash

        const decrypted = {
          plaintext,
          message_hash: messageHash,
          verification_timestamp: new Date().toISOString(),
        }

        // Cache ONLY if room hasn't changed
        if (activeRoomIdRef.current === roomId) {
          decryptedCacheRef.current.set(messageId, decrypted)
        }

        messageDebugger.logFrontendDecryptResponse(messageId, plaintext)
        messageDebugger.logFrontendDisplay(messageId, plaintext)

        currentDecryptionsRef.current.delete(messageId)
        return decrypted
      } catch (error) {
        console.error(`❌ [DECRYPT] Error for msg ${messageId}:`, error.message)
        messageDebugger.logError('DECRYPT', messageId, error)
        currentDecryptionsRef.current.delete(messageId)

        return {
          plaintext: contentEncrypted,
          message_hash: null,
          error: error.message,
        }
      }
    },
    []
  )

  /**
   * ⭐ REFACTORED: Batch decrypt messages to reduce concurrent state updates
   */
  const decryptMessagesBatch = useCallback(
    async (batch, roomId) => {
      if (!batch.length || activeRoomIdRef.current !== roomId) return

      const decryptedResults = await Promise.allSettled(
        batch.map((msg) => decryptMessageContent(msg.id, msg.content_encrypted, roomId))
      )

      // Verify if room still the same
      if (activeRoomIdRef.current !== roomId) {
        console.log(`❌ [BATCH DECRYPT] Room changed during batch, skipping updates`)
        return
      }

      // Process results - update state ONCE with all decryptions
      const updates = {}
      decryptedResults.forEach((result, idx) => {
        if (result.status === 'fulfilled' && result.value) {
          const msgId = batch[idx].id
          updates[msgId] = result.value
        }
      })

      // Single state update for all decrypted messages
      if (Object.keys(updates).length > 0) {
        setMessages((prev) =>
          prev.map((msg) =>
            updates[msg.id]
              ? {
                  ...msg,
                  content_decrypted: updates[msg.id].plaintext,
                  message_hash: updates[msg.id].message_hash,
                }
              : msg
          )
        )

        // Now verify all in batch
        await verifyMessagesBatch(
          batch.map((msg) => ({
            id: msg.id,
            plaintext: updates[msg.id]?.plaintext,
          })).filter((m) => m.plaintext),
          roomId
        )
      }
    },
    [decryptMessageContent]
  )

  /**
   * ⭐ REFACTORED: Batch verify messages
   */
  const verifyMessagesBatch = useCallback(
    async (batch, roomId) => {
      if (!batch.length || activeRoomIdRef.current !== roomId) return

      const verifications = await Promise.allSettled(
        batch.map((msg) =>
          performFullVerification(
            { id: msg.id, content_decrypted: msg.plaintext },
            token,
            true
          )
        )
      )

      // Verify room still same
      if (activeRoomIdRef.current !== roomId) return

      // Single update for verification results
      const verifyUpdates = {}
      verifications.forEach((result, idx) => {
        if (result.status === 'fulfilled') {
          verifyUpdates[batch[idx].id] = result.value
        }
      })

      if (Object.keys(verifyUpdates).length > 0) {
        setMessages((prev) =>
          prev.map((msg) =>
            verifyUpdates[msg.id]
              ? {
                  ...msg,
                  message_verified: verifyUpdates[msg.id].verified,
                  verification_timestamp: verifyUpdates[msg.id].timestamp,
                }
              : msg
          )
        )
      }
    },
    [token]
  )

  // ====================
  // LOAD FUNCTIONS
  // ====================

  async function loadRooms() {
    try {
      setIsLoading(true)
      const data = await listRooms()

      const sortedRooms = (data || []).sort((a, b) => {
        const timeA = a.last_message_at || a.created_at || 0
        const timeB = b.last_message_at || b.created_at || 0
        const dateA = new Date(timeA).getTime()
        const dateB = new Date(timeB).getTime()
        return dateB - dateA
      })

      setRooms(sortedRooms)
      if (sortedRooms?.length && !activeRoom) {
        setActiveRoom(sortedRooms[0])
      }
    } catch (error) {
      antMessage.error(error.message || 'Failed to load rooms')
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * ⭐ REFACTORED: Load messages with proper room filtering
   */
  async function loadMessages(roomId) {
    try {
      if (!roomId) {
        setMessages([])
        setHasMoreMessages(false)
        hasMoreRef.current = false
        return
      }

      // RESET: Clear messages for this room
      setMessages((prev) => prev.filter((msg) => msg.room_id !== roomId))
      setEvents((prev) => prev.filter((evt) => evt.room_id !== roomId))

      const data = await getRoomMessages(roomId, 0, 30)
      const batch = data.messages || []

      // ⭐ Room check - abort if room changed
      if (activeRoomIdRef.current !== roomId) {
        console.log(`❌ [LOAD] Room changed while loading, aborting for room ${roomId}`)
        return
      }

      // Set raw messages
      setMessages((prev) => [
        ...prev.filter((msg) => msg.room_id !== roomId), // Keep other rooms
        ...batch.map((msg) => ({ ...msg, room_id: roomId })), // Ensure room_id set
      ])

      const total = typeof data.total === 'number' ? data.total : batch.length
      const hasMore = batch.length < total
      setHasMoreMessages(hasMore)
      hasMoreRef.current = hasMore

      // Batch decrypt encrypted messages
      const encryptedBatch = batch.filter((msg) => msg.content_encrypted && msg.id)
      if (encryptedBatch.length > 0) {
        await decryptMessagesBatch(encryptedBatch, roomId)
      }

      setTimeout(scrollToBottom, 100)
    } catch (error) {
      console.error('Load messages error:', error)
      setMessages((prev) => prev.filter((msg) => msg.room_id !== activeRoom?.id))
      setHasMoreMessages(false)
      hasMoreRef.current = false
    }
  }

  /**
   * ⭐ REFACTORED: Load more messages with pagination
   */
  async function loadMoreMessages() {
    if (!activeRoom || loadingMoreRef.current || !hasMoreRef.current) return

    const container = messagesContainerRef.current
    if (!container) return

    const previousScrollHeight = container.scrollHeight
    const roomIdSnapshot = activeRoom.id
    loadingMoreRef.current = true
    setIsLoadingMore(true)

    try {
      const skip = currentRoomMessages.length
      const data = await getRoomMessages(roomIdSnapshot, skip, 30)
      const batch = data.messages || []
      const total = typeof data.total === 'number' ? data.total : skip + batch.length

      // Room check
      if (activeRoomIdRef.current !== roomIdSnapshot) {
        console.log(`❌ [LOAD MORE] Room changed, aborting`)
        return
      }

      if (batch.length === 0) {
        setHasMoreMessages(false)
        hasMoreRef.current = false
      } else {
        // Add new messages
        const existingIds = new Set(currentRoomMessages.map((m) => m.id))
        const newMessages = batch.filter((msg) => !existingIds.has(msg.id))

        if (newMessages.length > 0) {
          setMessages((prev) => [
            ...newMessages.map((msg) => ({ ...msg, room_id: roomIdSnapshot })),
            ...prev,
          ])

          // Batch decrypt
          const encryptedBatch = newMessages.filter((msg) => msg.content_encrypted && msg.id)
          if (encryptedBatch.length > 0) {
            await decryptMessagesBatch(encryptedBatch, roomIdSnapshot)
          }
        }

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

  // ====================
  // WEBSOCKET MANAGEMENT
  // ====================

  /**
   * ⭐ REFACTORED: Connect to all rooms with improved message handling
   */
  async function connectToAllRooms(roomsToConnect) {
    const baseUrl = API_BASE_URL || window.location.origin
    const wsBase = baseUrl.replace('https://', 'wss://').replace('http://', 'ws://')
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : ''

    // Close existing
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

      const roomId = room.id
      const isGroupChat = room.is_group

      ws.onopen = () => {
        console.log(
          `✅ [WS] Connected to room: ${roomId} | type: ${isGroupChat ? 'GROUP' : '1-1'}`
        )
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          console.log(`📥 [WS] Received:`, data.type, `| room: ${roomId}`)

          // Log for debugging
          if (data.type === 'message' && data.id) {
            messageDebugger.logFrontendReceive(
              data.id,
              data.room_id || roomId,
              data.sender_name,
              data.content_encrypted || ''
            )
          }

          // ⭐ ALWAYS update room list (for inactive rooms too)
          if (data.type === 'message' && data.id) {
            const displayContent = '[encrypted]'
            const preview = isGroupChat && data.sender_name ? `${data.sender_name}: ${displayContent}` : displayContent

            setRooms((prevRooms) =>
              prevRooms.map((r) =>
                r.id === roomId
                  ? {
                      ...r,
                      last_message_preview: preview,
                      last_message_at: data.created_at || new Date().toISOString(),
                      last_message_sender_name: data.sender_name || 'Unknown',
                      has_unread: r.id !== activeRoomRef.current?.id,
                    }
                  : r
              ).sort((a, b) => {
                const timeA = new Date(a.last_message_at || 0).getTime()
                const timeB = new Date(b.last_message_at || 0).getTime()
                return timeB - timeA
              })
            )
          }

          // ⭐ KEY FIX: Only process messages for ACTIVE room
          const isActiveRoom = activeRoomRef.current?.id === roomId

          if (!isActiveRoom) {
            console.log(`⏭️ [WS] Message for inactive room ${roomId}, skipping processing`)
            return // EXIT EARLY
          }

          console.log(`📨 [WS] Processing for active room:`, roomId)

          if (data.type === 'system') {
            const isDuplicate = currentRoomEvents.some(
              (e) =>
                e.id === data.id &&
                e.sender_id === data.sender_id &&
                new Date().getTime() - new Date(e.created_at || e.timestamp).getTime() < 5000
            )
            if (!isDuplicate) {
              setEvents((prev) => [...prev, { ...data, room_id: roomId, type: 'system' }])
            }
          } else if (data.type === 'message' && data.id) {
            console.log(`📨 [WS] Adding message:`, data.id, `from:`, data.sender_name)

            messageDebugger.logFrontendAddToState(data.id)

            // ⭐ Add or replace message
            setMessages((prev) => {
              // Check if already exists
              const existingIndex = prev.findIndex((m) => m.id === data.id)

              if (existingIndex >= 0) {
                console.log(`⚠️  [WS] Message already exists, skipping duplicate`)
                return prev
              }

              const messageToAdd = { ...data, room_id: roomId }

              // ⭐ KEY FIX: If sender is current user, replace all temp messages for this room
              if (normalizeId(data.sender_id) === normalizeId(userIdRef.current)) {
                const filtered = prev.filter(
                  (m) => !(m.id.startsWith('temp-') && m.room_id === roomId)
                )
                return [...filtered, messageToAdd]
              }

              return [...prev, messageToAdd]
            })

            // ⭐ Decrypt if needed
            if (data.content_encrypted && data.id) {
              decryptMessageContent(data.id, data.content_encrypted, roomId).then((decrypted) => {
                // Room check
                if (activeRoomIdRef.current !== roomId) {
                  console.log(`❌ [WS] Room changed, skipping decrypt update for ${data.id}`)
                  return
                }

                if (!decrypted) return // Abort

                // Update message with decrypted content
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === data.id
                      ? {
                          ...msg,
                          content_decrypted: decrypted.plaintext,
                          message_hash: decrypted.message_hash,
                        }
                      : msg
                  )
                )

                // Verify
                performFullVerification(
                  { id: data.id, content_decrypted: decrypted.plaintext },
                  token,
                  true
                ).then((verification) => {
                  // Room check again
                  if (activeRoomIdRef.current !== roomId) return

                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === data.id
                        ? {
                            ...msg,
                            message_verified: verification.verified,
                            verification_timestamp: verification.timestamp,
                          }
                        : msg
                    )
                  )
                })
              })
            }

            setTimeout(scrollToBottom, 50)
          }
        } catch (e) {
          console.error('[WS] Parse error:', e)
        }
      }

      ws.onerror = () => {
        console.error(`❌ [WS] Error for room: ${roomId}`)
      }

      ws.onclose = () => {
        console.log(`[WS] Closed for room: ${roomId}`)
      }

      wsConnectionsRef.current.set(roomId, ws)
    })
  }

  // ====================
  // SEND MESSAGE
  // ====================

  /**
   * ⭐ REFACTORED: Send message with proper room context
   */
  async function handleSend() {
    if (!draft.trim() || !activeRoom) return

    const messageText = draft.trim()
    const tempId = `temp-${Date.now()}-${Math.random()}`
    const messageId = tempId

    messageDebugger.logSend(messageId, messageText, activeRoom.id, user?.id)

    // Optimistic update
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

    try {
      const ws = wsConnectionsRef.current.get(activeRoom.id)
      if (ws?.readyState === WebSocket.OPEN) {
        messageDebugger.logWebSocketSend(messageId, activeRoom.id)
        ws.send(JSON.stringify({ room_id: activeRoom.id, content: messageText }))
        messageDebugger.logWebSocketSendSuccess(messageId)
      } else {
        const err = new Error('Connection not open')
        messageDebugger.logWebSocketSendFailed(messageId, err)
        antMessage.error('Connection lost')
        // Remove optimistic
        setMessages((prev) => prev.filter((m) => m.id !== messageId))
      }
    } catch (error) {
      messageDebugger.logError('WEBSOCKET', messageId, error)
      antMessage.error('Failed to send message')
      setMessages((prev) => prev.filter((m) => m.id !== messageId))
    }
  }

  async function handleCreateRoom() {
    if (!roomForm.name.trim()) {
      antMessage.warning('Room name required')
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

      const updatedRooms = await listRooms()
      setRooms(updatedRooms || [])
      await connectToAllRooms(updatedRooms || [])

      setActiveRoom(newRoom)
      antMessage.success('Room created')
    } catch (error) {
      antMessage.error(error.message || 'Failed to create room')
    } finally {
      setIsCreating(false)
    }
  }

  // ====================
  // EFFECTS
  // ====================

  useEffect(() => {
    loadRooms()
  }, [])

  useEffect(() => {
    if (rooms.length > 0) {
      connectToAllRooms(rooms)
    }

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

  // ⭐ KEY FIX: Track active room and clear cache on room change
  useEffect(() => {
    const prevRoomId = activeRoomIdRef.current
    const newRoomId = activeRoom?.id

    activeRoomRef.current = activeRoom
    activeRoomIdRef.current = newRoomId

    console.log(
      `🔄 [ACTIVE ROOM] Changed from ${prevRoomId} to ${newRoomId} | name: ${activeRoom?.name}`
    )

    if (prevRoomId && newRoomId !== prevRoomId) {
      console.log(`🧹 [CACHE] Clearing pending decryptions on room change`)
      currentDecryptionsRef.current.clear()
      // ⭐ Clear cache for this specific room
      decryptedCacheRef.current.forEach((val, key) => {
        // Keep cache for non-current rooms
        // We only want to clear very large old caches
        if (decryptedCacheRef.current.size > 500) {
          decryptedCacheRef.current.clear()
        }
      })
    }
  }, [activeRoom?.id])

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
      { root: container, threshold: 0.1 }
    )

    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [activeRoom?.id, currentRoomMessages.length])

  // ====================
  // RENDER
  // ====================

  return (
    <div className="messenger-container">
      <aside className="messenger-sidebar">
        <div className="sidebar-top">
          <h2 className="sidebar-title">Chats</h2>
          <Button type="text" icon={<PlusOutlined />} className="compose-btn" onClick={() => setModalOpen(true)} />
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
                    {room.last_message_preview ? room.last_message_preview : room.is_group ? <TeamOutlined /> : <UserOutlined />}
                  </div>
                </div>
                {room.has_unread && <div className="unread-badge"></div>}
                {room.last_message_at && (
                  <div className="conv-time">
                    {new Date(room.last_message_at).toLocaleDateString('vi-VN', { month: 'short', day: 'numeric' })}
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
                  <h2 className="header-title">{directPeer?.username || activeRoom?.display_name || activeRoom?.name}</h2>
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
                  <p className="no-msg-desc">{activeRoom?.is_group ? <TeamOutlined /> : <UserOutlined />}</p>
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
                          {item.content_decrypted || <em style={{ color: '#999' }}>Decrypting...</em>}
                        </div>
                        {item.message_verified === true && (
                          <div className="message-verification" style={{ fontSize: '11px', marginTop: '4px', color: '#999' }}>
                            <span title="Message integrity verified">🔒 Verified</span>
                          </div>
                        )}
                        {item.message_verified === false && (
                          <div className="message-verification" style={{ fontSize: '11px', marginTop: '4px', color: '#ff4d4f' }}>
                            <span title="Message verification FAILED - possible tampering!">⚠️ Tampered</span>
                          </div>
                        )}
                        <div className="message-time">
                          {new Date(item.created_at || item.timestamp).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                          {showReadStatus && <span className="read-status">{item.is_read ? '✓✓' : '✓'}</span>}
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
                        antMessage.success('Member removed')
                      } catch (error) {
                        antMessage.error(error.message || 'Failed')
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
                      antMessage.success('Room deleted')
                      await loadRooms()
                      setActiveRoom(null)
                    } catch (error) {
                      antMessage.error(error.message || 'Failed')
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
            antMessage.warning('User ID required')
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
            antMessage.success('Member added')
          } catch (error) {
            antMessage.error(error.message || 'Failed to add member')
          }
        }}
        onCancel={() => {
          setMemberModalOpen(false)
          setMemberForm({ userId: '', role: 'member' })
        }}
        width={400}
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
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #d9d9d9',
              fontSize: '14px',
            }}
          >
            <option value="member">Member</option>
            <option value="admin">Admin</option>
          </select>
        </div>
      </Modal>
    </div>
  )
}

export default ChatPage
