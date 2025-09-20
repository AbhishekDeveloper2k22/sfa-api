from pymongo import MongoClient
from urllib.parse import quote_plus
from config import settings

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize_connections()
        return cls._instance
    
    def _initialize_connections(self):
        # Create MongoDB connection strings with properly escaped credentials
        self.db1_uri = f"mongodb+srv://{quote_plus(settings.DB1_USERNAME)}:{quote_plus(settings.DB1_PASSWORD)}@{settings.DB1_HOST}/?authSource={settings.DB1_AUTH_SOURCE}&ssl=true&retryWrites=false"

        # Create MongoDB clients
        self.client1 = MongoClient(self.db1_uri)
    
    def get_client1(self):
        return self.client1
        
    def close_connections(self):
        """Close all database connections"""
        self.client1.close()

# Create a singleton instance
db = Database()

# Export the clients for easy access
client1 = db.get_client1()
