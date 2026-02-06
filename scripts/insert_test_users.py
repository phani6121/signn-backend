"""
Script to insert test users into Firestore database.
Run this from the backend directory:
python scripts/insert_test_users.py
"""

import sys
import os
import json
import hashlib
from datetime import datetime

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.firebase import firestore_manager


def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def insert_test_users():
    """Load test users from JSON and insert into Firestore"""
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_users_path = os.path.join(script_dir, '..', 'test-users.json')
    
    # Load test users from JSON file
    with open(test_users_path, 'r') as f:
        test_users = json.load(f)
    
    print(f"Loading {len(test_users)} test users...\n")
    
    inserted_count = 0
    failed_count = 0
    
    for user_data in test_users:
        try:
            username = user_data.get('username')
            password = user_data.get('password')
            
            # Hash the password
            hashed_password = hash_password(password)
            
            # Prepare user document
            user_doc = {
                'username': username,
                'password_hash': hashed_password,  # Store hashed password
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'phone': user_data.get('phone'),
                'role': user_data.get('role', 'driver'),
                'status': 'active',
                'last_login': None,  # Will be updated on first login
                'login_count': 0,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }
            
            # Create document using username as ID
            firestore_manager.create_document('users', username, user_doc)
            
            print(f"OK Created user: {username}")
            inserted_count += 1
            
        except Exception as e:
            print(f"FAIL Failed to create user {username}: {e}")
            failed_count += 1
    
    print(f"\n{'='*50}")
    print(f"Insertion Complete!")
    print(f"Successfully inserted: {inserted_count}/{len(test_users)}")
    if failed_count > 0:
        print(f"Failed: {failed_count}")
    print(f"{'='*50}\n")
    
    # Print login credentials
    print("Test User Credentials:")
    print("="*50)
    for user_data in test_users:
        print(f"Username: {user_data['username']:15} | Password: {user_data['password']}")
    print("="*50)


if __name__ == "__main__":
    try:
        insert_test_users()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure you're running this script from the backend directory.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
