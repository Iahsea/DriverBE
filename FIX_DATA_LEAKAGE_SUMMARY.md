# Fix Data Leakage & "Still Decrypting" Issues

## 📋 Vấn đề Gốc Rễ

Khi chuyển tab giữa các cuộc chat:
1. **Data leakage**: Tin nhắn từ Chat A hiển thị trong Chat B
2. **Still decrypting**: Tin nhắn gửi đi vẫn hiển thị "Decrypting..." lâu

Nguyên nhân chính: **Race condition giữa promises từ room cũ và state update của room mới**

---

## 🔧 Các Thay Đổi Đã Làm

### 1. **Thêm Refs Để Tracking Room Change** (Dòng ~85-87)

```javascript
const activeRoomIdRef = useRef(null) // ⭐ Track activeRoom.id riêng
const decryptedCacheRef = useRef(new Map())
const currentDecryptionsRef = useRef(new Set()) // ⭐ Track pending decryptions
```

**Tác dụng**: Giúp detect room change nhanh và abort pending operations

---

### 2. **Fix `decryptMessageContent()` - Add Room Check** (Dòng ~115-170)

```javascript
const decryptMessageContent = async (messageId, contentEncrypted, roomId = null) => {
  // ✅ Add roomId parameter
  // ✅ Check room BEFORE and AFTER API call
  if (roomId && activeRoomIdRef.current !== roomId) {
    console.log('❌ Abort: room changed')
    return null // Return null = abort
  }
  
  // ... API call ...
  
  // ✅ Check AGAIN after API
  if (roomId && activeRoomIdRef.current !== roomId) {
    return null // Abort result if room changed
  }
}
```

**Tác dụng**: Decryption hủy bỏ nếu room thay đổi, không cập nhật state

---

### 3. **Fix `loadMessages()` - Reset Ngay & Pass RoomId** (Dòng ~215-275)

```javascript
async function loadMessages(roomId) {
  // ✅ RESET messages ngay tức kì
  setMessages([])
  setEvents([])
  
  const data = await getRoomMessages(roomId, 0, 30)
  
  // ✅ Check khi refresh - user có chuyển room không?
  if (activeRoomIdRef.current !== roomId) {
    console.log('❌ Room changed, abort')
    return
  }
  
  setMessages(batch) // Set mới
  
  // ✅ Pass roomId vào decryption
  batch.forEach((msg) => {
    decryptMessageContent(msg.id, msg.content_encrypted, roomId).then((decrypted) => {
      ✅ // Check room trước update
      if (activeRoomIdRef.current !== roomId) return
      
      // Update state
    })
  })
}
```

**Tác dụng**: 
- Messages reset ngay nên không mix với room cũ
- Decryption biết thuộc room nào
- Abort nếu room đã thay đổi

---

### 4. **Fix `loadMoreMessages()` - Cùng Logic** (Dòng ~305-390)

Cùng cách fix như `loadMessages()`:
- Pass `roomId` snapshot vào decryption
- Check room change trước update state
- Abort nếu room thay đổi

---

### 5. **Fix WebSocket Handler - Early Exit + RoomId Check** (Dòng ~450-570)

**Trước:**
```javascript
if (activeRoomRef.current?.id === roomId) {
  // Process message...
  decryptMessageContent(data.id, data.content_encrypted).then((decrypted) => {
    setMessages((prev) => {
      // Update - NHƯNG decrypted có thể từ room cũ!
    })
  })
}
```

**Sau:**
```javascript
// ⭐ Early exit - nếu room inactive, đừng process message
const isActiveRoom = activeRoomRef.current?.id === roomId
if (!isActiveRoom) {
  console.log('⏭️ Inactive room, skip')
  return // ← EXIT EARLY
}

// ⭐ Pass roomId vào decryption
if (data.content_encrypted) {
  decryptMessageContent(data.id, data.content_encrypted, roomId).then((decrypted) => {
    // ⭐ Check room TRƯỚC update state
    if (activeRoomIdRef.current !== roomId) {
      return
    }
    
    if (!decrypted) return // Abort signal
    
    // Update state
  })
}
```

**Tác dụng**: 
- Messages từ inactive room không được process
- Decryption abort nếu room thay đổi
- Prevent data leakage hoàn toàn

---

### 6. **Fix useEffect - Track activeRoomId & Clear State** (Dòng ~730-745)

```javascript
useEffect(() => {
  const prevRoomId = activeRoomIdRef.current
  const newRoomId = activeRoom?.id
  
  activeRoomRef.current = activeRoom
  activeRoomIdRef.current = newRoomId // ⭐ Update này QUAN TRỌNG
  
  // ⭐ Khi room thay đổi, clear pending decryptions
  if (prevRoomId && newRoomId !== prevRoomId) {
    console.log('🧹 Clearing pending state for room change')
    currentDecryptionsRef.current.clear()
  }
}, [activeRoom?.id, activeRoom])
```

**Tác dụng**: 
- `activeRoomIdRef` được update ĐÚNG LÚC
- Pending decryptions cleared khi room thay đổi
- Không có race condition

---

## 📊 Kết Quả

### ❌ Vấn đề Cũ
```
Time 0ms:   User ở Room A, 5 messages decrypting
Time 500ms: User chuyển Room B
Time 600ms: loadMessages(B) execute → setMessages([b1, b2])
Time 800ms: Promise từ msg_A resolve 
            → setMessages(prev => [...prev, content_A])  ← BUG!
Result:     Room B = [b1, b2, content_A]  ← DATA LEAKAGE!
```

### ✅ Cố định
```
Time 0ms:   User ở Room A, 5 messages decrypting
Time 500ms: User chuyển Room B → setActiveRoom(B)
            → activeRoomIdRef.current = B.id
            → setMessages([]) ← RESET
Time 600ms: loadMessages(B) execute → setMessages([b1, b2])
Time 800ms: Promise từ msg_A resolve
            → Check: activeRoomIdRef.current (B) !== roomId_A
            → return null ← ABORT!
            → NOT update state
Result:     Room B = [b1, b2]  ✅ CORRECT!
```

---

## 🧪 Cách Test Fix

1. **Mở Chat A** - xem tin nhắn tải đúng không
2. **Mở Chat B** - chuyển ngay lập tức
3. **Kiểm tra**: 
   - Messages từ Chat A không hiển thị ở Chat B
   - Messages Chat B tải đúng
4. **Gửi tin nhắn** - kiểm tra:
   - Người nhận nhận bình thường ✓
   - Người gửi decrypt xong (không "Decrypting..." lâu) ✓
5. **Chuyển room nhiều lần** - kiểm tra:
   - Không mix data
   - Không "still decrypting"

---

## 📝 Logs Để Debug

Các console.log được thêm vào:

```javascript
// Check room change
if (activeRoomIdRef.current !== roomId) {
  console.log('❌ Abort: room changed')
}

// Clear state
console.log('🧹 Clearing pending state for room change')

// Early exit
console.log('⏭️ Inactive room, skip')

// Room switched during operation
console.log('❌ Room changed, skipping decrypt update for', msg.id)
```

Mở DevTools Console để xem chi tiết.

---

## 🎯 Summary

| Vấn đề | Fix | Kết quả |
|-------|-----|---------|
| Data leakage | Early exit + room check | ✅ No message mix |
| "Still decrypting" | Abort promises + reset cache | ✅ Fast decrypt |
| Race condition | activeRoomIdRef tracking | ✅ Synchronized |
| Temp message mix | Only process active room | ✅ Correct temp handling |

