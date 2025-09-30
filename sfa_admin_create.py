# create_user_type4.py
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

try:
    from passlib.hash import bcrypt
    def hash_password(p): return bcrypt.hash(p)
except ImportError:
    import bcrypt as pybcrypt
    def hash_password(p): return pybcrypt.hashpw(p.encode("utf-8"), pybcrypt.gensalt()).decode("utf-8")

from sfa.database import client1

db = client1["field_squad"]
users = db["users"]

def create_or_update_user_type4(
    email: str,
    password_plain: str,
    name: str = "Admin User",
    mobile: str = "9999999999",
    employee_code: str = "EMP-ADMIN-001",
):
    hashed = hash_password(password_plain)
    now_iso = datetime.utcnow().isoformat()

    set_doc = {
        "email": email,
        "mobile": mobile,
        "name": name,
        "employee_code": employee_code,
        "user_type": 4,                    # <- important
        "designation": "Admin",
        "department": "Admin",
        "employment_status": "Active",
        "date_of_joining": datetime.utcnow().strftime("%Y-%m-%d"),
        "password": hashed,                 # keep for auth compatibility
        "hash_password": hashed,            # explicit hashed password copy
        "plain_password": password_plain,   # store plain password as requested
        "last_login": None,
        "updated_at": now_iso,
    }

    # Upsert by email or mobile
    result = users.update_one(
        {"$or": [{"email": email}, {"mobile": mobile}]},
        {"$set": set_doc, "$setOnInsert": {"created_at": now_iso}},
        upsert=True,
    )

    if result.upserted_id:
        print(f"Created user_type 4 with _id: {result.upserted_id}")
    else:
        print("Updated existing user_type 4 (matched by email/mobile)")

if __name__ == "__main__":
    # TODO: Replace with your values
    create_or_update_user_type4(
        email="admin@1place.com",
        password_plain="Admin@12345",
        name="Admin User",
        mobile="9000000001",
        employee_code="EMP-ADMIN-001",
    )