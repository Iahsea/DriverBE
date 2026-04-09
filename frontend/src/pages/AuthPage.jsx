import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { App as AntdApp, Card, Input, Button, Tabs, Divider } from 'antd'
import { MailOutlined, LockOutlined, ArrowRightOutlined, UserOutlined } from '@ant-design/icons'
import { useAuth } from '../store/auth.jsx'

function AuthPage() {
  const navigate = useNavigate()
  const { login, register } = useAuth()
  const { message } = AntdApp.useApp()
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [signupForm, setSignupForm] = useState({
    username: '',
    email: '',
    password: '',
    confirm: '',
  })
  const [loading, setLoading] = useState(false)

  async function handleLogin() {
    if (!loginForm.username || !loginForm.password) {
      message.warning('Please enter username and password')
      return
    }
    setLoading(true)
    try {
      await login(loginForm.username, loginForm.password)
      message.success('Login successful')
      navigate('/chat')
    } catch (error) {
      message.error(error.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleRegister() {
    if (!signupForm.username || !signupForm.email || !signupForm.password) {
      message.warning('Please complete all fields')
      return
    }
    if (signupForm.password !== signupForm.confirm) {
      message.warning('Passwords do not match')
      return
    }
    setLoading(true)
    try {
      await register(signupForm.username, signupForm.email, signupForm.password)
      message.success('Account created, please log in')
    } catch (error) {
      message.error(error.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-left">
        <div className="auth-brand">
          <div className="brand-mark">D</div>
          <div className="brand-name">The Digital Sanctuary</div>
        </div>
        <div className="auth-hero">
          <h1>Silence the noise. Secure the signal.</h1>
          <p>
            Enter a refined environment designed for high-stakes communication,
            where encryption is architectural and privacy is the default.
          </p>
        </div>
        <div className="auth-highlights">
          <div className="highlight-card">
            <div className="highlight-icon">&#128274;</div>
            <div>
              <div className="highlight-title">End-to-End Encryption</div>
              <div className="highlight-text">Military-grade protection for every message.</div>
            </div>
          </div>
          <div className="highlight-card">
            <div className="highlight-icon">&#128737;</div>
            <div>
              <div className="highlight-title">Hashed Security</div>
              <div className="highlight-text">Passwords are transformed using MD5 protocols.</div>
            </div>
          </div>
        </div>
        <div className="auth-footer">© 2026 The Digital Sanctuary</div>
      </div>

      <div className="auth-right">
        <Card className="auth-card" variant="borderless">
          <div className="auth-card-title">Access Command Center</div>
          <div className="auth-card-subtitle">
            Secure authentication required to join the thread.
          </div>

          <Tabs
            className="auth-tabs"
            items={[
              {
                key: 'login',
                label: 'Login',
                children: (
                  <div className="auth-form">
                    <label>Username</label>
                    <Input
                      prefix={<UserOutlined />}
                      placeholder="username"
                      value={loginForm.username}
                      onChange={(event) =>
                        setLoginForm({ ...loginForm, username: event.target.value })
                      }
                    />
                    <div className="password-row">
                      <label>Password</label>
                      <span className="forgot-link">Forgot?</span>
                    </div>
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder="••••••••"
                      value={loginForm.password}
                      onChange={(event) =>
                        setLoginForm({ ...loginForm, password: event.target.value })
                      }
                    />
                    <div className="auth-hint">Passwords are stored securely using MD5 hash protocols.</div>
                    <Button type="primary" className="primary-btn" block loading={loading} onClick={handleLogin}>
                      Enter Sanctuary <ArrowRightOutlined />
                    </Button>
                  </div>
                ),
              },
              {
                key: 'signup',
                label: 'Sign Up',
                children: (
                  <div className="auth-form">
                    <label>Username</label>
                    <Input
                      prefix={<UserOutlined />}
                      placeholder="username"
                      value={signupForm.username}
                      onChange={(event) =>
                        setSignupForm({ ...signupForm, username: event.target.value })
                      }
                    />
                    <label>Email address</label>
                    <Input
                      prefix={<MailOutlined />}
                      placeholder="name@sanctuary.com"
                      value={signupForm.email}
                      onChange={(event) =>
                        setSignupForm({ ...signupForm, email: event.target.value })
                      }
                    />
                    <label>Password</label>
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder="Create a secure password"
                      value={signupForm.password}
                      onChange={(event) =>
                        setSignupForm({ ...signupForm, password: event.target.value })
                      }
                    />
                    <label>Confirm password</label>
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder="Repeat your password"
                      value={signupForm.confirm}
                      onChange={(event) =>
                        setSignupForm({ ...signupForm, confirm: event.target.value })
                      }
                    />
                    <Button type="primary" className="primary-btn" block loading={loading} onClick={handleRegister}>
                      Create Access <ArrowRightOutlined />
                    </Button>
                  </div>
                ),
              },
            ]}
          />

          <Divider className="auth-divider">Identity Providers</Divider>
          <div className="auth-providers">
            <Button className="ghost-btn">Google</Button>
            <Button className="ghost-btn">SSO</Button>
          </div>
          <div className="auth-legal">
            Secure connection via SSL. <span className="linkish">Terms of Engagement</span>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default AuthPage
