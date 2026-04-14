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
import NotificationPanel from './NotificationPanel.jsx'

const { Sider, Header, Content } = Layout

function AppShell({ activeKey, children }) {
  const { user, logout, unreadCount } = useAuth()
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
            <Badge count={unreadCount} size="small" offset={[-4, 4]} color="#ff4d4f">
              <BellOutlined
                className="header-icon"
                onClick={() => setDrawerOpen(true)}
                style={{ fontSize: '18px', cursor: 'pointer' }}
              />
            </Badge>
            <Avatar className="header-avatar" size={32}>
              {initial}
            </Avatar>
          </div>
        </Header>
        <Content className="app-content">{children}</Content>
      </Layout>

      <Drawer
        title={null}
        placement="right"
        onClose={() => setDrawerOpen(false)}
        open={drawerOpen}
        width={360}
        bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column' }}
        headerStyle={{ display: 'none' }}
      >
        <NotificationPanel onClose={() => setDrawerOpen(false)} />
      </Drawer>
    </Layout>
  )
}

export default AppShell
