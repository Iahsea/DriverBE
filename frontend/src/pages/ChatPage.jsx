import { useEffect, useMemo, useRef, useState } from 'react'
import { App as AntdApp, Avatar, Button, Card, Divider, Tag, Input, Modal } from 'antd'
import { SendOutlined, PlusOutlined, LockOutlined } from '@ant-design/icons'
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

function normalizeId(value) {
  return value ? value.replace(/-/g, '').toLowerCase() : ''
}

function ChatPage() {
  const { message } = AntdApp.useApp()
  const { token, user } = useAuth()
  const [rooms, setRooms] = useState([])
  const [activeRoom, setActiveRoom] = useState(null)
  const [messages, setMessages] = useState([])
  const [events, setEvents] = useState([])
  const [draft, setDraft] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [roomForm, setRoomForm] = useState({ name: '', description: '' })
  const [roomDetails, setRoomDetails] = useState(null)
  const [memberModalOpen, setMemberModalOpen] = useState(false)
  const [memberForm, setMemberForm] = useState({ userId: '', role: 'member' })
  const wsRef = useRef(null)

  async function loadRooms() {
    try {
      const data = await listRooms()
      setRooms(data || [])
      if (data?.length) {
        setActiveRoom(data[0])
      }
    } catch (error) {
      message.error(error.message || 'Failed to load rooms')
    }
  }

  async function loadMessages(roomId) {
    try {
      const data = await getRoomMessages(roomId, 0, 50)
      setMessages(data.messages || [])
    } catch (error) {
      message.error(error.message || 'Failed to load messages')
    }
  }

  async function loadRoomDetails(roomId) {
    try {
      const data = await getRoom(roomId)
      setRoomDetails(data)
    } catch (error) {
      setRoomDetails(null)
    }
  }

  useEffect(() => {
    loadRooms()
  }, [])

  useEffect(() => {
    if (activeRoom?.id) {
      loadMessages(activeRoom.id)
      loadRoomDetails(activeRoom.id)
    }
  }, [activeRoom?.id])

  useEffect(() => {
    if (!activeRoom?.id || !token) {
      return undefined
    }

    const wsUrl = API_BASE_URL.replace('http', 'ws')
    const ws = new WebSocket(`${wsUrl}/ws/chat/${activeRoom.id}?token=${token}`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.type === 'system') {
          setEvents((prev) => [...prev, payload])
        } else if (payload.type === 'message') {
          setMessages((prev) => [...prev, payload])
        }
      } catch (error) {
        message.error('Invalid websocket message')
      }
    }

    ws.onerror = () => {
      message.error('WebSocket error')
    }

    return () => {
      ws.close()
    }
  }, [activeRoom?.id, token])

  useEffect(() => {
    const handler = () => setModalOpen(true)
    window.addEventListener('open-create-room', handler)
    return () => window.removeEventListener('open-create-room', handler)
  }, [])

  async function handleCreateRoom() {
    if (!roomForm.name) {
      message.warning('Room name is required')
      return
    }
    try {
      const created = await createRoom({
        name: roomForm.name,
        description: roomForm.description || 'Private room',
        is_group: true,
      })
      setModalOpen(false)
      setRoomForm({ name: '', description: '' })
      await loadRooms()
      setActiveRoom(created)
    } catch (error) {
      message.error(error.message || 'Failed to create room')
    }
  }

  function handleSend() {
    if (!draft || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return
    }
    wsRef.current.send(JSON.stringify({ content: draft }))
    setDraft('')
  }

  const roomTitle = activeRoom?.name || 'No rooms yet'
  const currentUserId = normalizeId(user?.id)
  const members = roomDetails?.members || []

  const combinedFeed = useMemo(() => {
    return [...events, ...messages].sort((a, b) => {
      const timeA = new Date(a.created_at || a.timestamp || 0).getTime()
      const timeB = new Date(b.created_at || b.timestamp || 0).getTime()
      return timeA - timeB
    })
  }, [events, messages])

  return (
    <div className="chat-page">
      <div className="chat-main">
        <div className="chat-header">
          <div>
            <div className="chat-title">{roomTitle}</div>
            <div className="chat-subtitle">
              <Tag color="green">AES-256 Encrypted</Tag>
            </div>
          </div>
          <div className="chat-avatars">
            <Avatar size={32}>{user?.username?.slice(0, 1).toUpperCase() || 'U'}</Avatar>
            <div className="chat-count">{rooms.length} rooms</div>
          </div>
        </div>

        <div className="chat-feed">
          {combinedFeed.map((item) => {
            if (item.type === 'system') {
              return (
                <Card className="chat-alert" variant="borderless" key={item.timestamp}>
                  <div className="alert-icon">
                    <LockOutlined />
                  </div>
                  <div>
                    <div className="alert-title">System</div>
                    <div className="alert-text">{item.content}</div>
                  </div>
                </Card>
              )
            }
            const isSelf = normalizeId(item.sender_id) === currentUserId
            return (
              <div className={`chat-bubble ${isSelf ? 'outgoing' : 'incoming'}`} key={item.id}>
                {!isSelf && (
                  <div className="bubble-meta">
                    <Avatar size={28}>{item.sender_name?.slice(0, 1).toUpperCase() || 'U'}</Avatar>
                    <span>{item.sender_name || 'Unknown'}</span>
                  </div>
                )}
                <p>{item.content}</p>
                {isSelf && <span className="bubble-time">You</span>}
              </div>
            )
          })}
          {combinedFeed.length === 0 && <div className="empty-state">No messages yet.</div>}
        </div>

        <div className="chat-input">
          <Button icon={<PlusOutlined />} className="circle-btn" onClick={() => setModalOpen(true)} />
          <Input
            placeholder="Type a secure message..."
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onPressEnter={handleSend}
          />
          <Button type="primary" icon={<SendOutlined />} className="circle-btn primary-btn" onClick={handleSend} />
        </div>
      </div>

      <div className="chat-side">
        <Card className="members-card" variant="borderless">
          <div className="card-title">Rooms</div>
          {rooms.map((room) => (
            <Button
              key={room.id}
              type={room.id === activeRoom?.id ? 'primary' : 'text'}
              className="room-pill"
              onClick={() => setActiveRoom(room)}
              block
            >
              {room.name}
            </Button>
          ))}
          {rooms.length === 0 && <div className="empty-state">Create your first room.</div>}
        </Card>

        <Card className="room-card" variant="borderless">
          <div className="room-avatar">&#128273;</div>
          <div className="room-title">{roomTitle}</div>
          <div className="room-subtitle">Secure group coordination.</div>
          <Divider />
          <div className="room-info">
            <div>
              <span>Privacy</span>
              <strong>End-to-End</strong>
            </div>
            <div>
              <span>Members</span>
              <strong>{members.length}</strong>
            </div>
          </div>
        </Card>

        <Card className="members-card" variant="borderless">
          <div className="card-title">Members</div>
          {members.map((member) => (
            <div className="member-item" key={member.id}>
              <Avatar size={32}>{member.username?.slice(0, 1).toUpperCase()}</Avatar>
              <div>
                <div>{member.username}</div>
                <span>{member.role}</span>
              </div>
              {member.user_id !== currentUserId && activeRoom?.id && (
                <Button
                  size="small"
                  className="ghost-btn"
                  onClick={async () => {
                    try {
                      await removeRoomMember(activeRoom.id, member.user_id)
                      await loadRoomDetails(activeRoom.id)
                    } catch (error) {
                      message.error(error.message || 'Failed to remove member')
                    }
                  }}
                >
                  Remove
                </Button>
              )}
            </div>
          ))}
          {members.length === 0 && <div className="empty-state">No members found.</div>}
          <Button className="ghost-btn" block onClick={() => setMemberModalOpen(true)} disabled={!activeRoom?.id}>
            Add Members
          </Button>
          <Button
            danger
            className="ghost-btn"
            block
            onClick={async () => {
              if (!activeRoom?.id) {
                return
              }
              try {
                await deleteRoom(activeRoom.id)
                message.success('Room deleted')
                await loadRooms()
                setActiveRoom(null)
              } catch (error) {
                message.error(error.message || 'Failed to delete room')
              }
            }}
            disabled={!activeRoom?.id}
          >
            Delete Room
          </Button>
        </Card>
      </div>

      <Modal
        title="Create Room"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleCreateRoom}
        okText="Create"
      >
        <Input
          placeholder="Room name"
          value={roomForm.name}
          onChange={(event) => setRoomForm({ ...roomForm, name: event.target.value })}
        />
        <Input
          placeholder="Description"
          value={roomForm.description}
          onChange={(event) => setRoomForm({ ...roomForm, description: event.target.value })}
          style={{ marginTop: 12 }}
        />
      </Modal>

      <Modal
        title="Add Member"
        open={memberModalOpen}
        onCancel={() => setMemberModalOpen(false)}
        onOk={async () => {
          if (!activeRoom?.id || !memberForm.userId) {
            message.warning('Provide user ID')
            return
          }
          try {
            await addRoomMember(activeRoom.id, {
              user_id: memberForm.userId,
              role: memberForm.role,
            })
            setMemberForm({ userId: '', role: 'member' })
            setMemberModalOpen(false)
            loadRoomDetails(activeRoom.id)
          } catch (error) {
            message.error(error.message || 'Failed to add member')
          }
        }}
        okText="Add"
      >
        <Input
          placeholder="User ID"
          value={memberForm.userId}
          onChange={(event) => setMemberForm({ ...memberForm, userId: event.target.value })}
        />
        <Input
          placeholder="Role (admin, moderator, member)"
          value={memberForm.role}
          onChange={(event) => setMemberForm({ ...memberForm, role: event.target.value })}
          style={{ marginTop: 12 }}
        />
      </Modal>
    </div>
  )
}

export default ChatPage
