#!/usr/bin/env python3
"""
Script to create admin users in the 'users' collection
"""

import os
import sys
from datetime import datetime
from bson import ObjectId
from passlib.hash import bcrypt
from pymongo import MongoClient

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def create_admin_users():
    """Create admin users in the users collection"""
    
    try:
        # Get database connection details from environment variables
        db_username = os.getenv('DB1_USERNAME', '')
        db_password = os.getenv('DB1_PASSWORD', '')
        db_host = os.getenv('DB1_HOST', 'localhost')
        db_auth_source = os.getenv('DB1_AUTH_SOURCE', 'admin')
        
        print(db_username, db_password, db_host, db_auth_source)

        # # Create MongoDB connection string
        # if db_username and db_password:
        #     connection_string = f"mongodb://{db_username}:{db_password}@{db_host}/?authSource={db_auth_source}"
        # else:
        #     connection_string = f"mongodb://{db_host}/"

        # print(connection_string)

        connection_string = "mongodb+srv://kunakbhatia477:OnaNkm9u1uFVaOyD@hrms.5s00j.mongodb.net/?authSource=admin"
        
        # Connect to MongoDB
        client = MongoClient(connection_string)
        db = client['hrms_master']
        users_collection = db['users']

        print(db.list_collection_names())
        
        # Check if users collection exists, if not create it
        if 'users' not in db.list_collection_names():
            print("Creating 'users' collection...")
        
        # Sample admin users
        admin_users = [
            {
                "_id": ObjectId(),
                "email": "admin@hrms.com",
                "password": bcrypt.hash("admin123"),
                "full_name": "System Administrator",
                "role": "Admin",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "_id": ObjectId(),
                "email": "hr@hrms.com", 
                "password": bcrypt.hash("hr123"),
                "full_name": "HR Manager",
                "role": "Admin",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        # Insert admin users
        for user in admin_users:
            # Check if user already exists
            existing_user = users_collection.find_one({"email": user["email"]})
            if existing_user:
                print(f"User {user['email']} already exists, skipping...")
            else:
                result = users_collection.insert_one(user)
                print(f"Created admin user: {user['email']} with ID: {result.inserted_id}")
        
        print("\nAdmin users created successfully!")
        print("Default credentials:")
        print("1. admin@hrms.com / admin123")
        print("2. hr@hrms.com / hr123")
        
        # Close the connection
        client.close()
        
    except Exception as e:
        print(f"Error creating admin users: {e}")
        print("Make sure MongoDB is running and accessible")
        print("Also ensure your .env file has the correct database credentials:")
        print("- DB1_USERNAME")
        print("- DB1_PASSWORD") 
        print("- DB1_HOST")
        print("- DB1_AUTH_SOURCE")
        sys.exit(1)

if __name__ == "__main__":
    create_admin_users()
