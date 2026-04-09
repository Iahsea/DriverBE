import React from 'react'
import ReactDOM from 'react-dom/client'
import { App as AntdApp, ConfigProvider } from 'antd'
import App from './App.jsx'
import { AuthProvider } from './store/auth.jsx'
import 'antd/dist/reset.css'
import './index.css'

const theme = {
  token: {
    colorPrimary: '#0c4dd5',
    colorText: '#111827',
    colorTextSecondary: '#6b7280',
    borderRadius: 16,
    fontFamily: 'Space Grotesk, Segoe UI, Tahoma, sans-serif',
  },
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider theme={theme}>
      <AntdApp>
        <AuthProvider>
          <App />
        </AuthProvider>
      </AntdApp>
    </ConfigProvider>
  </React.StrictMode>,
)
