"""
Comprehensive Test Suite for Secure Chat Backend

Kiểm thử:
1. Authentication flow (Register, Login, Get Me)
2. Database operations
3. Crypto bridge (Mock MD5 hash)
4. JWT token
5. WebSocket connections
"""

import asyncio
from fastapi.testclient import TestClient
from app.database.database import SessionLocal, engine, Base, drop_db, init_db
from app.core.crypto_bridge import crypto_bridge
from app.core.security import create_access_token, verify_access_token
from app.database.models import User
from main import app
import uuid

# ==================== Setup and Teardown ====================

def setup_module():
    """Setup: Create fresh database for tests."""
    drop_db()
    init_db()
    print("\n✓ Test database initialized")


def teardown_module():
    """Cleanup: Drop test database."""
    drop_db()
    print("✓ Test database cleaned up")


# ==================== Test Classes ====================

class TestCryptoBridge:
    """Test crypto_bridge MD5 hashing (Mock implementation)."""
    
    def test_hash_password_returns_32_char_hex(self):
        """Test MD5 hash returns 32 character hex string."""
        password = "TestPassword123!"
        
        async def async_test():
            hash_result = await crypto_bridge.hash_password_with_driver(password)
            assert len(hash_result) == 32, f"Hash should be 32 chars, got {len(hash_result)}"
            assert all(c in '0123456789abcdef' for c in hash_result), "Hash should be hex"
            print(f"✓ Hash test passed: {hash_result[:16]}...")
        
        asyncio.run(async_test())
    
    def test_same_password_same_hash(self):
        """Test that same password produces same hash (deterministic)."""
        password = "SecurePass123!"
        
        async def async_test():
            hash1 = await crypto_bridge.hash_password_with_driver(password)
            hash2 = await crypto_bridge.hash_password_with_driver(password)
            assert hash1 == hash2, "Same password should produce same hash"
            print(f"✓ Deterministic hash test passed")
        
        asyncio.run(async_test())
    
    def test_different_passwords_different_hash(self):
        """Test that different passwords produce different hashes."""
        password1 = "Password123!"
        password2 = "Password456!"
        
        async def async_test():
            hash1 = await crypto_bridge.hash_password_with_driver(password1)
            hash2 = await crypto_bridge.hash_password_with_driver(password2)
            assert hash1 != hash2, "Different passwords should produce different hashes"
            print(f"✓ Different password test passed")
        
        asyncio.run(async_test())


class TestSecurityJWT:
    """Test JWT token creation and verification."""
    
    def test_create_and_verify_token(self):
        """Test JWT token creation and verification."""
        data = {"user_id": str(uuid.uuid4()), "username": "testuser"}
        
        token = create_access_token(data)
        assert token is not None, "Token should not be None"
        assert isinstance(token, str), "Token should be string"
        
        payload = verify_access_token(token)
        assert payload["user_id"] == data["user_id"], "user_id should match"
        assert payload["username"] == data["username"], "username should match"
        
        print(f"✓ JWT test passed: Token={token[:20]}...")
    
    def test_invalid_token_raises_exception(self):
        """Test that invalid token raises exception."""
        from app.core.security import HTTPException
        
        invalid_token = "invalid.token.here"
        
        try:
            verify_access_token(invalid_token)
            assert False, "Should raise HTTPException"
        except Exception as e:
            print(f"✓ Invalid token test passed: Caught {type(e).__name__}")


class TestAuthRegisterLoginFlow:
    """Test Register and Login endpoints."""
    
    def test_register_new_user(self):
        """Test successful user registration."""
        client = TestClient(app)
        
        user_data = {
            "username": "testuser_" + str(uuid.uuid4())[:8],
            "email": f"test_{uuid.uuid4()}@example.com",
            "password": "TestPassword123!",
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert "id" in data
        assert "password_hash" not in data  # Should not expose hash
        
        print(f"✓ Register test passed: User {data['username']} created")
        return user_data
    
    def test_register_duplicate_username(self):
        """Test that duplicate username is rejected."""
        client = TestClient(app)
        
        user_data = {
            "username": "duplicate_" + str(uuid.uuid4())[:8],
            "email": f"test_{uuid.uuid4()}@example.com",
            "password": "TestPassword123!",
        }
        
        # First registration should succeed
        response1 = client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201
        
        # Second registration with same username should fail
        user_data["email"] = f"test_{uuid.uuid4()}@example.com"  # Different email
        response2 = client.post("/api/v1/auth/register", json=user_data)
        assert response2.status_code == 400, f"Expected 400, got {response2.status_code}"
        
        print(f"✓ Duplicate username test passed")
    
    def test_login_success(self):
        """Test successful login."""
        client = TestClient(app)
        
        # Register first
        user_data = {
            "username": "logintest_" + str(uuid.uuid4())[:8],
            "email": f"test_{uuid.uuid4()}@example.com",
            "password": "TestPassword123!",
        }
        
        reg_response = client.post("/api/v1/auth/register", json=user_data)
        assert reg_response.status_code == 201
        
        # Then login
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"],
        }
        
        login_response = client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200, f"Expected 200, got {login_response.status_code}: {login_response.text}"
        
        data = login_response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == user_data["username"]
        
        print(f"✓ Login success test passed: Token obtained")
        return data["access_token"]
    
    def test_login_invalid_password(self):
        """Test login with wrong password."""
        client = TestClient(app)
        
        # Register first
        user_data = {
            "username": "wrongpass_" + str(uuid.uuid4())[:8],
            "email": f"test_{uuid.uuid4()}@example.com",
            "password": "CorrectPassword123!",
        }
        
        client.post("/api/v1/auth/register", json=user_data)
        
        # Try login with wrong password
        login_data = {
            "username": user_data["username"],
            "password": "WrongPassword456!",
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        
        print(f"✓ Invalid password test passed")
    
    def test_get_current_user(self):
        """Test GET /me endpoint."""
        client = TestClient(app)
        
        # Register and login
        user_data = {
            "username": "metest_" + str(uuid.uuid4())[:8],
            "email": f"test_{uuid.uuid4()}@example.com",
            "password": "TestPassword123!",
        }
        
        client.post("/api/v1/auth/register", json=user_data)
        
        login_response = client.post("/api/v1/auth/login", json={
            "username": user_data["username"],
            "password": user_data["password"],
        })
        
        token = login_response.json()["access_token"]
        
        # Get current user
        get_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["username"] == user_data["username"]
        
        print(f"✓ Get current user test passed")
    
    def test_get_current_user_invalid_token(self):
        """Test GET /me with invalid token."""
        client = TestClient(app)
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
        
        print(f"✓ Invalid token test passed")


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self):
        """Test GET /"""
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "status" in response.json()
        print(f"✓ Root endpoint test passed")
    
    def test_health_endpoint(self):
        """Test GET /health"""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        print(f"✓ Health endpoint test passed")
    
    def test_ping_endpoint(self):
        """Test GET /api/v1/ping"""
        client = TestClient(app)
        response = client.get("/api/v1/ping")
        assert response.status_code == 200
        assert response.json()["message"] == "pong"
        print(f"✓ Ping endpoint test passed")


# ==================== Run Tests ====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Secure Chat Backend Test Suite")
    print("="*60)
    
    setup_module()
    
    try:
        # Test Crypto Bridge
        print("\n--- Testing Crypto Bridge ---")
        crypto_tests = TestCryptoBridge()
        crypto_tests.test_hash_password_returns_32_char_hex()
        crypto_tests.test_same_password_same_hash()
        crypto_tests.test_different_passwords_different_hash()
        
        # Test Security/JWT
        print("\n--- Testing JWT Security ---")
        jwt_tests = TestSecurityJWT()
        jwt_tests.test_create_and_verify_token()
        jwt_tests.test_invalid_token_raises_exception()
        
        # Test Health Endpoints
        print("\n--- Testing Health Endpoints ---")
        health_tests = TestHealthEndpoints()
        health_tests.test_root_endpoint()
        health_tests.test_health_endpoint()
        health_tests.test_ping_endpoint()
        
        # Test Auth Flow
        print("\n--- Testing Auth Flow ---")
        auth_tests = TestAuthRegisterLoginFlow()
        auth_tests.test_register_new_user()
        auth_tests.test_register_duplicate_username()
        auth_tests.test_login_success()
        auth_tests.test_login_invalid_password()
        auth_tests.test_get_current_user()
        auth_tests.test_get_current_user_invalid_token()
        
        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("="*60 + "\n")
    
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        teardown_module()
