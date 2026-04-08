# AI Chat Project Template: Secure Socket Chat with Kernel-Mode Crypto

## 1. Purpose and Scope
Xây dựng hệ thống Chat bảo mật đa tầng hỗ trợ **1-to-1** và **Group Chat**, kết hợp giữa ứng dụng web hiện đại và bảo mật cấp thấp (Kernel-level):
* **Frontend:** Sử dụng **ReactJS** (Hooks, Context API/Redux) để xây dựng giao diện người dùng.
* **Backend:** Sử dụng **Python FastAPI** làm server điều phối, quản lý kết nối WebSocket, quản lý phòng chat và giao tiếp với Driver.
* **Kernel Security:** Mọi hoạt động mã hóa **AES** và băm **MD5** phải thực hiện trong **Kernel Driver** (Windows KMDF hoặc Linux LKM) thông qua cơ chế IOCTL.
* **Group Chat:** Hỗ trợ tạo phòng chat, thêm/xóa thành viên, quản lý quyền hạn (Admin, Member).
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
│   │   │       └── messages.py # POST /messages (history), GET /rooms/{id}/messages
│   │   ├── schemas/          # Pydantic models (DTOs)
│   │   │   ├── user.py       # UserCreate, UserLogin, UserResponse
│   │   │   ├── room.py       # RoomCreate, RoomResponse, RoomMemberResponse
│   │   │   └── message.py    # MessageCreate, MessageResponse
│   │   └── websocket/        # connection_manager.py (quản lý room subscriptions)
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
    content TEXT NOT NULL COMMENT 'Nội dung tin nhắn (plaintext hoặc encrypted)',
    content_encrypted TEXT COMMENT 'Nội dung mã hóa bằng AES',
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

### Scenario 2: Gửi tin nhắn tới Group
* **User:** "Gửi tin nhắn tới phòng chat group và mã hóa với Driver."
* **AI:** "Sử dụng WebSocket `/ws/chat/{room_id}`:
  1. Client gửi message
  2. Backend hash/encrypt với crypto_bridge
  3. Lưu vào Messages table
  4. Broadcast tới tất cả members trong room"

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

## 7. Instructions for the AI & User
* **AI:** Phải nhớ Backend dùng **Python/FastAPI** và Frontend dùng **React**. Ưu tiên viết code sạch, sử dụng `async/await` cho Backend và Functional Components/Hooks cho Frontend. Group Chat phải quản lý room subscriptions và member permissions.
* **User:** Đảm bảo cài đặt đầy đủ môi trường (Python 3.10+, Node.js, C++ Build Tools) và chạy Terminal với quyền **Admin** khi test Driver trên Windows. Khi tạo group chat, luôn verify permissions (creator là admin).

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

## 8.1. Message Flow - Group Chat (Cập nhật với Friendship)

### 1. Tạo phòng group:
```
Client → POST /api/v1/rooms → Backend:
  - Tạo Room(is_group=1)
  - Thêm creator vào RoomMembers(admin)
  - Trả về RoomResponse
```

### 2. Gửi tin nhắn tới group:
```
Client 1 → WS /ws/chat/{room_id} → Backend:
  - Nhận message từ client
  - Verify user là member của room
  - Hash/Encrypt với crypto_bridge
  - Lưu vào Messages table
  - Broadcast tới tất cả members (client trong room)
  - Client 2, 3, ... nhận message
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

## 9. Current Database Status
- **Database**: MySQL `secure_chat` @ localhost:3306
- **User Table**: ✓ Created (id, username, email, password_hash, timestamps)
- **Room Tables**: ✓ Created (Room, RoomMember, Message models)
- **Friendship Tables**: ⏳ To be created (friend_requests, friendships)
- **Encryption**: Fallback mock AES + MD5 via crypto_bridge (real driver pending)

## 10. Friendship System Rules
* **Kết bạn:** User phải gửi lời mời → user khác chấp nhận → tạo friendship record
* **Group Chat Restriction**: Chỉ có thể thêm bạn bè vào group chat. Nếu không phải bạn → Trả về error 403
* **1-to-1 Chat**: Có thể tạo room 1-to-1 mà không cần là bạn bè (tùy chọn tương lai: có thể yêu cầu friendship)
* **Friend List**: User chỉ thấy bạn bè là những người đã accept friend request (status='accepted')
* **Pending Requests**: Hiển thị riêng lời mời chờ nhận (status='pending')

## 11. Fallback & Troubleshooting
* **Mocking:** Nếu chưa có Driver, AI sẽ cung cấp mã giả lập (Mock) trong `crypto_bridge.py` bằng thư viện `cryptography` của Python để test luồng Socket.
* **Error Handling:** Luôn xử lý lỗi mất kết nối WebSocket trên React và lỗi Timeout khi gọi xuống Driver từ FastAPI.
* **Room Permissions**: Kiểm tra user là admin trước khi cho delete room hoặc manage members.
* **Friendship Validation**: Kiểm tra friendship record trước khi thêm member vào group (chặn non-friends)
* **Message Encryption**: Hiện tại lưu plaintext + encrypted version; cần migrate tới chỉ encrypted.