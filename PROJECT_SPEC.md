# AI Chat Project Template: Secure Socket Chat with Kernel-Mode Crypto

## 1. Purpose and Scope
Xây dựng hệ thống Chat bảo mật đa tầng, kết hợp giữa ứng dụng web hiện đại và bảo mật cấp thấp (Kernel-level):
* **Frontend:** Sử dụng **ReactJS** (Hooks, Context API/Redux) để xây dựng giao diện người dùng.
* **Backend:** Sử dụng **Python FastAPI** làm server điều phối, quản lý kết nối WebSocket và giao tiếp với Driver.
* **Kernel Security:** Mọi hoạt động mã hóa **AES** và băm **MD5** phải thực hiện trong **Kernel Driver** (Windows KMDF hoặc Linux LKM) thông qua cơ chế IOCTL.
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
│   │   ├── api/              # v1 endpoints (Auth, Users, Rooms)
│   │   ├── schemas/          # Pydantic models (DTOs)
│   │   └── websocket/        # connection_manager.py
│   ├── database/             # PostgreSQL models (SQLAlchemy)
│   ├── main.py
│   └── requirements.txt
├── kernel-module/            # C Source: Linux Kernel Driver
│   ├── crypto_driver.c       # AES & MD5 implementation
│   ├── crypto_driver.h       # IOCTL commands definitions
│   └── Makefile
└── windows-driver/           # Windows KMDF: Driver cho môi trường test

---

## 3. Guidelines for User Input
Để nhận được hỗ trợ chính xác nhất, người dùng cần cung cấp ngữ cảnh rõ ràng:
* **Phạm vi:** Nêu rõ đang yêu cầu code cho **React (Frontend)**, **FastAPI (Backend)** hay **C (Driver)**.
* **Môi trường:** Xác nhận đang code cho **Windows** (Winsock/IOCTL) hay **Linux** (POSIX/LKM).
* **Tương tác:** Hỏi về cách kết nối giữa các tầng, ví dụ: *"Cách gọi hàm C từ Python FastAPI để mã hóa tin nhắn"*.

---

## 4. Conversation Scenarios

### Scenario: Backend Development (FastAPI)
* **User:** "Tạo một WebSocket endpoint trong FastAPI để nhận tin nhắn và đẩy xuống Driver mã hóa."
* **AI:** "Sử dụng `fastapi.WebSocket`. Sau khi nhận bản tin, gọi instance của `CryptoBridge` để lấy bản mã AES từ Driver trước khi broadcast tới các client khác..."

### Scenario: Frontend Development (React)
* **User:** "Viết một custom hook `useSocket` để quản lý kết nối và nhận tin nhắn thời gian thực."
* **AI:** "Sử dụng `useEffect` để khởi tạo `new WebSocket()`. Hook này sẽ trả về trạng thái kết nối và danh sách tin nhắn..."

---

## 5. Instructions for the AI & User
* **AI:** Phải nhớ Backend dùng **Python/FastAPI** và Frontend dùng **React**. Ưu tiên viết code sạch, sử dụng `async/await` cho Backend và Functional Components/Hooks cho Frontend.
* **User:** Đảm bảo cài đặt đầy đủ môi trường (Python 3.10+, Node.js, C++ Build Tools) và chạy Terminal với quyền **Admin** khi test Driver trên Windows.

---

## 6. Fallback & Troubleshooting
* **Mocking:** Nếu chưa có Driver, AI sẽ cung cấp mã giả lập (Mock) trong `crypto_bridge.py` bằng thư viện `cryptography` của Python để test luồng Socket.
* **Error Handling:** Luôn xử lý lỗi mất kết nối WebSocket trên React và lỗi Timeout khi gọi xuống Driver từ FastAPI.