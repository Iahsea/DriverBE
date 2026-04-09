import { request } from './client.js'

async function listFriends() {
  return request('/api/v1/friends')
}

async function listFriendRequests() {
  return request('/api/v1/friends/requests')
}

async function sendFriendRequest(toUserId) {
  return request('/api/v1/friends/request', {
    method: 'POST',
    body: JSON.stringify({ to_user_id: toUserId }),
  })
}

async function acceptFriendRequest(requestId) {
  return request(`/api/v1/friends/request/${requestId}/accept`, {
    method: 'POST',
  })
}

async function rejectFriendRequest(requestId) {
  return request(`/api/v1/friends/request/${requestId}/reject`, {
    method: 'POST',
  })
}

async function cancelFriendRequest(requestId) {
  return request(`/api/v1/friends/request/${requestId}/cancel`, {
    method: 'POST',
  })
}

async function deleteFriend(userId) {
  return request(`/api/v1/friends/${userId}`, {
    method: 'DELETE',
  })
}

export {
  listFriends,
  listFriendRequests,
  sendFriendRequest,
  acceptFriendRequest,
  rejectFriendRequest,
  cancelFriendRequest,
  deleteFriend,
}
