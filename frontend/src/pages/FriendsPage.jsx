import { useEffect, useMemo, useState } from 'react'
import { App as AntdApp, Card, Button, Avatar, Input, Tag, Badge, Modal } from 'antd'
import { UserAddOutlined } from '@ant-design/icons'
import {
  listFriends,
  listFriendRequests,
  sendFriendRequest,
  acceptFriendRequest,
  rejectFriendRequest,
  deleteFriend,
} from '../api/friends.js'

function FriendsPage() {
  const { message } = AntdApp.useApp()
  const [friends, setFriends] = useState([])
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [requestUserId, setRequestUserId] = useState('')

  async function fetchData() {
    setLoading(true)
    try {
      const [friendsData, requestData] = await Promise.all([
        listFriends(),
        listFriendRequests(),
      ])
      setFriends(friendsData.friends || [])
      setRequests(requestData.requests || [])
    } catch (error) {
      message.error(error.message || 'Failed to load friends')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const filteredFriends = useMemo(() => {
    if (!search) {
      return friends
    }
    return friends.filter((friend) =>
      friend.username.toLowerCase().includes(search.toLowerCase())
    )
  }, [friends, search])

  async function handleSendRequest() {
    if (!requestUserId) {
      message.warning('Enter user ID to invite')
      return
    }
    try {
      await sendFriendRequest(requestUserId)
      message.success('Friend request sent')
      setModalOpen(false)
      setRequestUserId('')
    } catch (error) {
      message.error(error.message || 'Failed to send request')
    }
  }

  async function handleAccept(requestId) {
    try {
      await acceptFriendRequest(requestId)
      message.success('Request accepted')
      fetchData()
    } catch (error) {
      message.error(error.message || 'Failed to accept')
    }
  }

  async function handleReject(requestId) {
    try {
      await rejectFriendRequest(requestId)
      message.info('Request declined')
      fetchData()
    } catch (error) {
      message.error(error.message || 'Failed to decline')
    }
  }

  async function handleDeleteFriend(userId) {
    try {
      await deleteFriend(userId)
      message.success('Friend removed')
      fetchData()
    } catch (error) {
      message.error(error.message || 'Failed to remove friend')
    }
  }

  return (
    <div className="friends-page">
      <div className="friends-hero">
        <Card className="hero-card" variant="borderless">
          <h2>Connect your world.</h2>
          <p>
            Expand your network within the sanctuary. Every connection is end-to-end
            encrypted by default.
          </p>
          <Button
            type="primary"
            icon={<UserAddOutlined />}
            className="primary-btn"
            onClick={() => setModalOpen(true)}
          >
            Add New Friend
          </Button>
        </Card>
        <Card className="score-card" variant="borderless">
          <div className="score-icon">&#128737;</div>
          <div className="score-label">Security Score</div>
          <div className="score-value">98%</div>
          <div className="score-text">All active channels are currently verified & secure.</div>
        </Card>
      </div>

      <div className="friends-content">
        <div className="friends-list">
          <div className="section-header">
            <h3>Active Friends</h3>
            <Input
              placeholder="Find a friend..."
              className="search-input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <div className="filter-tags">
              <Tag color="blue">All ({filteredFriends.length})</Tag>
              <Tag>Online</Tag>
            </div>
          </div>

          {filteredFriends.map((friend) => (
            <Card className="friend-card" variant="borderless" key={friend.id}>
              <Avatar size={48}>{friend.username.slice(0, 1).toUpperCase()}</Avatar>
              <div>
                <div className="friend-name">{friend.username}</div>
                <div className="friend-meta">{friend.email}</div>
              </div>
              <div className="friend-actions">
                <Badge status="success" />
                <Button className="ghost-btn" size="small" onClick={() => handleDeleteFriend(friend.id)}>
                  Remove
                </Button>
              </div>
            </Card>
          ))}
          {!loading && filteredFriends.length === 0 && (
            <div className="empty-state">No friends yet.</div>
          )}
        </div>

        <div className="friends-requests">
          <Card className="request-card" variant="borderless">
            <div className="card-title">Requests</div>
            {requests.map((request) => (
              <div className="request-item" key={request.id}>
                <Avatar size={40}>{request.from_username.slice(0, 1).toUpperCase()}</Avatar>
                <div>
                  <div className="friend-name">{request.from_username}</div>
                  <div className="friend-meta">wants to connect</div>
                </div>
                <div className="request-actions">
                  <Button type="primary" className="primary-btn" onClick={() => handleAccept(request.id)}>
                    Accept
                  </Button>
                  <Button className="ghost-btn" onClick={() => handleReject(request.id)}>
                    Decline
                  </Button>
                </div>
              </div>
            ))}
            {!loading && requests.length === 0 && (
              <div className="empty-state">No pending requests.</div>
            )}
          </Card>
          <Card className="tip-card" variant="borderless">
            <div className="card-title">Privacy Tip</div>
            <p>Your "Ghost Mode" is currently off. Toggle in settings anytime.</p>
          </Card>
        </div>
      </div>

      <Modal
        title="Add New Friend"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSendRequest}
        okText="Send Request"
      >
        <Input
          placeholder="Paste friend user ID"
          value={requestUserId}
          onChange={(event) => setRequestUserId(event.target.value)}
        />
      </Modal>
    </div>
  )
}

export default FriendsPage
