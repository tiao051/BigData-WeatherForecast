from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()
import os

# MongoDB connection configuration from environment variables
MONGO_HOST = os.environ.get("MONGO_HOST", "localhost")
MONGO_PORT = int(os.environ.get("MONGO_PORT", 27017))
MONGO_USERNAME = os.environ.get("MONGO_USERNAME", None)
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD", None)
DB_NAME = os.environ.get("DB_NAME", "your_database_name")

# Initialize MongoDB client with authentication if credentials provided
if MONGO_USERNAME and MONGO_PASSWORD:
    client = MongoClient(
        MONGO_HOST, 
        MONGO_PORT,
        username=MONGO_USERNAME,
        password=MONGO_PASSWORD,
        authSource='admin'  # MongoDB admin database for authentication
    )
else:
    # Connect without authentication (for development)
    client = MongoClient(MONGO_HOST, MONGO_PORT)

# Connect to the specified database
db = client[DB_NAME]

# Create indexes for better query performance
def create_indexes():
    """Create database indexes for optimized query performance"""
    try:
        # Index on predicted_at for sorting (descending order)
        db.predict.create_index([("predicted_at", -1)], background=True)
        print("✓ MongoDB indexes created successfully")
    except Exception as e:
        print(f"⚠ Warning: Could not create indexes - {e}")

# Initialize indexes when module is imported
create_indexes()

