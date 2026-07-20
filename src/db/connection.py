import os
from pymongo import MongoClient
from pymongo.database import Database
from dotenv import load_dotenv

load_dotenv()

_client = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise ValueError(
                "MONGODB_URI not set. Check your .env file."
            )
        _client = MongoClient(uri)
    return _client


def get_db() -> Database:
    db_name = os.getenv("MONGODB_DB_NAME", "incident_intel")
    return get_client()[db_name]


def test_connection() -> bool:
    try:
        client = get_client()
        client.admin.command("ping")
        print("✅ Connected to MongoDB Atlas successfully.")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()