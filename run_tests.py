#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend Test Suite - Simple Version (ASCII only)
"""

import asyncio
import sys
from fastapi.testclient import TestClient
from app.database.database import SessionLocal, engine, Base, drop_db, init_db
from app.core.crypto_bridge import crypto_bridge
from app.core.security import create_access_token, verify_access_token
from app.database.models import User
from main import app
import uuid

def run_all_tests():
    """Run all backend tests"""
    print("\n" + "="*60)
    print("SECURE CHAT BACKEND TEST SUITE")
    print("="*60)
    
    # Setup
    drop_db()
    init_db()
    print("\n[SETUP] Database initialized")
    
    try:
        # Test 1: Crypto bridge
        print("\n--- TEST 1: Crypto Bridge (MD5 Hash) ---")
        
        async def crypto_test():
            hash1 = await crypto_bridge.hash_password_with_driver("TestPass123")
            assert len(hash1) == 32, "Hash should be 32 chars"
            assert all(c in '0123456789abcdef' for c in hash1), "Hash should be hex"
            
            hash2 = await crypto_bridge.hash_password_with_driver("TestPass123")
            assert hash1 == hash2, "Same password should produce same hash"
            
            hash3 = await crypto_bridge.hash_password_with_driver("DifferentPass456")
            assert hash1 != hash3, "Different passwords should produce different hashes"
        
        asyncio.run(crypto_test())
        print("[PASS] Crypto bridge: All hash tests passed")
        
        # Test 2: JWT Security
        print("\n--- TEST 2: JWT Token ---")
        
        data = {"user_id": str(uuid.uuid4()), "username": "testuser"}
        token = create_access_token(data)
        payload = verify_access_token(token)
        assert payload["user_id"] == data["user_id"]
        assert payload["username"] == data["username"]
        
        print("[PASS] JWT: Token creation and verification successful")
        
        # Test 3: Health endpoints
        print("\n--- TEST 3: Health Endpoints ---")
        
        client = TestClient(app)
        
        resp = client.get("/")
        assert resp.status_code == 200
        assert "status" in resp.json()
        
        resp = client.get("/health")
        assert resp.status_code == 200
        
        resp = client.get("/api/v1/ping")
        assert resp.status_code == 200
        assert resp.json()["message"] == "pong"
        
        print("[PASS] Health endpoints: All endpoints responding")
        
        # Test 4: Register
        print("\n--- TEST 4: User Registration ---")
        
        user_data = {
            "username": "testuser_" + str(uuid.uuid4())[:8],
            "email": f"test_{uuid.uuid4()}@example.com",
            "password": "TestPassword123!",
        }
        
        resp = client.post("/api/v1/auth/register", json=user_data)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
        data = resp.json()
        assert data["username"] == user_data["username"]
        assert "password_hash" not in data
        
        print(f"[PASS] Registration: User {user_data['username']} created")
        
        # Test 5: Duplicate username check
        print("\n--- TEST 5: Duplicate Username Prevention ---")
        
        user_data["email"] = f"test_{uuid.uuid4()}@example.com"
        resp = client.post("/api/v1/auth/register", json=user_data)
        assert resp.status_code == 400, "Should reject duplicate username"
        
        print("[PASS] Duplicate check: Correctly rejected duplicate")
        
        # Test 6: Login
        print("\n--- TEST 6: User Login ---")
        
        login_data = {
            "username": user_data["username"],
            "password": "TestPassword123!",
        }
        
        resp = client.post("/api/v1/auth/login", json={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "access_token" in data
        token = data["access_token"]
        
        print("[PASS] Login: Token obtained successfully")
        
        # Test 7: Invalid password
        print("\n--- TEST 7: Invalid Password Handling ---")
        
        resp = client.post("/api/v1/auth/login", json={
            "username": user_data["username"],
            "password": "WrongPassword456!"
        })
        assert resp.status_code == 401
        
        print("[PASS] Invalid password: Correctly rejected")
        
        # Test 8: Get current user
        print("\n--- TEST 8: Get Current User (JWT) ---")
        
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["username"] == user_data["username"]
        
        print("[PASS] Get current user: User info retrieved successfully")
        
        # Test 9: Invalid token
        print("\n--- TEST 9: Invalid Token Handling ---")
        
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert resp.status_code == 401
        
        print("[PASS] Invalid token: Correctly rejected")
        
        # Summary
        print("\n" + "="*60)
        print("[SUCCESS] ALL TESTS PASSED!")
        print("="*60)
        print("\nTest Summary:")
        print("  [PASS] Crypto Bridge")
        print("  [PASS] JWT Security")
        print("  [PASS] Health Endpoints")
        print("  [PASS] User Registration")
        print("  [PASS] Duplicate Prevention")
        print("  [PASS] User Login")
        print("  [PASS] Invalid Password")
        print("  [PASS] Get Current User")
        print("  [PASS] Invalid Token")
        print("\n")
        
        return 0
    
    except AssertionError as e:
        print(f"\n[FAIL] Test assertion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    except Exception as e:
        print(f"\n[ERROR] Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        drop_db()
        print("[CLEANUP] Test database dropped")

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
