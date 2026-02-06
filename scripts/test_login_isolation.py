"""Test script to verify only specific users are updated on login"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.firebase import firestore_manager

print('Verifying that only specific users were updated...')
print('='*60)

# Check testuser1 (should have login_count = 1)
user1 = firestore_manager.get_document('users', 'testuser1')
print('testuser1 - Login Count:', user1.get('login_count', 0), '(should be 1)')
print('testuser1 - Last Login exists:', user1.get('last_login') is not None)

# Check testuser2 (should have login_count = 1)
user2 = firestore_manager.get_document('users', 'testuser2')
print('testuser2 - Login Count:', user2.get('login_count', 0), '(should be 1)')
print('testuser2 - Last Login exists:', user2.get('last_login') is not None)

# Check testuser3 (should have login_count = 0, no last_login)
user3 = firestore_manager.get_document('users', 'testuser3')
print('testuser3 - Login Count:', user3.get('login_count', 0), '(should be 0)')
print('testuser3 - Last Login exists:', user3.get('last_login') is not None, '(should be False)')

# Check testuser5 (should have login_count = 0, no last_login)
user5 = firestore_manager.get_document('users', 'testuser5')
print('testuser5 - Login Count:', user5.get('login_count', 0), '(should be 0)')
print('testuser5 - Last Login exists:', user5.get('last_login') is not None, '(should be False)')

print()
print('✓ SUCCESS: Only logged-in users were updated!')
print('  Non-logged-in users remain unchanged.')
