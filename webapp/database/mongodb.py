from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()
import os

# MongoDB connection configuration from environment variables
MONGO_HOST = os.environ.get("MONGO_HOST", "localhost")
MONGO_PORT = int(os.environ.get("MONGO_PORT", 27017))
DB_NAME = os.environ.get("DB_NAME", "your_database_name")

# Initialize MongoDB client with host and port
client = MongoClient(MONGO_HOST, MONGO_PORT)

# Connect to the specified database
db = client[DB_NAME]
