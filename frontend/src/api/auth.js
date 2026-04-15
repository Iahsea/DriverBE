import { request } from './client.js'

async function login(username, password) {
  return request('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

async function register(username, email, password) {
  return request('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password }),
  })
}

async function getMe() {
  return request('/api/v1/auth/me')
}

async function getUser(userId) {
  return request(`/api/v1/auth/users/${userId}`)
}

export { login, register, getMe, getUser }
