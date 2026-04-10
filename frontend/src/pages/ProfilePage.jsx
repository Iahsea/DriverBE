import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { App as AntdApp, Spin, Button, Card, Empty, Divider } from 'antd'
import { ArrowLeftOutlined, UserAddOutlined, MailOutlined, CalendarOutlined } from '@ant-design/icons'
import { getUser } from '../api/auth'
import { sendFriendRequest } from '../api/friends'
import { useAuth } from '../store/auth'
import '../styles/ProfilePage.css'

function ProfilePage() {
  const { userId } = useParams()
  const navigate = useNavigate()
  const { message } = AntdApp.useApp()
  const { user: currentUser } = useAuth()
  
  const [userProfile, setUserProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [friendStatus, setFriendStatus] = useState(null) // 'friend', 'pending', 'none'

  const isOwnProfile = currentUser?.id === userId

  useEffect(() => {
    async function fetchUserProfile() {
      if (!userId) return
      
      setLoading(true)
      try {
        const data = await getUser(userId)
        setUserProfile(data)
        
        // Set friend status (từ friends list hoặc requests)
        if (data.is_friend) {
          setFriendStatus('friend')
        } else if (data.is_pending) {
          setFriendStatus('pending')
        } else {
          setFriendStatus('none')
        }
      } catch (error) {
        message.error(error.message || 'Failed to load profile')
      } finally {
        setLoading(false)
      }
    }

    fetchUserProfile()
  }, [userId, message])

  async function handleAddFriend() {
    if (!userId) return
    
    setActionLoading(true)
    try {
      await sendFriendRequest(userId)
      setFriendStatus('pending')
      message.success('Friend request sent')
    } catch (error) {
      message.error(error.message || 'Failed to send request')
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="profile-page">
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
          <Spin size="large" />
        </div>
      </div>
    )
  }

  if (!userProfile) {
    return (
      <div className="profile-page">
        <Empty description="User not found" />
      </div>
    )
  }

  return (
    <div className="profile-page">
      <div className="profile-container">
        {/* Header */}
        <div className="profile-header">
          <Button 
            type="text" 
            icon={<ArrowLeftOutlined />}
            className="back-btn"
            onClick={() => navigate(-1)}
          >
            Back
          </Button>
          <h1>{isOwnProfile ? 'My Profile' : 'Profile'}</h1>
          <div style={{ width: 56 }} />
        </div>

        {/* Profile Card */}
        <div className="profile-card-wrapper">
          <Card className="profile-card" bordered={false}>
            {/* Avatar Section */}
            <div className="profile-top">
              <div className="profile-avatar">
                {userProfile.username?.slice(0, 1).toUpperCase()}
              </div>
              
              <div className="profile-header-info">
                <h2 className="profile-name">{userProfile.username}</h2>
                <p className="profile-email">{userProfile.email}</p>
              </div>

              {/* Action Buttons */}
              {!isOwnProfile && friendStatus !== 'friend' && (
                <div className="profile-actions">
                  {friendStatus === 'none' && (
                    <Button 
                      type="primary" 
                      icon={<UserAddOutlined />}
                      loading={actionLoading}
                      onClick={handleAddFriend}
                    >
                      Add Friend
                    </Button>
                  )}
                  {friendStatus === 'pending' && (
                    <Button disabled>
                      Pending
                    </Button>
                  )}
                </div>
              )}
            </div>

            <Divider />

            {/* Info Section */}
            <div className="profile-info">
              <div className="info-row">
                <div className="info-label">
                  <MailOutlined /> Email
                </div>
                <div className="info-value">{userProfile.email}</div>
              </div>

              <div className="info-row">
                <div className="info-label">
                  <CalendarOutlined /> Joined
                </div>
                <div className="info-value">
                  {new Date(userProfile.created_at).toLocaleDateString()}
                </div>
              </div>

              {userProfile.bio && (
                <div className="info-row">
                  <div className="info-label">Bio</div>
                  <div className="info-value">{userProfile.bio}</div>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default ProfilePage
