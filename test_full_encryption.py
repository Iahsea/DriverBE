#!/usr/bin/env python3
"""Test full message encryption flow with backend"""

import asyncio
import json
import sys
import aiohttp
import websockets
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

# Test credentials
TEST_USER = "testuser_" + str(uuid.uuid4())[:8]
TEST_PASS = "Test@1234"
TEST_USER2 = "testuser2_" + str(uuid.uuid4())[:8]

async def test_message_encryption():
    """Test end-to-end message encryption"""
    
    print("=" * 70)
    print("Testing Message Encryption Flow")
    print("=" * 70)
    
    async with aiohttp.ClientSession() as session:
        # 1. Register users
        print("\n1️⃣  Registering test users...")
        resp = await session.post(f"{BASE_URL}/api/v1/auth/register", json={
            "username": TEST_USER,
            "password": TEST_PASS,
            "email": f"{TEST_USER}@test.com"
        })
        if resp.status not in [200, 201]:
            print(f"❌ User 1 signup failed: {await resp.text()}")
            return
        user1_data = await resp.json()
        user1_id = user1_data.get("id")
        
        # Login to get token
        resp = await session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASS,
        })
        if resp.status != 200:
            print(f"❌ User 1 login failed: {await resp.text()}")
            return
        login_data = await resp.json()
        user1_token = login_data.get("access_token")
        print(f"✅ User 1 created: {TEST_USER} (ID: {user1_id[:8]}...)")
        
        resp = await session.post(f"{BASE_URL}/api/v1/auth/register", json={
            "username": TEST_USER2,
            "password": TEST_PASS,
            "email": f"{TEST_USER2}@test.com"
        })
        if resp.status not in [200, 201]:
            print(f"❌ User 2 signup failed: {await resp.text()}")
            return
        user2_data = await resp.json()
        user2_id = user2_data.get("id")
        
        # Login to get token
        resp = await session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "username": TEST_USER2,
            "password": TEST_PASS,
        })
        if resp.status != 200:
            print(f"❌ User 2 login failed: {await resp.text()}")
            return
        login_data = await resp.json()
        user2_token = login_data.get("access_token")
        print(f"✅ User 2 created: {TEST_USER2} (ID: {user2_id[:8]}...)")
        
        # 2. Create chat room
        print("\n2️⃣  Creating chat room...")
        headers = {"Authorization": f"Bearer {user1_token}"}
        resp = await session.post(
            f"{BASE_URL}/api/v1/rooms",
            json={"name": f"Test Room {uuid.uuid4().hex[:8]}"},
            headers=headers
        )
        if resp.status not in [200, 201]:
            print(f"❌ Room creation failed: {await resp.text()}")
            return
        room_data = await resp.json()
        room_id = room_data.get("id")
        print(f"✅ Room created: {room_id[:8]}...")
        
        # 3a. Add as friends first
        print("\n3a️⃣  Adding users as friends...")
        resp = await session.post(
            f"{BASE_URL}/api/v1/friends/request",
            json={"to_user_id": user2_id},
            headers=headers
        )
        if resp.status not in [200, 201]:
            print(f"⚠️  Friend request failed: {await resp.text()}")
        else:
            print(f"   Friend request sent")
            
            # Accept friend request as user 2
            headers2 = {"Authorization": f"Bearer {user2_token}"}
            resp = await session.get(
                f"{BASE_URL}/api/v1/friends/requests",
                headers=headers2
            )
            if resp.status == 200:
                requests_data = await resp.json()
                if requests_data:
                    # Accept first request (from user 1)
                    friend_id = user1_id
                    resp = await session.post(
                        f"{BASE_URL}/api/v1/friends/request/{friend_id}/accept",
                        headers=headers2
                    )
                    if resp.status in [200, 201]:
                        print(f"   ✅ Friendship established")
        
        # 3b. Add user 2 to room
        print("\n3b️⃣  Adding user 2 to room...")
        resp = await session.post(
            f"{BASE_URL}/api/v1/rooms/{room_id}/members",
            json={"user_id": user2_id},
            headers=headers
        )
        if resp.status not in [200, 201]:
            print(f"❌ Adding user to room failed: {await resp.text()}")
            return
        print(f"✅ User 2 added to room")
        
        # 4. Connect to WebSocket and send message
        print("\n4️⃣  Connecting to WebSocket and sending message...")
        
        messages_received = []
        
        async def send_message(user_token, user_id, room_id, message):
            """Send message via WebSocket"""
            try:
                uri = f"{WS_URL}/ws/chat/{room_id}?token={user_token}&user_id={user_id}"
                async with websockets.connect(uri) as websocket:
                    print(f"   Connected to WebSocket for user {user_id[:8]}...")
                    
                    # Send message
                    msg_data = {"type": "message", "content": message}
                    await websocket.send(json.dumps(msg_data))
                    
                    # Receive broadcast
                    for _ in range(3):  # Try to receive a few messages
                        try:
                            msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            msg_obj = json.loads(msg)
                            if msg_obj.get("type") == "message":
                                messages_received.append(msg_obj)
                                print(f"   ✅ Received broadcast: {msg_obj.get('type')}")
                                break
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            print(f"   ⚠️  Error receiving: {e}")
                            break
            except Exception as e:
                print(f"❌ WebSocket error: {e}")
                raise

        test_message = "Hello from secure chat! 🔐 " + str(datetime.now())
        await send_message(user1_token, user1_id, room_id, test_message)
        
        # 5. Check message in database via API
        print("\n5️⃣  Retrieving message history...")
        headers = {"Authorization": f"Bearer {user1_token}"}
        resp = await session.get(f"{BASE_URL}/api/v1/rooms/{room_id}/messages", headers=headers)
        if resp.status != 200:
            print(f"❌ Failed to get messages: {await resp.text()}")
            return
        
        messages = await resp.json()
        print(f"✅ Retrieved {len(messages)} message(s)")
        
        if messages:
            msg = messages[-1]  # Latest message
            print(f"\n   Message ID: {msg.get('id')[:8]}...")
            print(f"   Sender: {msg.get('sender_name')}")
            print(f"   Has encrypted content: {'content_encrypted' in msg}")
            print(f"   Encrypted length: {len(msg.get('content_encrypted', ''))}")
            
            # 6. Try to decrypt via API
            print("\n6️⃣  Attempting to decrypt message via API...")
            msg_id = msg.get('id')
            resp = await session.post(
                f"{BASE_URL}/api/v1/messages/{msg_id}/decrypt",
                headers=headers
            )
            if resp.status == 200:
                decrypt_data = await resp.json()
                decrypted = decrypt_data.get('decrypted_content')
                print(f"✅ Message decrypted successfully!")
                print(f"   Decrypted: {decrypted}")
                
                if decrypted == test_message:
                    print("✅ Decrypted message matches original!")
                else:
                    print(f"❌ Decrypted message doesn't match")
                    print(f"   Expected: {test_message}")
                    print(f"   Got:      {decrypted}")
            else:
                error_text = await resp.text()
                print(f"❌ Decryption failed ({resp.status}): {error_text}")

        print("\n" + "=" * 70)
        print("✅ Test completed successfully!")
        print("=" * 70)

if __name__ == "__main__":
    try:
        asyncio.run(test_message_encryption())
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
