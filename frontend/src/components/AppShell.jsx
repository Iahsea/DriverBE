import { useState } from 'react'
import { Layout, Button, Avatar, Badge, Input, Drawer } from 'antd'
import {
  MessageOutlined,
  TeamOutlined,
  SettingOutlined,
  BellOutlined,
  SearchOutlined,
  LogoutOutlined,
  PlusOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons'
import { Link } from 'react-router-dom'
import { useAuth } from '../store/auth.jsx'

const { Sider, Header, Content } = Layout

function AppShell({ activeKey, children }) {
  const { user, logout, notifications } = useAuth()
  const initial = user?.username?.slice(0, 1)?.toUpperCase() || 'U'
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <Layout className="app-shell">
      <Sider width={240} className="app-sider" theme="light">
        <div className="brand">
          <div className="brand-mark">D</div>
          <div>
            <div className="brand-name">Digital Sanctuary</div>
            <div className="brand-sub">Secure connection</div>
          </div>
        </div>

        <div className="side-actions">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            className="primary-btn"
            block
            onClick={() => window.dispatchEvent(new CustomEvent('open-create-room'))}
          >
            New Message
          </Button>
        </div>

        <div className="side-menu">
          <Link className={activeKey === 'chat' ? 'side-link active' : 'side-link'} to="/chat">
            <MessageOutlined />
            <span>Chat</span>
          </Link>
          <Link className={activeKey === 'friends' ? 'side-link active' : 'side-link'} to="/friends">
            <TeamOutlined />
            <span>Friends</span>
          </Link>
          <Link className={activeKey === 'settings' ? 'side-link active' : 'side-link'} to="/settings">
            <SettingOutlined />
            <span>Settings</span>
          </Link>
        </div>

        <div className="side-footer">
          <Button icon={<QuestionCircleOutlined />} type="text" className="side-footer-btn">
            Help
          </Button>
          <Button icon={<LogoutOutlined />} type="text" className="side-footer-btn" onClick={logout}>
            Logout
          </Button>
          <div className="side-profile">
            <Avatar size={36}>{initial}</Avatar>
            <div>
              <div className="side-profile-name">{user?.username || 'Anonymous'}</div>
              <div className="side-profile-email">{user?.email || 'unknown@sanctuary'}</div>
            </div>
          </div>
        </div>
      </Sider>

      <Layout className="app-main">
        <Header className="app-header">
          <div className="header-left">
            <Input
              className="header-search"
              placeholder="Search"
              prefix={<SearchOutlined />}
            />
          </div>
          <div className="header-right">
            <Badge count={notifications.length} size="small" offset={[4, -2]}>
              <BellOutlined className="header-icon" onClick={() => setDrawerOpen(true)} />
            </Badge>
            <Avatar className="header-avatar" size={32}>
              {initial}
            </Avatar>
          </div>
        </Header>
        <Content className="app-content">{children}</Content>
      </Layout>

      <Drawer
        title="Notifications"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      >
        {notifications.length === 0 && (
          <div className="empty-state">No notifications yet.</div>
        )}
        {notifications.map((item, index) => (
          <div className="notification-item" key={`${item.type}-${item.timestamp || index}`}>
            <div className="notification-type">{item.type}</div>
            <div className="notification-message">{item.message || 'Update received'}</div>
            <div className="notification-time">{item.timestamp}</div>
          </div>
        ))}
      </Drawer>
    </Layout>
  )
}

export default AppShell
