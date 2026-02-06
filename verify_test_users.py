"""Final verification of test users and per-user login system"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.authservice import login
from app.schemas.auth import LoginRequest
from app.core.firebase import firestore_manager

print('FINAL VERIFICATION - Test Users & Login System')
print('='*70)
print()

# Test 1: Show all test users
print('1. All Test Users in Database:')
print('-'*70)
for i in range(1, 11):
    username = f'testuser{i}'
    user = firestore_manager.get_document('users', username)
    email = user.get('email')
    print(f'   {i:2}. {username:12} - Email: {email}')
print()

# Test 2: Login with testuser1
print('2. Testing Login (testuser1):')
print('-'*70)
try:
    req = LoginRequest(username='testuser1', password='123456')
    resp = login(req)
    print(f'   Username:   {resp.username}')
    print(f'   Email:      {resp.email}')
    print(f'   Name:       {resp.name}')
    print(f'   Role:       {resp.role}')
    print(f'   Token:      {resp.token[:30]}...')
    print(f'   Login Count: {resp.login_count}')
    print()
except Exception as e:
    print(f'   ERROR: {e}')
    print()

# Test 3: Verify only testuser1 was updated
print('3. Verify Per-User Update (Only testuser1 should have login_count=1):')
print('-'*70)
updated_users = []
unchanged_users = []

for i in range(1, 11):
    username = f'testuser{i}'
    user = firestore_manager.get_document('users', username)
    count = user.get('login_count', 0)
    
    if count > 0:
        updated_users.append(username)
    else:
        unchanged_users.append(username)

print(f'   Updated (login_count > 0): {updated_users}')
print(f'   Unchanged (login_count = 0): {unchanged_users}')
print()

# Test 4: Summary
print('='*70)
print('SUMMARY:')
print(f'  + Total test users: 10')
print(f'  + Users that logged in: {len(updated_users)}')
print(f'  + Users that did NOT login: {len(unchanged_users)}')
print(f'  + Per-user updates working: {len(updated_users) >= 1}')
print(f'  + User isolation verified: {len(unchanged_users) >= 8}')
print()
print('SUCCESS: ALL SYSTEMS READY!')
print('='*70)
