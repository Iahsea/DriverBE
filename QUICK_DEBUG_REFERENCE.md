# Debug Commands Quick Reference

## 🎯 Cách sử dụng Debug Debugger

Sau khi mở browser DevTools (F12 → Console):

### 1. **Xem Flow Timeline của một Message**
```javascript
// Copy message ID từ UI hoặc logs, sau đó:
debugger.printFlowTimeline('your-message-id-here')
```

**Output:**
```
📊 Flow Timeline for your-message-id
┌─────────────┬──────┬────────────────────────────────┐
│   phase     │ time │           text                 │
├─────────────┼──────┼────────────────────────────────┤
│ SEND        │  0   │ 📝 USER SENDS MESSAGE          │
│ WEBSOCKET   │  25  │ 📤 SENDING TO WEBSOCKET        │
│ WEBSOCKET   │  30  │ ✅ SENT TO WEBSOCKET           │
│ RECEIVE     │  120 │ 📥 FRONTEND RECEIVES...        │
│ DECRYPT     │  150 │ 🔑 FRONTEND CALLING DECRYPT..  │
│ DISPLAY     │  220 │ 📺 FRONTEND DISPLAYING...      │
└─────────────┴──────┴────────────────────────────────┘
```

### 2. **Xem Metrics (Thời gian mỗi Phase)**
```javascript
debugger.printMetrics('message-id')
```

**Output:**
```
📊 Metrics for message-id
Total Time: 220ms
Total Phases: 6
Avg Phase Time: 36.67ms

┌─────────────┬──────────┬────────────────┐
│   phase     │ duration │ cumulativeTime │
├─────────────┼──────────┼────────────────┤
│ SEND        │ 0ms      │ 0ms            │
│ WEBSOCKET   │ 25ms     │ 25ms           │
│ WEBSOCKET   │ 5ms      │ 30ms           │
│ RECEIVE     │ 90ms     │ 120ms          │
│ DECRYPT     │ 30ms     │ 150ms          │
│ DISPLAY     │ 70ms     │ 220ms          │
└─────────────┴──────────┴────────────────┘
```

### 3. **Xem Tất cả Message Flows**
```javascript
debugger.printAllFlows()
```

### 4. **Xem Status của tất cả Messages**
```javascript
debugger.printAnalysisReport()
```

**Output:**
```
🔍 Message Flow Analysis Report

📊 Summary
Total Messages: 15
Average Flow Time: 185ms
Fastest: 120ms
Slowest: 350ms

📍 Message Status
┌────────────┬────────────────────────────┐
│   status   │       message_ids          │
├────────────┼────────────────────────────┤
│ DISPLAYED  │ [msg1234, msg5678, msg9...]│
│ DECRYPTING │ [msg2222]                  │
│ ERROR      │ []                         │
└────────────┴────────────────────────────┘

⚠️ Bottlenecks
┌───────────┬─────────────────┬──────────┐
│messageId  │     between     │ duration │
├───────────┼─────────────────┼──────────┤
│ msg2222   │ API → DECRYPT   │ 150ms    │
│ msg9999   │ RECEIVE → ...   │ 120ms    │
└───────────┴─────────────────┴──────────┘
```

### 5. **Tìm Message theo Status**
```javascript
debugger.getMessagesByStatus()
// {
//   DISPLAYED: ['msg1234', 'msg5678', ...],
//   DECRYPTING: ['msg2222'],
//   ERROR: [],
//   ...
// }
```

### 6. **Tìm Bottlenecks**
```javascript
debugger.findBottlenecks()
// Trả về list các phase transitions có delay > 100ms
```

### 7. **Get Status của một Message**
```javascript
debugger.getMessageStatus('message-id')
// Returns: 'DISPLAYED', 'DECRYPTING', 'ERROR', 'SENDING', etc.
```

### 8. **Get Flow Metrics cho một Message**
```javascript
debugger.getFlowMetrics('message-id')
// {
//   messageId: 'msg1234',
//   totalTime: 220,
//   phaseCount: 6,
//   avgPhaseTime: 36.67,
//   phaseTimings: [...]
// }
```

---

## 📊 Backend Debug Logs

### Xem Real-time Backend Logs:

```bash
# Terminal 1: Start backend with logging
python main.py

# Terminal 2: Tail logs với grep
tail -f output.log | grep -E "PHASE|ERROR"
```

### Backend Log Format:
```
[🔄 PHASE 6] Backend receives from WebSocket | msg_len=15 | from user abc12345...
[🔐 PHASE 7] Starting encryption with driver | content: Hello world
[✅ PHASE 8] Encryption success | encrypted_len=48
[💾 PHASE 9] Saving to database
[✅ PHASE 10] Database saved | message_id: msg12345...
[📡 PHASE 11] Broadcasting to room members
[🔑 PHASE 15] Backend receives decrypt request
[🔓 PHASE 16] Starting decryption
[✅ PHASE 17] Decryption success
[📤 PHASE 18] Sending decrypt response
```

---

## 🔴 Common Debug Scenarios

### Scenario 1: Message bị duplicate
```javascript
// Check tất cả messages
const statuses = debugger.getMessagesByStatus()
console.log('Messages by status:', statuses)

// Check flow của từng message
debugger.printAllFlows()

// Xem UI: inspect element để check message count
```

### Scenario 2: Message không decrypt
```javascript
// Get metrics của message
debugger.printMetrics('message-id')

// Check toàn bộ flow
debugger.printFlowTimeline('message-id')

// Check error phase
const flow = debugger.messageFlows.get('message-id')
const errorPhase = flow.find(p => p.phase.includes('ERROR'))
console.log('Error:', errorPhase)
```

### Scenario 3: Sender nhìn thấy message của mình duplicate
```javascript
// Check message status
debugger.getMessageStatus('message-id')

// Check nếu có phase thêm temp message rồi real message?
debugger.printFlowTimeline('message-id')

// Look for duplicate temp IDs
const allFlows = Array.from(debugger.messageFlows.keys())
const tempIds = allFlows.filter(id => id.startsWith('temp-'))
console.log('Temp message IDs:', tempIds)
```

### Scenario 4: Performance slow (> 500ms delays)
```javascript
// Xem bottlenecks
const bottlenecks = debugger.findBottlenecks()
console.table(bottlenecks)

// Xem metrics chi tiết
debugger.printAnalysisReport()

// Check phase transitions riêng lẻ
const flow = debugger.messageFlows.get('message-id')
for (let i = 1; i < flow.length; i++) {
  const duration = flow[i].time - flow[i-1].time
  if (duration > 100) {
    console.warn(`Slow: ${flow[i-1].phase} → ${flow[i].phase}: ${duration}ms`)
  }
}
```

---

## 📈 How to Interpret Timing

**Healthy Flow Times:**
- SEND → WEBSOCKET: 20-50ms
- WEBSOCKET → RECEIVE: 30-100ms (depending on network)
- RECEIVE → DECRYPT: 50-150ms (encryption depends on message size)
- DECRYPT → DISPLAY: 50-100ms (UI update)
- **Total: 120-250ms** ✅

**Warning Signs:**
- Any single phase > 200ms ⚠️
- RECEIVE → gaps appear ⚠️
- Multiple phases missing ⚠️
- Error phase present ❌

---

## 🛠️ Exporting Debug Data

```javascript
// Export all flows as JSON
const allFlows = Object.fromEntries(debugger.messageFlows)
JSON.stringify(allFlows, null, 2)

// Copy to clipboard
copy(JSON.stringify(allFlows, null, 2))

// Save to file (in DevTools console)
console.save = function(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'})
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
}
console.save(allFlows, 'message-flows.json')
```

---

## 🎯 Tips for Effective Debugging

1. **Always capture right after transaction** - Don't wait, run commands immediately
2. **Check PHASE numbers sequentially** - Make sure no phases are skipped
3. **Look at timings first** - Large gaps indicate problems
4. **Cross-reference frontend & backend logs** - Match message IDs
5. **Use grep to find errors** - `grep ERROR` on backend logs
6. **Monitor multiple messages** - Single message might work, but many might fail
