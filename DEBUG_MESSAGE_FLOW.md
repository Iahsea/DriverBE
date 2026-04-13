# Debug Message Flow - Hướng dẫn

## Tổng quan Flow

```
1️⃣  User gửi tin nhắn (SEND)
    → handleSend() in ChatPage.jsx
    → Generate temp message ID
    
2️⃣  Gửi qua WebSocket (WEBSOCKET)
    → ws.send(messageData) to /ws/chat/{room_id}
    
3️⃣  Backend nhận via WebSocket handler (main.py)
    → Verify JWT token
    → Extract plaintext content
    
4️⃣  Backend mã hóa bằng Kernel Driver (ENCRYPT)
    → Call crypto_bridge.encrypt_message_payload()
    → Driver returns encrypted ciphertext
    
5️⃣  Backend lưu vào Database (DB)
    → Save both plaintext + encrypted
    → Generate permanent message ID
    
6️⃣  Backend phát sóng (WEBSOCKET BROADCAST)
    → Send {id, room_id, sender_id, content_encrypted} to all room members
    
7️⃣  Frontend nhận từ WebSocket (RECEIVE)
    → onmessage handler
    → Parse JSON
    → Add to messages state (before decrypt)
    
8️⃣  Frontend gọi API decrypt (API REQUEST)
    → POST /api/v1/messages/{message_id}/decrypt
    → Send encrypted content to backend
    
9️⃣  Backend giải mã (DECRYPT)
    → Backend calls crypto_bridge.decrypt_message_payload()
    → Returns plaintext
    
🔟 Frontend nhận plaintext (API RESPONSE)
    → Update message state with decrypted content
    → Display in UI

⏱️  Tổng thời gian: ~100-500ms (tùy CPU)
```

## Cách xem Debug Logs

### 1. **Trên Frontend (Browser Console)**

Mở DevTools (F12 → Console tab)

```javascript
// Xem timeline của một message cụ thể
debugger.printFlowTimeline('message_id_here')

// Xem tất cả flows
debugger.printAllFlows()
```

**Giải thích màu sắc:**
- 🔴 **RED**: Gửi tin nhắn (SEND phase)
- 🔵 **BLUE**: WebSocket communication
- 🟢 **GREEN**: Nhận tin nhắn (RECEIVE phase)
- 🟡 **YELLOW**: Decrypt operations
- 🔵 **TEAL**: Encrypt operations
- 💜 **PLUM**: Display on UI (DISPLAY phase)
- 🟠 **ORANGE**: API calls

### 2. **Trên Backend (Server Logs)**

```bash
# Xem real-time logs
tail -f /path/to/backend.log | grep -E "PHASE|ERROR"

# Hoặc dùng journalctl nếu chạy with systemd
journalctl -u python-backend -f --no-pager
```

**Log Pattern:**
```
[🔄 PHASE 6] Backend receives from WebSocket | msg_len=15 | from user abc12345... in room def67890...
[🔐 PHASE 7] Starting encryption with driver | content: Hello world pad! | content_len=15
[✅ PHASE 8] Encryption success | encrypted_len=48 | encrypted_start: base64encryptedtext...
[💾 PHASE 9] Saving to database | plaintext: Hello world pad! | encrypted: base64encryptedtext...
[✅ PHASE 10] Database saved | message_id: msg12345...
[📡 PHASE 11] Broadcasting to room members | room: room1234... | message_id: msg12345... | encrypted_len: 48
```

### 3. **Theo dõi Message từ đầu đến cuối**

**Ví dụ: Gửi "Hello" từ User A sang Group:**

```
Frontend (User A):
[SEND] 📝 USER SENDS MESSAGE (temp-time-12345)
[WEBSOCKET] 📤 SENDING TO WEBSOCKET 
[WEBSOCKET] ✅ SENT TO WEBSOCKET

Backend (Server):
[🔄 PHASE 6] Backend receives from WebSocket
[🔐 PHASE 7] Starting encryption with driver
[✅ PHASE 8] Encryption success
[💾 PHASE 9] Saving to database
[✅ PHASE 10] Database saved | message_id: real-uuid-1234
[📡 PHASE 11] Broadcasting to room members

Frontend (All members in room):
[RECEIVE] 📥 FRONTEND RECEIVES FROM WEBSOCKET
[RECEIVE] 📋 FRONTEND ADDING TO MESSAGE LIST
[DECRYPT] 🔑 FRONTEND CALLING DECRYPT API
    ↓ HTTP POST /api/v1/messages/real-uuid-1234/decrypt

Backend (Decrypt):
[🔑 PHASE 15] Backend receives decrypt request
[🔓 PHASE 16] Starting decryption
[✅ PHASE 17] Decryption success
[📤 PHASE 18] Sending decrypt response

Frontend (Final):
[✅ PHASE 19] FRONTEND RECEIVES DECRYPTED CONTENT
[DISPLAY] 📺 FRONTEND DISPLAYING DECRYPTED MESSAGE
```

## Cách Debugging

### 1. **Kiểm tra có bị duplicate message:**

Mở browser console và chạy:
```javascript
// Tìm message IDs trong state
window.messageIds = // pass into console from React debugger tree
// Hoặc:
console.log(document.querySelectorAll('[data-message-id]').map(el => el.dataset.messageId))
```

### 2. **Kiểm tra encryption/decryption:**

Backend logs:
```bash
grep "PHASE 7\|PHASE 8\|PHASE 16\|PHASE 17" backend.log
```

### 3. **Kiểm tra WebSocket communication:**

Frontend console:
```javascript
// Tất cả WebSocket messages
debugger.printAllFlows()

// Timeline của message cụ thể
debugger.printFlowTimeline('message-id')
```

### 4. **Kiểm tra Database:**

```sql
SELECT id, sender_id, content, content_encrypted, created_at 
FROM message 
ORDER BY created_at DESC 
LIMIT 5;
```

## Phổ biến Issues & Cách Debug

### Issue 1: Duplicate Messages
```
👉 DEBUG: 
- Check browser console: debugger.printAllFlows()
- Check duplicate message IDs
- Check WebSocket message flow timestamp
- Xem phase 13 (FRONTEND ADDING TO MESSAGE LIST)
```

### Issue 2: Message không decrypt
```
👉 DEBUG:
- Backend log PHASE 16 có error không?
- Frontend log PHASE 19 có error không?
- Check encrypted content not null
- Check message_id format
```

### Issue 3: Encryption/Decryption fail
```
👉 DEBUG:
- Backend log PHASE 7 success?
- Backend log PHASE 8 success?
- Check driver logs: sudo dmesg | tail -20
- Check if driver loaded: lsmod | grep crypto_chat_driver
```

### Issue 4: WebSocket not connected
```
👉 DEBUG:
- Browser console: ws connection status
- Check token valid
- Check JWT not expired
- Check room_id correct
```

## API to get Debug Data Programmatically

```javascript
// Get all message flows
const flows = debugger.messageFlows

// Get specific message flow
const flow = debugger.messageFlows.get('message-id')

// Get metrics
const phases = flow.map(f => ({ phase: f.phase, duration: f.time }))
const totalTime = flow[flow.length - 1].time
console.log(`Total time: ${totalTime}ms`)
```

## Best Practices untuk Debugging

1. **Always check PHASE numbers in order** - They should be sequential without gaps
2. **Check timestamps** - Look for unexpected delays (> 1000ms)
3. **Check error messages** - Look for ERROR lines in logs
4. **Cross-check frontend & backend logs** - Match message IDs
5. **Monitor encrypted payload size** - Should be ~16 bytes larger than plaintext (IV + padding)
6. **Check for race conditions** - Multiple messages at same time
