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

async function searchPeople(query, limit = 20) {
  const params = new URLSearchParams({ query, limit: String(limit) })
  return request(`/api/v1/friends/search?${params.toString()}`)
}

async function listFriendSuggestions(limit = 8) {
  const params = new URLSearchParams({ limit: String(limit) })
  return request(`/api/v1/friends/suggestions?${params.toString()}`)
}

export {
  listFriends,
  listFriendRequests,
  sendFriendRequest,
  acceptFriendRequest,
  rejectFriendRequest,
  cancelFriendRequest,
  deleteFriend,
  searchPeople,
  listFriendSuggestions,
}
