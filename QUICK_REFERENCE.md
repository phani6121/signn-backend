# Quick Reference - Test Users & Login

## Test User Credentials

```
Username: testuser1-testuser10
Password: 123456 (all users)
```

## Login API Endpoint

**URL:** `POST http://localhost:8000/api/auth/login`

**Request:**
```json
{
  "username": "testuser1",
  "password": "123456"
}
```

**Response:**
```json
{
  "token": "token_abc123...",
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

## Important: Per-User Updates

✅ **ONLY the logged-in user's record is updated**
- `last_login`: Set to current time
- `login_count`: Incremented by 1
- `token`: New unique token

✅ **Other users are NOT affected**
- Their `login_count` stays the same
- Their `last_login` stays the same
- Database has no interference between users

## Scripts

### Insert Test Users
```bash
python scripts/insert_test_users.py
```

### Verify User Isolation
```bash
python scripts/test_login_isolation.py
```

## Database Check

To verify a user's login data:
```bash
python -c "
from app.core.firebase import firestore_manager
user = firestore_manager.get_document('users', 'testuser1')
print('Login Count:', user.get('login_count'))
print('Last Login:', user.get('last_login'))
"
```

## Error Responses

### Invalid Password
```json
{
  "detail": "Invalid username or password"
}
```
HTTP Status: **401 Unauthorized**

### User Not Found
```json
{
  "detail": "Invalid username or password"
}
```
HTTP Status: **401 Unauthorized**

## Login Flow

1. Client sends username + password
2. Server finds user by username
3. Server verifies password hash
4. Server generates new token
5. **Server updates ONLY that user's document** ✓
6. Server returns user info + token

## All Test Users

| # | Username  | Email |
|---|-----------|-------|
| 1 | testuser1 | testuser1@example.com |
| 2 | testuser2 | testuser2@example.com |
| 3 | testuser3 | testuser3@example.com |
| 4 | testuser4 | testuser4@example.com |
| 5 | testuser5 | testuser5@example.com |
| 6 | testuser6 | testuser6@example.com |
| 7 | testuser7 | testuser7@example.com |
| 8 | testuser8 | testuser8@example.com |
| 9 | testuser9 | testuser9@example.com |
| 10 | testuser10 | testuser10@example.com |

All have password: **123456**

---

✅ **Ready to test!** Login with any of the test users.
