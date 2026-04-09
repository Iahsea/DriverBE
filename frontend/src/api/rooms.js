import { request } from './client.js'

async function listRooms() {
  return request('/api/v1/rooms')
}

async function createRoom(payload) {
  return request('/api/v1/rooms', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

async function getRoomMessages(roomId, skip = 0, limit = 50) {
  return request(`/api/v1/rooms/${roomId}/messages?skip=${skip}&limit=${limit}`)
}

async function getRoom(roomId) {
  return request(`/api/v1/rooms/${roomId}`)
}

async function addRoomMember(roomId, payload) {
  return request(`/api/v1/rooms/${roomId}/members`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

async function removeRoomMember(roomId, userId) {
  return request(`/api/v1/rooms/${roomId}/members/${userId}`, {
    method: 'DELETE',
  })
}

async function deleteRoom(roomId) {
  return request(`/api/v1/rooms/${roomId}`, {
    method: 'DELETE',
  })
}

export { listRooms, createRoom, getRoomMessages, getRoom, addRoomMember, removeRoomMember, deleteRoom }
