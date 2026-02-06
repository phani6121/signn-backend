# Test Users Setup & User-Specific Login ✅

## Overview
You now have 10 test users in your Firestore database. When users login, ONLY their specific record is updated - not all users in the database.

## Test Users

All test users have the same password: **123456**

| Username  | Email                    | Name          |
|-----------|--------------------------|---------------|
| testuser1 | testuser1@example.com    | Test User 1   |
| testuser2 | testuser2@example.com    | Test User 2   |
| testuser3 | testuser3@example.com    | Test User 3   |
| testuser4 | testuser4@example.com    | Test User 4   |
| testuser5 | testuser5@example.com    | Test User 5   |
| testuser6 | testuser6@example.com    | Test User 6   |
| testuser7 | testuser7@example.com    | Test User 7   |
| testuser8 | testuser8@example.com    | Test User 8   |
| testuser9 | testuser9@example.com    | Test User 9   |
| testuser10| testuser10@example.com   | Test User 10  |

## Files Created

### 1. [backend/test-users.json](test-users.json)
- JSON file with all 10 test users
- Contains: username, password, email, name, phone, role

### 2. [backend/scripts/insert_test_users.py](scripts/insert_test_users.py)
- Script to insert test users into Firestore
- Hashes passwords before storing
- Run with: `python scripts/insert_test_users.py`

### 3. [backend/scripts/test_login_isolation.py](scripts/test_login_isolation.py)
- Verifies that only specific users are updated on login
- Shows that non-logged-in users remain unchanged

## Key Changes

### 1. **Updated Authentication Schema** (`app/schemas/auth.py`)
- Accepts both `username` and `email` for login
- Returns detailed user info after login
- Fields: `token`, `user_id`, `username`, `email`, `name`, `role`, `login_count`, `last_login`

### 2. **Enhanced Auth Service** (`app/services/authservice.py`)
- **Password Hashing**: Uses SHA-256 to store hashes
- **Per-User Updates**: 
  - Uses `firestore_manager.update_document()` with specific user ID
  - ONLY updates the logged-in user's record
  - Non-logged-in users are NOT affected
- **Verification**: Checks username/email exists and password is correct
- **Logging**: Tracks login attempts and errors

### 3. **Updated Auth Endpoint** (`app/api/v1/auth.py`)
- Better error handling with HTTP 401 for auth failures
- Accepts `username` or `email` in login request
- Returns complete user details

## How Login Works (Per-User Updates)

### Before (❌ Wrong - Updated All Users)
```python
# Old way - would update ALL users
firestore_manager.create_document('users', 'all_users', data)
```

### After (✅ Correct - Updates Only Specific User)
```python
# New way - updates ONLY the specific user
username = "testuser1"
login_update = {
    'last_login': datetime.utcnow(),
    'login_count': current_count + 1,
    'token': generated_token,
}

# This updates ONLY testuser1's document
firestore_manager.update_document('users', username, login_update)
```

## Testing

### Test Login via API

**Using cURL:**
```bash
# Login with testuser1
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser1",
    "password": "123456"
  }'
```

**Expected Response:**
```json
{
  "token": "token_abc123def456...",
  "token_type": "bearer",
  "user_id": "testuser1",
  "username": "testuser1",
  "email": "testuser1@example.com",
  "name": "Test User 1",
  "role": "driver",
  "login_count": 1,
  "last_login": "2026-02-04T10:30:00"
}
```

### Test Invalid Login
```bash
# Wrong password
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser1",
    "password": "wrongpassword"
  }'
```

**Expected Response:**
```json
{
  "detail": "Invalid username or password"
}
```
(HTTP 401 Unauthorized)

### Verify User Isolation

Run the test script:
```bash
python scripts/test_login_isolation.py
```

Output will show:
- Users who logged in have `login_count > 0` and `last_login` set
- Users who never logged in have `login_count = 0` and `last_login = None`

## Database Schema

Each user document has:

```json
{
  "username": "testuser1",
  "password_hash": "sha256_hash_here",
  "email": "testuser1@example.com",
  "name": "Test User 1",
  "phone": "+1234567891",
  "role": "driver",
  "status": "active",
  "last_login": "2026-02-04T07:29:29.991333Z",
  "login_count": 1,
  "token": "token_xyz123abc...",
  "created_at": "2026-02-04T07:20:15.123456Z",
  "updated_at": "2026-02-04T07:29:29.991333Z"
}
```

## Security Features

✅ **Password Hashing**: Passwords are hashed with SHA-256 before storage
✅ **User Isolation**: Each login only updates that specific user
✅ **Error Logging**: Failed attempts are logged for debugging
✅ **Validation**: Username/email and password are validated
✅ **Token Generation**: Unique tokens generated per login

## Common Issues

### Issue: "User not found"
- Check username/email spelling
- Verify user was inserted with `python scripts/insert_test_users.py`

### Issue: "Invalid username or password"
- Could be either:
  - Username doesn't exist
  - Password is wrong (default is `123456`)
- Check user in Firestore console

### Issue: Other users being updated
- This should NOT happen anymore!
- New system uses per-user document updates
- Verify you're using the updated auth service

## Quick Start

1. **Insert test users** (if not done):
   ```bash
   python scripts/insert_test_users.py
   ```

2. **Start backend server**:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

3. **Test login**:
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser1", "password": "123456"}'
   ```

4. **Verify isolation**:
   ```bash
   python scripts/test_login_isolation.py
   ```

## Next Steps

- Integrate the login endpoint in your frontend
- Add JWT token validation for protected endpoints
- Create logout endpoint that clears user session
- Add user profile update endpoint (only for logged-in user)
