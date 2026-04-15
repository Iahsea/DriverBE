# 🔍 Message Flow Debug System

## 📋 Tóm tắt

Có **3 file chính** giúp debug quá trình gửi/nhận/giải mã tin nhắn:

### 1. **Frontend Debugger** (`messageDebugger.js`)
- Tự động track từng phase của message
- Ghi lại thời gian mỗi phase
- Cung cấp API để query/analyze

📍 `frontend/src/utils/messageDebugger.js`

### 2. **Backend Logging** (Updates to `main.py` & `messages.py`)
- Thêm 20 phase logs cho toàn bộ flow
- Track encryption, decryption, database operations
- Theo dõi WebSocket broadcast

📍 `main.py` (websocket handler)
📍 `app/api/v1/messages.py` (decrypt endpoint)

### 3. **Documentation**
- `DEBUG_MESSAGE_FLOW.md` - Hướng dẫn chi tiết từng phase
- `QUICK_DEBUG_REFERENCE.md` - Lệnh nhanh để debug

---

## 🚀 Quick Start

### Frontend Debugging (Browser Console)

```javascript
// Xem timeline và timing của một message
debugger.printFlowTimeline('message-id')
debugger.printMetrics('message-id')

// Xem tất cả messages và tìm bottlenecks
debugger.printAnalysisReport()

// Xem messages theo status
debugger.getMessagesByStatus()

// Tìm messages có delay > 100ms
debugger.findBottlenecks()
```

### Backend Debugging

Trong server logs, tìm những dòng này:

```
[🔄 PHASE 6] Backend receives from WebSocket
[🔐 PHASE 7] Starting encryption with driver
[✅ PHASE 8] Encryption success
[💾 PHASE 9] Saving to database
[📡 PHASE 11] Broadcasting to room members
[🔑 PHASE 15] Backend receives decrypt request
[🔓 PHASE 16] Starting decryption
[✅ PHASE 17] Decryption success
```

---

## 📊 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    MESSAGE FLOW DEBUG SYSTEM                     │
└─────────────────────────────────────────────────────────────────┘

🖥️  FRONTEND (Browser)
├─ [SEND] User gửi tin nhắn
│  └─ messageDebugger.logSend()
│
├─ [WEBSOCKET] Gửi qua WebSocket
│  ├─ messageDebugger.logWebSocketSend()
│  └─ messageDebugger.logWebSocketSendSuccess()
│
└─ [RECEIVE] Nhận từ WebSocket
   ├─ messageDebugger.logFrontendReceive()
   ├─ messageDebugger.logFrontendAddToState()
   │
   ├─ [DECRYPT] Gọi API decrypt
   │  ├─ messageDebugger.logFrontendDecryptRequest()
   │  ├─ messageDebugger.logFrontendDecryptResponse()
   │  └─ messageDebugger.logFrontendDisplay()
   │
   └─ [DISPLAY] Hiển thị UI


🗄️  BACKEND (Server)
├─ [PHASE 6] Backend nhận từ WebSocket
│  └─ logger.info("[🔄 PHASE 6]...")
│
├─ [PHASE 7-8] Encryption
│  ├─ logger.info("[🔐 PHASE 7]...")
│  └─ logger.info("[✅ PHASE 8]...")
│
├─ [PHASE 9-10] Database
│  ├─ logger.info("[💾 PHASE 9]...")
│  └─ logger.info("[✅ PHASE 10]...")
│
├─ [PHASE 11] Broadcast
│  └─ logger.info("[📡 PHASE 11]...")
│
└─ [PHASE 15-18] Decrypt API
   ├─ logger.info("[🔑 PHASE 15]...")
   ├─ logger.info("[🔓 PHASE 16]...")
   ├─ logger.info("[✅ PHASE 17]...")
   └─ logger.info("[📤 PHASE 18]...")

┌─────────────────────────────────────────────────────────────────┐
│                    TIMING EXPECTATIONS                           │
├─────────────────────────────────────────────────────────────────┤
│ SEND:                0ms  (immediate)                            │
│ WEBSOCKET SND:      20-50ms                                     │
│ BACKEND RECV:       30-100ms (network dependent)                │
│ ENCRYPT:            50-150ms (depends on key size)              │
│ DB SAVE:            10-50ms                                     │
│ BROADCAST:          10-50ms                                     │
│ FRONTEND RECV:      0-10ms (immediate)                          │
│ DECRYPT:            50-150ms (backend decryption)               │
│ DISPLAY:            50-100ms (UI update with React)             │
│ ─────────────────────────────────────────────────────────────   │
│ TOTAL:             120-250ms  ✅ HEALTHY                         │
│       > 500ms ⚠️ WARNING                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation Details

### Frontend Changes

**File:** `frontend/src/pages/ChatPage.jsx`
- Import: `import { debugger as messageDebugger } from '../utils/messageDebugger.js'`
- Updated `handleSend()` - added PHASE 1-3 logging
- Updated `onmessage` handler - added PHASE 12-13 logging
- Updated `decryptMessageContent()` - added PHASE 14-20 logging

### Backend Changes

**File:** `main.py` (WebSocket endpoint)
- Added PHASE 6-11 logging in websocket handler
- Track encryption, database, broadcast operations
- Enhanced error logging

**File:** `app/api/v1/messages.py` (decrypt endpoint)
- Added PHASE 15-18 logging in `decrypt_message()` endpoint
- Track decryption flow

### New Files

- `frontend/src/utils/messageDebugger.js` - Debug utility class
- `DEBUG_MESSAGE_FLOW.md` - Comprehensive debug guide
- `QUICK_DEBUG_REFERENCE.md` - Quick command reference

---

## 🎯 Use Cases

### 1. Fix Duplicate Messages
```javascript
// Check nếu có duplicate IDs
const allMessages = new Set()
debugger.messageFlows.forEach((flow, id) => {
  console.log(`Message: ${id}, Status: ${debugger.getMessageStatus(id)}`)
})

// Timeline của message bị duplicate
debugger.printFlowTimeline('duplicate-message-id')
```

### 2. Performance Optimization
```javascript
// Tìm slow phases
const bottlenecks = debugger.findBottlenecks()
console.table(bottlenecks)

// Chi tiết timing
debugger.printAnalysisReport()
```

### 3. Encryption/Decryption Issues
```bash
# Backend: Xem encryption errors
grep "PHASE 7\|PHASE 8\|ERROR" backend.log

# Frontend: Xem decryption errors
# In console: debugger.printFlowTimeline('message-id')
```

### 4. WebSocket Issues
```javascript
// Check WebSocket phases
const flow = debugger.messageFlows.get('message-id')
const wsPhases = flow.filter(p => p.phase.includes('WEBSOCKET'))
console.table(wsPhases)
```

---

## 📝 Sample Output

### Browser Console Output

```
[SEND] [     0ms] 📝 USER SENDS MESSAGE (temp-t46-89)
  messageId: "temp-t46-89"
  roomId: "room123"
  userId: "user456"
  content: "Hello world"

[WEBSOCKET] [    23ms] 📤 SENDING TO WEBSOCKET
  status: "attempting"

[WEBSOCKET] [    28ms] ✅ SENT TO WEBSOCKET
  messageId: "temp-t46-89"

[WEBSOCKET] [   125ms] 📥 BACKEND RECEIVES FROM WEBSOCKET
  roomId: "room123"
  senderName: "Alice"
  encryptedLength: 48

[RECEIVE] [   127ms] 📋 FRONTEND ADDING TO MESSAGE LIST
  status: "added_to_state"

[DECRYPT] [   150ms] 🔑 FRONTEND CALLING DECRYPT API
  endpoint: "/api/v1/messages/real-uuid-1234/decrypt"

[DECRYPT] [   215ms] ✅ FRONTEND RECEIVES DECRYPTED CONTENT
  plaintext: "Hello world"

[DISPLAY] [   220ms] 📺 FRONTEND DISPLAYING DECRYPTED MESSAGE
  content: "Hello world"
```

### Backend Log Output

```
[🔄 PHASE 6] Backend receives from WebSocket | msg_len=11 | from user 12345... in room room12...
[🔐 PHASE 7] Starting encryption with driver | content: Hello world | content_len=11
[✅ PHASE 8] Encryption success | encrypted_len=48 | encrypted_start: base64encryptedstring...
[💾 PHASE 9] Saving to database | plaintext: Hello world | encrypted: base64encryptedstring...
[✅ PHASE 10] Database saved | message_id: real-u...
[📡 PHASE 11] Broadcasting to room members | room: room12... | message_id: real-u... | encrypted_len: 48
[✅ PHASE 11+] Broadcast completed | message_id: real-u...

# Later, when decryptMessage is called:
[🔑 PHASE 15] Backend receives decrypt request | message_id: real-u... | user: Alice
[🔓 PHASE 16] Starting decryption | encrypted_len: 48 | encrypted_start: base64encryptedstring...
[✅ PHASE 17] Decryption success | plaintext_len: 11 | plaintext: Hello world
[📤 PHASE 18] Sending decrypt response | message_id: real-u... | plaintext: Hello world
```

---

## 📚 Related Documentation

1. **[DEBUG_MESSAGE_FLOW.md](./DEBUG_MESSAGE_FLOW.md)** - In-depth explanation of each phase
2. **[QUICK_DEBUG_REFERENCE.md](./QUICK_DEBUG_REFERENCE.md)** - Quick commands and scenarios
3. **[main.py](/main.py)** - WebSocket handler with logging (line ~318-390)
4. **[messages.py](/app/api/v1/messages.py)** - Decrypt endpoint with logging (line ~155+)

---

## ✅ Testing the Debug System

1. Open browser DevTools (F12)
2. Send a message in the chat
3. In console, run: `debugger.printAnalysisReport()`
4. Check frontend logs for PHASES 1-20
5. Check backend logs for PHASES 6-18 in websocket, PHASES 15-18 in decrypt
6. Use `debugger.printFlowTimeline('message-id')` to see detailed timeline

---

## 🧪 Known Limitations

- Debugger only tracks messages received after page load
- Temporary message IDs (temp-*) replaced with real UUIDs at phase 10
- Browser refresh clears all debug data
- Export/Import of debug sessions not yet implemented

---

## 🚀 Future Improvements

- [ ] Persist debug data to localStorage
- [ ] Export debug sessions as JSON
- [ ] Real-time dashboard view
- [ ] Comparison view for multiple message flows
- [ ] Performance regression detection
- [ ] Automated bottleneck alerts
