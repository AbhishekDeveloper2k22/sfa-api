from pymongo import MongoClient
from datetime import datetime
import bcrypt

# MongoDB se connect (apna URI dalna)
# client = MongoClient("mongodb://localhost:27017/")
client = MongoClient("mongodb+srv://kunakbhatia477:OnaNkm9u1uFVaOyD@hrms.5s00j.mongodb.net/?authSource=admin")

# Database select karo
db = client["trust_rewards"]

# Password ko hash karna (bcrypt use karke)
plain_password = "Demo@12345"
hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())

# Admin user document
admin_user = {
    "username": "demo@1place.com",
    "email": "demo@1placetech.com",
    "hash_password": hashed_password.decode('utf-8'),  # hashed password
    "role": "admin",
    "status": "active",
    "createdAt": datetime.utcnow()
}

# Insert into users collection
result = db.users.insert_one(admin_user)

print("Inserted Admin ID:", result.inserted_id)
