import { Card, Button, Avatar, Switch, Input } from 'antd'
import { useAuth } from '../store/auth.jsx'

function SettingsPage() {
  const { user } = useAuth()
  const initial = user?.username?.slice(0, 1)?.toUpperCase() || 'U'

  return (
    <div className="settings-page">
      <div className="settings-left">
        <Card className="settings-card" variant="borderless">
          <h2>Account Settings</h2>
          <p>Manage your personal sanctuary and security protocols.</p>

          <div className="account-profile">
            <Avatar size={64}>{initial}</Avatar>
            <Button className="edit-avatar">Edit</Button>
            <div className="account-fields">
              <div>
                <label>Display name</label>
                <Input defaultValue={user?.username || ''} />
              </div>
              <div>
                <label>Handle</label>
                <Input defaultValue={`@${user?.username || 'user'}`} />
              </div>
              <div className="full">
                <label>Email address</label>
                <Input defaultValue={user?.email || ''} />
              </div>
            </div>
          </div>
        </Card>

        <Card className="settings-card" variant="borderless">
          <h3>Security Protocols</h3>
          <div className="security-item">
            <div>
              <div className="security-title">Master Password</div>
              <span>Last updated 14 days ago</span>
            </div>
            <Button type="link">Update</Button>
          </div>
          <div className="security-item">
            <div>
              <div className="security-title">Two-Factor Auth</div>
              <span>Recommended for high-security rooms</span>
            </div>
            <Switch defaultChecked />
          </div>
        </Card>
      </div>

      <div className="settings-right">
        <Card className="settings-card" variant="borderless">
          <h3>Preferences</h3>
          <div className="preference-item">
            <div>
              <div className="security-title">Direct Messages</div>
              <span>Instant push for incoming encrypted texts.</span>
            </div>
            <Switch defaultChecked />
          </div>
          <div className="preference-item">
            <div>
              <div className="security-title">Friend Events</div>
              <span>Alerts when contacts go online/offline.</span>
            </div>
            <Switch defaultChecked />
          </div>
          <div className="preference-item">
            <div>
              <div className="security-title">System Updates</div>
              <span>Critical sanctuary maintenance alerts.</span>
            </div>
            <Switch />
          </div>
          <div className="preference-item">
            <div>
              <div className="security-title">Invisible Mode</div>
              <span>Hide your online status from contacts.</span>
            </div>
            <Switch />
          </div>
        </Card>

        <div className="stats-row">
          <Card className="stat-card" variant="borderless">
            <div className="stat-label">Account Age</div>
            <div className="stat-value">1.4 Years</div>
          </Card>
          <Card className="stat-card" variant="borderless">
            <div className="stat-label">Secure Messages</div>
            <div className="stat-value">42,891</div>
          </Card>
          <Card className="stat-card" variant="borderless">
            <div className="stat-label">Encryption Tier</div>
            <div className="stat-value">Platinum</div>
          </Card>
        </div>

        <div className="settings-actions">
          <Button className="ghost-btn">Discard Changes</Button>
          <Button type="primary" className="primary-btn">Save Preferences</Button>
        </div>
      </div>
    </div>
  )
}

export default SettingsPage
