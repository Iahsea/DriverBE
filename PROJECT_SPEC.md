# AI Chat Project Template: Secure Socket Chat with Kernel-Mode Crypto

## 1. Purpose and Scope
Xây dựng hệ thống Chat bảo mật đa tầng hỗ trợ **1-to-1** và **Group Chat**, kết hợp giữa ứng dụng web hiện đại và mã hóa **Backend-side via Kernel Driver**:
* **Frontend:** Sử dụng **ReactJS** (Hooks, Context API/Redux) để xây dựng giao diện người dùng. **Gửi plaintext message** tới Backend qua WebSocket (không mã hóa ở client).
* **Backend:** Sử dụng **Python FastAPI** làm server điều phối, quản lý kết nối WebSocket, quản lý phòng chat. **Backend GỌI KERNEL DRIVER để mã hóa message** (AES-256-CBC) trước khi broadcast.
* **Backend Encryption via Driver:** Client gửi plaintext → Backend nhận → Backend gọi Driver encrypt (IOCTL) → Lưu plaintext + encrypted vào database → Broadcast encrypted tới members → Client nhận và có thể decrypt.
* **Authentication:** Dùng JWT token và Kernel Driver (**Windows KMDF** hoặc **Linux LKM**) để hash password (MD5).
* **Group Chat:** Hỗ trợ tạo phòng chat, thêm/xóa thành viên, quản lý quyền hạn (Admin, Member).
* **Friendship System:** Hỗ trợ gửi/chấp nhận lời mời kết bạn, quản lý danh sách bạn bè.
* **Target:** Thử nghiệm trên **Windows** trước khi triển khai chính thức trên **Ubuntu**.

---

## 2. Project Structure

secure-chat-system/
├── frontend-react/           # ReactJS: Giao diện người dùng
│   ├── src/
│   │   ├── components/       # ChatWindow, Message, Sidebar
│   │   ├── hooks/            # useSocket.js, useAuth.js
│   │   ├── context/          # AuthContext.js, SocketContext.js
│   │   └── services/         # api.js (Axios)
│   ├── public/
│   └── package.json
├── backend-fastapi/          # Python FastAPI: Điều phối và Logic
│   ├── app/
│   │   ├── core/             # crypto_bridge.py (Giao tiếp Driver qua ctypes)
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py   # POST /register, /login, GET /me
│   │   │       ├── rooms.py  # POST /rooms (create), GET /rooms (list), DELETE /rooms/{id}
│   │   │       ├── messages.py # POST /messages (history), GET /rooms/{id}/messages
│   │   │       └── friends.py  # Friend management endpoints (NEW)
│   │   ├── schemas/          # Pydantic models (DTOs)
│   │   │   ├── user.py       # UserCreate, UserLogin, UserResponse
│   │   │   ├── room.py       # RoomCreate, RoomResponse, RoomMemberResponse
│   │   │   ├── message.py    # MessageCreate, MessageResponse
│   │   │   └── friend.py     # FriendRequestCreate, FriendRequestResponse, ... (NEW)
│   │   └── websocket/        # WebSocket managers
│   │       ├── connection_manager.py  # Quản lý room subscriptions
│   │       └── notification_manager.py  # Quản lý notifications real-time (NEW)
│   ├── database/             # MySQL models (SQLAlchemy)
│   │   ├── database.py       # Engine, session factory
│   │   └── models.py         # User, Room, RoomMember, Message ORM models
│   ├── main.py
│   └── requirements.txt
├── kernel-module/            # C Source: Linux Kernel Driver
│   ├── crypto_driver.c       # AES & MD5 implementation
│   ├── crypto_driver.h       # IOCTL commands definitions
│   └── Makefile
└── windows-driver/           # Windows KMDF: Driver cho môi trường test

---

## 3. Database Schema
```sql
-- Users table
CREATE TABLE users (
    id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT 'UUID string',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT 'Tên đăng nhập',
    email VARCHAR(255) NOT NULL UNIQUE COMMENT 'Email',
    password_hash VARCHAR(64) NOT NULL COMMENT 'MD5 hash',
    is_active TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Tài khoản hoạt động',
    is_verified TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Email đã xác minh',
    created_at DATETIME NOT NULL COMMENT 'Thời gian tạo',
    updated_at DATETIME NOT NULL COMMENT 'Thời gian cập nhật',
    last_login_at DATETIME NULL COMMENT 'Lần đăng nhập gần nhất',
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Rooms table (1-to-1 hoặc Group Chat)
CREATE TABLE rooms (
    id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT 'UUID string',
    name VARCHAR(255) NOT NULL COMMENT 'Tên phòng chat',
    description TEXT COMMENT 'Mô tả phòng',
    is_group TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0: 1-to-1, 1: Group Chat',
    created_by_id VARCHAR(36) NOT NULL COMMENT 'User tạo phòng',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian tạo',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Thời gian cập nhật',
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_created_by (created_by_id),
    INDEX idx_is_group (is_group)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Room members (quản lý thành viên phòng chat)
CREATE TABLE room_members (
    id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT 'UUID string',
    room_id VARCHAR(36) NOT NULL COMMENT 'ID phòng',
    user_id VARCHAR(36) NOT NULL COMMENT 'ID user',
    role VARCHAR(20) NOT NULL DEFAULT 'member' COMMENT 'admin, moderator, member',
    joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian tham gia',
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_member (room_id, user_id),
    INDEX idx_room (room_id),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Messages table
CREATE TABLE messages (
    id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT 'UUID string',
    room_id VARCHAR(36) NOT NULL COMMENT 'ID phòng',
    sender_id VARCHAR(36) NOT NULL COMMENT 'ID người gửi',
    content TEXT NULL COMMENT 'Nội dung tin nhắn (DEPRECATED - for backward compatibility)',
    content_encrypted TEXT NOT NULL COMMENT 'Nội dung mã hóa bằng AES (E2EE - required)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian gửi',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Thời gian cập nhật',
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_room_created (room_id, created_at),
    INDEX idx_sender (sender_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Friend Requests table (Quản lý lời mời kết bạn)
CREATE TABLE friend_requests (
    id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT 'UUID string',
    from_user_id VARCHAR(36) NOT NULL COMMENT 'ID người gửi lời mời',
    to_user_id VARCHAR(36) NOT NULL COMMENT 'ID người nhận lời mời',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending, accepted, rejected, canceled',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian gửi lời mời',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Thời gian cập nhật',
    FOREIGN KEY (from_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (to_user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_request (from_user_id, to_user_id),
    INDEX idx_to_user_status (to_user_id, status),
    INDEX idx_from_user (from_user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Friendships table (Các cặp bạn bè đã chấp nhận)
CREATE TABLE friendships (
    id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT 'UUID string',
    user_id_1 VARCHAR(36) NOT NULL COMMENT 'ID user 1 (nhỏ hơn user_id_2)',
    user_id_2 VARCHAR(36) NOT NULL COMMENT 'ID user 2 (lớn hơn user_id_1)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian trở thành bạn',
    FOREIGN KEY (user_id_1) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id_2) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_friendship (user_id_1, user_id_2),
    INDEX idx_user1 (user_id_1),
    INDEX idx_user2 (user_id_2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 4. Guidelines for User Input
Để nhận được hỗ trợ chính xác nhất, người dùng cần cung cấp ngữ cảnh rõ ràng:
* **Phạm vi:** Nêu rõ đang yêu cầu code cho **React (Frontend)**, **FastAPI (Backend)** hay **C (Driver)**.
* **Môi trường:** Xác nhận đang code cho **Windows** (Winsock/IOCTL) hay **Linux** (POSIX/LKM).
* **Tương tác:** Hỏi về cách kết nối giữa các tầng, ví dụ: *"Tạo endpoint để tạo group chat" hoặc "Gửi tin nhắn tới room và mã hóa với Driver"*.

---

## 5. Conversation Scenarios

### Scenario 1: Tạo Group Chat
* **User:** "Tạo endpoint để tạo group chat mới."
* **AI:** "Tạo `POST /api/v1/rooms` endpoint:
  1. Validate room name, description
  2. Tạo Room object với is_group=1
  3. Thêm creator vào RoomMembers với role='admin'
  4. Trả về RoomResponse với list members"

### Scenario 2: Gửi tin nhắn tới Group (Backend Driver Encryption)
* **User:** "Gửi tin nhắn tới phòng chat group và mã hóa với Driver."
* **AI:** "Sử dụng WebSocket `/ws/chat/{room_id}`:
  1. Client gửi plaintext message
  2. Backend nhận plaintext
  3. Backend GỌI DRIVER encrypt (IOCTL_ENCRYPT_AES) - AES-256-CBC
  4. Lưu BOTH plaintext + encrypted vào Messages table
  5. Broadcast encrypted message tới tất cả members trong room
  6. Client nhận encrypted → giải mã hoặc hiển thị plaintext"

### Scenario 3: Quản lý thành viên (với Friendship)
* **User:** "Thêm user mới vào group chat."
* **AI:** "Tạo `POST /api/v1/rooms/{room_id}/members` endpoint:
  1. Verify user là admin của room
  2. **Verify admin và target user là bạn bè (check friendships table)**
  3. Nếu không phải bạn bè → Trả về 403 Forbidden
  4. Thêm user vào RoomMembers
  5. Broadcast notification tới tất cả members"

### Scenario 4: Frontend - Hiển thị list room
* **User:** "Viết component để hiển thị danh sách group chat."
* **AI:** "Tạo `RoomList` component:
  1. Call `GET /api/v1/rooms` để lấy danh sách rooms
  2. Render list với room name, member count, last message
  3. Click để open ChatWindow với `/ws/chat/{room_id}`"

### Scenario 5: Gửi lời mời kết bạn (NEW)
* **User:** "Gửi lời mời kết bạn tới user khác."
* **AI:** "Tạo `POST /api/v1/friends/request` endpoint:
  1. Validate from_user_id (current user) và to_user_id không trùng nhau
  2. Check xem chưa là bạn bè hoặc chưa có pending request
  3. Insert vào friend_requests table với status='pending'
  4. Trả về request info + status"

### Scenario 6: Chấp nhận lời mời kết bạn (NEW)
* **User:** "Chấp nhận lời mời kết bạn."
* **AI:** "Tạo `POST /api/v1/friends/request/{request_id}/accept` endpoint:
  1. Verify request tồn tại và to_user_id = current user
  2. Update friend_request status='accepted'
  3. Insert vào friendships table (tạo quan hệ bạn bè)
  4. Trả về success message
  5. Frontend có thể hiển thị thông báo: 'Bạn và {username} hiện là bạn bè'"

---

## 6. API Endpoints - Group Chat

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/v1/rooms` | Lấy danh sách phòng của user |
| POST | `/api/v1/rooms` | Tạo phòng chat mới |
| GET | `/api/v1/rooms/{id}` | Lấy chi tiết phòng + thành viên |
| DELETE | `/api/v1/rooms/{id}` | Xóa phòng (admin only) |
| POST | `/api/v1/rooms/{id}/members` | Thêm thành viên vào phòng **(Require: phải là bạn bè)** |
| DELETE | `/api/v1/rooms/{id}/members/{user_id}` | Xóa thành viên khỏi phòng |
| GET | `/api/v1/rooms/{id}/messages` | Lấy history tin nhắn |
| POST | `/api/v1/rooms/{id}/messages` | Gửi tin nhắn (qua REST hoặc WebSocket) |
| WS | `/ws/chat/{room_id}` | WebSocket để gửi/nhận tin nhắn real-time |

## 6.1. API Endpoints - Friendship Management (NEW)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/v1/friends` | Lấy danh sách bạn bè của user |
| GET | `/api/v1/friends/requests` | Lấy danh sách lời mời kết bạn đang chờ |
| POST | `/api/v1/friends/request` | Gửi lời mời kết bạn đến user khác |
| POST | `/api/v1/friends/request/{request_id}/accept` | Chấp nhận lời mời kết bạn |
| POST | `/api/v1/friends/request/{request_id}/reject` | Từ chối lời mời kết bạn |
| POST | `/api/v1/friends/request/{request_id}/cancel` | Hủy lời mời kết bạn (người gửi) |
| DELETE | `/api/v1/friends/{user_id}` | Xóa bạn/huỷ quan hệ bạn bè |

## 6.2. WebSocket Endpoints - Real-time Notifications (NEW)

| Endpoint | Mô tả | Connection |
|----------|-------|-----------|
| WS | `/ws/notifications` | Nhận thông báo real-time (lời mời kết bạn, chấp nhận, từ chối, ...) |
| WS | `/ws/chat/{room_id}` | Nhận tin nhắn real-time và thông báo group chat |

## 6.3. API Endpoints - Message Management (NEW - Backend Decryption)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/v1/messages/{message_id}` | Lấy chi tiết message (encrypted) |
| POST | `/api/v1/messages/{message_id}/decrypt` | **Giải mã message - Backend decrypt** |
| GET | `/api/v1/messages/room/{room_id}` | Lấy history messages của room (paginated) |

---

## 7. Instructions for the AI & User (Updated)
* **AI:** Phải nhớ Backend dùng **Python/FastAPI** và Frontend dùng **React**. Ưu tiên viết code sạch, sử dụng `async/await` cho Backend và Functional Components/Hooks cho Frontend. 
  - **Message Flow:** Backend MÃ HÓA (Driver) khi Client1 gửi, **Decrypt API** để Client2 giải mã khi request
  - Backend LUÔN lưu BOTH plaintext + encrypted vào database
  - Broadcast encrypted tới room members
  - Client2 có thể dùng plaintext từ WebSocket broadcast HOẶC call decrypt API để lấy plaintext
* **User:** Đảm bảo cài đặt đầy đủ môi trường (Python 3.10+, Node.js, C++ Build Tools) và chạy Terminal với quyền **Admin** khi test Driver trên Windows.

---

## 8. Message Flow - Friendship System (NEW)

### 1. Gửi lời mời kết bạn:
```
Client A → POST /api/v1/friends/request → Backend:
  - Validate: from_user & to_user không trùng
  - Check: Chưa là bạn hoặc chưa có pending request
  - Insert: friend_requests(from=A, to=B, status=pending)
  - Trả về: FriendRequestResponse
```

### 2. Chấp nhận lời mời kết bạn:
```
Client B → POST /api/v1/friends/request/{id}/accept → Backend:
  - Verify: request.to_user_id == current_user
  - Update: friend_requests status='accepted'
  - Insert: friendships(user_id_1, user_id_2) [sorted]
  - Notify: A và B hiện là bạn bè
```

### 3. Xem danh sách bạn bè:
```
Client A → GET /api/v1/friends → Backend:
  - Query: SELECT * FROM friendships WHERE user_id_1=A OR user_id_2=A
  - Extract: Danh sách ID bạn bè
  - Join: Với users table để lấy thông tin (name, avatar, ...)
  - Trả về: List[FriendResponse]
```

## 8.1. Message Flow - Group Chat (Backend Encryption via Kernel Driver)

### 1. Tạo phòng group:
```
Client → POST /api/v1/rooms → Backend:
  - Tạo Room(is_group=1)
  - Thêm creator vào RoomMembers(admin)
  - Trả về RoomResponse
```

### 2. Gửi tin nhắn tới group (Backend Driver Encryption):
```
┌─────────────────────────────────────────────────────────────────┐
│ CLIENT 1 SIDE:                                                  │
│   - User gõ message: "Hello"                                    │
│   - Client 1 gửi PLAINTEXT payload tới Backend                 │
│   - WebSocket: POST /ws/chat/{room_id}?token=JWT_TOKEN         │
│   - Message JSON: { "content": "Hello" }                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ BACKEND SIDE:                                                   │
│   1. Nhận plaintext message từ Client 1                        │
│   2. Verify user là member của room                            │
│   3. GỌI KERNEL DRIVER: encrypt_aes_with_driver()            │
│      - IOCTL_ENCRYPT_AES (AES-256-CBC)                        │
│      - Plaintext: "Hello" → Ciphertext: "x9a2b3c..."         │
│   4. Lưu vào Messages table:                                   │
│      - content = "Hello" (plaintext)                           │
│      - content_encrypted = "x9a2b3c..." (encrypted)           │
│   5. Broadcast tới tất cả members trong room:                  │
│      { "type": "message", "content_encrypted": "x9a2b3c..." }│
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ CLIENT 2,3,... SIDE:                                            │
│   - Nhận encrypted payload từ Backend                           │
│   - GỌI WEB CRYPTO API: decrypt AES-256-CBC                   │
│   - Ciphertext: "x9a2b3c..." → Plaintext: "Hello"            │
│   - Hiển thị plaintext message: "Hello"                        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1. Giải mã tin nhắn - Client2 Request Backend Decrypt (NEW):
```
CLIENT 2 SIDE:
  - Nhận encrypted payload từ WebSocket: { "content_encrypted": "x9a2b3c..." }
  - User click "View Message" hoặc decrypt tự động
  - Frontend call: POST /api/v1/messages/{message_id}/decrypt
  - Gửi HTTP request với JWT token

BACKEND SIDE:
  1. Xác thực JWT token
  2. Verify user là member của room chứa message
  3. Query Message từ database: message = db.query(Message).filter(id=message_id)
  4. Gọi crypto_bridge để decrypt:
     plaintext = await crypto_bridge.decrypt_message_payload(message.content_encrypted)
     - Hàm này:
       a) Base64 decode encrypted payload
       b) Extract IV (16 bytes đầu)
       c) Extract ciphertext (phần còn lại)
       d) Gọi Kernel Driver IOCTL_DECRYPT_AES (hoặc mock crypto)
       e) PKCS7 unpad plaintext
       f) Return plaintext string
  5. Trả về response:
     {
       "id": "message_id",
       "room_id": "room_id",
       "sender_id": "user_id",
       "content_plaintext": "Hello",  // ✓ Decrypted plaintext
       "created_at": "2026-04-09T...",
       "message": "Message decrypted successfully"
     }

CLIENT 2 SIDE (after decrypt):
  - Nhận plaintext từ API response
  - Hiển thị message: "Hello"
  - Hoặc cache result để dùng lần sau
```

### 2.2. Alternative - Client2 Use Plaintext từ WebSocket (Fallback):
```
Nếu không muốn call API decrypt (hoặc decrypt không work):
- Backend broadcast message cả plaintext + encrypted:
  {
    "type": "message",
    "content": "Hello",                    # ← Plaintext (fallback)
    "content_encrypted": "x9a2b3c..."     # ← Encrypted (main)
  }
- Client2 có thể hiển thị plaintext từ WebSocket luôn (không cần decrypt)
- Hoặc client2 thử decrypt encrypted (nếu có key)
```

### 3. Quản lý members (với Friendship validation):
```
Admin Client → POST /api/v1/rooms/{id}/members → Backend:
  - Validate: admin permissions
  - **NEW: Check friendships table - admin và new_user phải là bạn bè**
  - Nếu không phải bạn → Trả về 403: "Bạn phải là bạn với user này mới có thể thêm vào group"
  - Thêm new user vào RoomMembers table
  - Broadcast notification: "New member joined"
```

## 8.2. Message Flow - Real-time Friendship Notifications (NEW)

### 1. Gửi lời mời kết bạn (với notification):
```
Client A → POST /api/v1/friends/request → Backend:
  - Validate: from_user & to_user không trùng
  - Check: Chưa là bạn hoặc chưa có pending request
  - Insert: friend_requests(from=A, to=B, status=pending)
  - **NEW: Broadcast notification tới User B** (nếu B online ở /ws/notifications):
    {
      "type": "friend_request",
      "from_user_id": "<A_ID>",
      "from_username": "UserA",
      "request_id": "abc123...",
      "message": "UserA muốn kết bạn với bạn",
      "timestamp": "2026-04-09T10:30:00"
    }
  - Trả về: FriendRequestResponse
```

### 2. Chấp nhận lời mời kết bạn (với notification):
```
Client B → POST /api/v1/friends/request/{id}/accept → Backend:
  - Verify: request.to_user_id == current_user
  - Update: friend_requests status='accepted'
  - Insert: friendships(user_id_1, user_id_2) [sorted]
  - **NEW: Broadcast notification tới User A** (nếu A online ở /ws/notifications):
    {
      "type": "friend_request_accepted",
      "user_id": "<B_ID>",
      "username": "UserB",
      "message": "Bạn đã trở thành bạn với UserB",
      "timestamp": "2026-04-09T10:31:00"
    }
  - **NEW: Broadcast notification tới User B** (tự thông báo cho chính mình):
    {
      "type": "friend_request_accepted",
      "user_id": "<A_ID>",
      "username": "UserA",
      "message": "Bạn đã trở thành bạn với UserA",
      "timestamp": "2026-04-09T10:31:00"
    }
  - Trả về: FriendshipResponse
```

### 3. Từ chối lời mời kết bạn (với notification):
```
Client B → POST /api/v1/friends/request/{id}/reject → Backend:
  - Verify: request.to_user_id == current_user
  - Update: friend_requests status='rejected'
  - **NEW: Broadcast notification tới User A** (nếu A online ở /ws/notifications):
    {
      "type": "friend_request_rejected",
      "user_id": "<B_ID>",
      "username": "UserB",
      "message": "UserB đã từ chối lời mời kết bạn",
      "timestamp": "2026-04-09T10:32:00"
    }
  - Trả về: Success message
```

### 4. Hủy lời mời kết bạn (với notification):
```
Client A → POST /api/v1/friends/request/{id}/cancel → Backend:
  - Verify: request.from_user_id == current_user
  - Update: friend_requests status='canceled'
  - **NEW: Broadcast notification tới User B** (nếu B online ở /ws/notifications):
    {
      "type": "friend_request_canceled",
      "user_id": "<A_ID>",
      "username": "UserA",
      "message": "UserA đã hủy lời mời kết bạn",
      "timestamp": "2026-04-09T10:33:00"
    }
  - Trả về: Success message
```

### 5. Xóa bạn bè (với notification):
```
Client A → DELETE /api/v1/friends/{user_b_id} → Backend:
  - Query: Friendship với user_id_1 = min(A, B) và user_id_2 = max(A, B)
  - Delete: Friendship record
  - **NEW: Broadcast notification tới User B** (nếu B online ở /ws/notifications):
    {
      "type": "friend_deleted",
      "user_id": "<A_ID>",
      "username": "UserA",
      "message": "UserA đã xóa bạn bè với bạn",
      "timestamp": "2026-04-09T10:34:00"
    }
  - Trả về: Success message
```

### 6. WebSocket Connection Flow:
```
Client → WS /ws/notifications?token=JWT_TOKEN → Backend:
  - Backend xác thực JWT token
  - Add user vào online notification connections: {user_id: websocket}
  - Backend giữ connection sống bằng ping/pong
  
  Khi có sự kiện friend:
    - Backend tìm user_id trong connections
    - Gửi JSON notification tới user (nếu đang online)
    - Nếu user offline, notification bị miss (optional: lưu vào DB)

Client disconnect:
  - Remove user khỏi online connections
```

## 9. Current Database Status
- **Database**: MySQL `secure_chat` @ localhost:3306
- **User Table**: ✓ Created (id, username, email, password_hash, timestamps)
- **Room Tables**: ✓ Created (Room, RoomMember, Message models)
- **Friendship Tables**: ⏳ To be created (friend_requests, friendships)
- **Notification System**: ✓ In-memory (via WebSocket /ws/notifications, no DB persistence yet)
- **Message Encryption**: ✓ Backend-side AES-256-CBC via Kernel Driver (IOCTL_ENCRYPT_AES)
- **Message Decryption API**: ✓ POST /api/v1/messages/{message_id}/decrypt endpoint
- **Password Hashing**: ✓ MD5 via Kernel Driver (KMDF/LKM) or fallback mock
- **Backend Role**: 
  - ENCRYPT messages via Driver khi Client1 gửi
  - Store both plaintext + encrypted
  - Broadcast encrypted to room
  - DECRYPT messages via API khi Client2 request

## 10. Friendship System Rules
* **Kết bạn:** User phải gửi lời mời → user khác chấp nhận → tạo friendship record
* **Group Chat Restriction**: Chỉ có thể thêm bạn bè vào group chat. Nếu không phải bạn → Trả về error 403
* **1-to-1 Chat**: Có thể tạo room 1-to-1 mà không cần là bạn bè (tùy chọn tương lai: có thể yêu cầu friendship)
* **Friend List**: User chỉ thấy bạn bè là những người đã accept friend request (status='accepted')
* **Pending Requests**: Hiển thị riêng lời mời chờ nhận (status='pending')

## 10.1. Real-time Notification System Rules (NEW)

* **Notification Connection:** Mỗi user có thể kết nối tới `/ws/notifications` để nhận thông báo real-time
* **Notification Types:**
  - `friend_request`: Nhận khi user khác gửi lời mời kết bạn
  - `friend_request_accepted`: Nhận khi user khác chấp nhận lời mời của mình
  - `friend_request_rejected`: Nhận khi user khác từ chối lời mời của mình
  - `friend_request_canceled`: Nhận khi user khác hủy lời mời gửi tới mình
  - `friend_deleted`: Nhận khi user khác xóa bạn bè với mình
* **Real-time Delivery:** Notification chỉ được gửi nếu user đang online (connected tới `/ws/notifications`)
* **Offline Handling:** Nếu user offline, notification bị miss (optional: lưu vào database để sync sau)
* **Authentication:** Notification WebSocket yêu cầu JWT token trong query params: `?token=JWT_TOKEN`
* **Message Format:** JSON đồng nhất với `type`, `user_id`/`from_user_id`, `username`/`from_username`, `message`, `timestamp`
* **Broadcasting:** Mỗi sự kiện friend action phải broadcast tới tất cả users liên quan (sender + recipient)

## 11. Fallback & Troubleshooting (Backend Driver Encryption + Decrypt API)
* **Kernel Driver Usage:** Driver được dùng để:
  1. Hash password (MD5) - IOCTL_HASH_MD5 cho authentication
  2. Encrypt message (AES-256-CBC) - IOCTL_ENCRYPT_AES khi Client1 gửi
  3. Decrypt message (AES-256-CBC) - IOCTL_DECRYPT_AES khi call `/api/v1/messages/{id}/decrypt`
* **Backend sẽ tự động fallback sang mock crypto** nếu Driver không tìm thấy:
  - Windows KMDF driver not found → Use fallback Python cryptography library
  - /dev/crypto_chat_driver not found (Linux) → Use fallback mock
* **Message Decrypt API Flow:**
  - Client2 nhận encrypted message qua WebSocket
  - Client2 call: `POST /api/v1/messages/{message_id}/decrypt` (with JWT token)
  - Backend verify user là member của room
  - Backend call `crypto_bridge.decrypt_message_payload(ciphertext)` 
  - Backend trả về plaintext trong response
  - Client2 nhận và hiển thị plaintext
* **Message Storage:** Backend lưu CẢ plaintext và encrypted vào database:
  - `content` = plaintext (để hiển thị/broadcast)
  - `content_encrypted` = AES-256-CBC ciphertext (via Driver)
* **Error Handling:** 
  - Xử lý lỗi mất kết nối WebSocket trên React
  - Nếu Decrypt API thất bại: 401 (unauthorized), 403 (forbidden), 404 (not found), 422 (decrypt error)
  - User sẽ thấy error message: "Failed to decrypt message" hoặc specific error detail
* **Room Permissions**: Kiểm tra user là admin trước khi cho delete room hoặc manage members.
* **Friendship Validation**: Kiểm tra friendship record trước khi thêm member vào group (chặn non-friends).
* **Message Integrity**: Nếu ciphertext bị corruption, decrypt API sẽ return 422 "Decryption failed" - tự động phát hiện tampering.

## 11.1. Notification System Troubleshooting (NEW)
* **WebSocket Connection Fails**: Verify JWT token hợp lệ và user tồn tại trước khi accept connection
* **Lost Notification**: Nếu user disconnect/reconnect, miss notification không được recover (tính năng future)
* **Offline User Handling**: Backend không cố gắng gửi notification tới offline users, chỉ thử sending nếu connection tồn tại
* **Duplicate Notifications**: Tránh gửi duplicate bằng cách check connection.active_connections trước send
* **Memory Leak**: Luôn remove user khỏi notification_manager.active_connections khi disconnect (cleanup trong finally block)
* **Token Expiration**: Nếu JWT token hết hạn, user phải reconnect với token mới
* **Concurrent Notifications**: Sử dụng async/await để handle multiple concurrent notification sendings
* **Database Sync**: Nếu lưu notification vào DB, implement cron job để xóa stale notifications (>7 days)