import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import AppShell from './components/AppShell.jsx'
import AuthPage from './pages/AuthPage.jsx'
import ChatPage from './pages/ChatPage.jsx'
import FriendsPage from './pages/FriendsPage.jsx'
import SettingsPage from './pages/SettingsPage.jsx'
import { useAuth } from './store/auth.jsx'
import './App.css'

function RequireAuth({ children }) {
  const { token, loading } = useAuth()
  if (loading) {
    return <div className="page-loading">Loading...</div>
  }
  if (!token) {
    return <Navigate to="/auth" replace />
  }
  return children
}

function App() {
  const { token } = useAuth()

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/auth" replace />} />
        <Route path="/auth" element={token ? <Navigate to="/chat" replace /> : <AuthPage />} />
        <Route
          path="/chat"
          element={
            <RequireAuth>
              <AppShell activeKey="chat">
                <ChatPage />
              </AppShell>
            </RequireAuth>
          }
        />
        <Route
          path="/friends"
          element={
            <RequireAuth>
              <AppShell activeKey="friends">
                <FriendsPage />
              </AppShell>
            </RequireAuth>
          }
        />
        <Route
          path="/settings"
          element={
            <RequireAuth>
              <AppShell activeKey="settings">
                <SettingsPage />
              </AppShell>
            </RequireAuth>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
