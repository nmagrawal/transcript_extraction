import os
from dotenv import load_dotenv

from pymongo import MongoClient
from pymongo.server_api import ServerApi

# 1. Connection URI 
load_dotenv()
uri = os.getenv("MONGODB_URI")
# 2. Create a new client and connect to the server
client = MongoClient(uri, serverSelectionTimeoutMS=10000)

# 2. Select Database
db = client["opgov-prod"]
source_col = db["meetings"]
target_col_name = "speakers_history"

print("Starting aggregation...")

try:
    # 3. Define the Aggregation Pipeline
    pipeline = [
        # Stage 1: Filter out meetings that have no public comments
        {
            "$match": {
                "PublicComments": {"$exists": True, "$ne": []}
            }
        },
        # Stage 2: 'Unwind' the comments array.
        # This splits the meeting document: if a meeting has 12 speakers, 
        # this creates 12 documents in memory, one for each speaker.
        {
            "$unwind": "$PublicComments"
        },
        # Stage 3: Group by the Speaker's Name
        {
            "$group": {
                "_id": "$PublicComments.Speaker", # The unique key is the Name
                
                # We count how many times they have spoken total
                "total_comments": {"$sum": 1},
                
                # We push their comment details into a new list
                "engagements": {
                    "$push": {
                        "meeting_seoId": "$seoId",
                        "organization": "$organization",
                        "date": "$Date",
                        "comment_summary": "$PublicComments.CommentSummary",
                        "source_file": "$PublicComments.Source"
                    }
                }
            }
        },
        # Stage 4: Clean up the output format (Rename _id to speaker_name)
        {
            "$project": {
                "_id": 0,
                "speaker_name": "$_id",
                "total_comments": 1,
                "engagements": 1
            }
        },
        # Stage 5: Write the results to the new collection
        # $merge allows you to update existing records or insert new ones
        {
            "$merge": {
                "into": target_col_name,
                "whenMatched": "merge",
                "whenNotMatched": "insert"
            }
        }
    ]

    # 4. Run the Pipeline
    source_col.aggregate(pipeline)
    
    print(f"Success! Data has been aggregated into the collection: '{target_col_name}'")

    # Optional: Print a sample to verify
    sample = db[target_col_name].find_one()
    print("\n--- Sample Document from New Collection ---")
    print(sample)

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    client.close()