import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { Layout, Button, Menu, Avatar, Dropdown, Badge, Drawer } from 'antd'
import {
  MessageOutlined,
  TeamOutlined,
  SettingOutlined,
  LogoutOutlined,
  BellOutlined,
} from '@ant-design/icons'
import AuthPage from './pages/AuthPage'
import ChatPage from './pages/ChatPage'
import FriendsPage from './pages/FriendsPage'
import ProfilePage from './pages/ProfilePage'
import NotificationPanel from './components/NotificationPanel'
import { useAuth } from './store/auth'
import './App.css'

function AppShell({ children }) {
  const { user, logout, unreadCount } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const [notificationDrawerOpen, setNotificationDrawerOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    {
      key: '/chat',
      icon: <MessageOutlined />,
      label: 'Chat',
    },
    {
      key: '/friends',
      icon: <TeamOutlined />,
      label: 'Friends',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
  ]

  const userMenu = {
    items: [
      {
        key: 'profile',
        icon: <MessageOutlined />,
        label: 'View Profile',
        onClick: () => navigate(`/profile/${user?.id}`),
      },
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: 'Logout',
        onClick: logout,
      },
    ],
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Sider trigger={null} collapsible collapsed={collapsed} width={240}>
        <div className="logo">
          <h2 style={{ color: '#ffffff', margin: 0 }}>SecureChat</h2>
        </div>
        <Menu
          theme="dark"
          items={menuItems}
          selectedKeys={[location.pathname]}
          onClick={({ key }) => navigate(key)}
        />
      </Layout.Sider>

      <Layout>
        <div className="app-header">
          <div className="header-left">
            <Button
              type="text"
              onClick={() => setCollapsed(!collapsed)}
              style={{ color: '#65676b', fontSize: 18 }}
            >
              ☰
            </Button>
          </div>

          <div className="header-right">
            <Badge count={unreadCount} size="small" offset={[-4, 4]} color="#ff4d4f">
              <Button 
                type="text" 
                icon={<BellOutlined />} 
                onClick={() => setNotificationDrawerOpen(true)}
                style={{ fontSize: 18 }}
              />
            </Badge>
            <Dropdown menu={userMenu} trigger={['click']}>
              <Avatar style={{ backgroundColor: '#1890ff', cursor: 'pointer' }}>
                {user?.username?.slice(0, 1).toUpperCase() || 'U'}
              </Avatar>
            </Dropdown>
          </div>
        </div>

        <div className="app-content">{children}</div>
      </Layout>

      <Drawer
        title={null}
        placement="right"
        onClose={() => setNotificationDrawerOpen(false)}
        open={notificationDrawerOpen}
        width={360}
        bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column' }}
        headerStyle={{ display: 'none' }}
      >
        <NotificationPanel onClose={() => setNotificationDrawerOpen(false)} />
      </Drawer>
    </Layout>
  )
}

function App() {
  const { token } = useAuth()

  return (
    <Router>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        <Route
          path="/chat"
          element={token ? <AppShell><ChatPage /></AppShell> : <Navigate to="/auth" />}
        />
        <Route
          path="/friends"
          element={token ? <AppShell><FriendsPage /></AppShell> : <Navigate to="/auth" />}
        />
        <Route
          path="/profile/:userId"
          element={token ? <AppShell><ProfilePage /></AppShell> : <Navigate to="/auth" />}
        />
        <Route path="/" element={<Navigate to={token ? '/chat' : '/auth'} />} />
      </Routes>
    </Router>
  )
}

export default App
