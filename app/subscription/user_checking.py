
import requests
import os
import logging
from dotenv import load_dotenv
from pymongo import MongoClient


# 1. Connection URI 
load_dotenv()
uri = os.getenv("MONGODB_URI")

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

# 2. Create a new client
client = MongoClient(uri, serverSelectionTimeoutMS=10000)

# 3. Select Database
db = client["opgov-prod"]
users = db["users"]




def update_clerk_unsafe_metadata(clerk_id, api_key):
    """
    Update Clerk user's unsafeMetadata.newsletterSubscribed to True.
    Returns True if successful, False otherwise.
    """
    url = f"https://api.clerk.com/v1/users/{clerk_id}/metadata"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "unsafe_metadata": {
            "newsletterSubscribed": True
        }
    }
    try:
        response = requests.patch(url, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            return True
        else:
            logging.error(f"Clerk API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logging.exception(f"Exception updating Clerk metadata: {e}")
        return False

def subscribe_user_to_newsletter(email):
    """
    If a user with the given email exists, set unsafeMetadata.newsletterSubscribed to True in MongoDB and Clerk.
    If not, insert a new user with the email and unsafeMetadata.newsletterSubscribed=True in MongoDB only.
    Returns a message indicating the action taken.
    """
    # Normalize email (lowercase, strip spaces)
    email = email.strip().lower()
    clerk_api_key = os.getenv("CLERK_SECRET_KEY")
    try:
        user = users.find_one({"email": email})
        clerk_updated = False
        if user:
            result = users.update_one(
                {"email": email},
                {"$set": {"unsafeMetadata.newsletterSubscribed": True}}
            )
            # Update Clerk if clerkId exists and API key is available
            clerk_id = user.get("clerkId")
            if clerk_id and clerk_api_key:
                clerk_updated = update_clerk_unsafe_metadata(clerk_id, clerk_api_key)
            return (
                f"Email already exists. Newsletter subscription updated. Clerk updated: {clerk_updated}."
                if result.modified_count > 0
                else f"Email already exists. Newsletter subscription was already True. Clerk updated: {clerk_updated}."
            )
        else:
            users.insert_one({"email": email, "unsafeMetadata": {"newsletterSubscribed": True}})
            return "Email did not exist. New user created and subscribed to newsletter."
    except Exception as e:
        logging.exception(f"Exception in subscribe_user_to_newsletter: {e}")
        return "An error occurred while subscribing the user."