import os
from dotenv import load_dotenv
from pymongo import MongoClient

# 1. Connection URI 
load_dotenv()
uri = os.getenv("MONGODB_URI")

# 2. Create a new client
client = MongoClient(uri, serverSelectionTimeoutMS=10000)

# 3. Select Database
db = client["opgov-prod"]
source_col = db["meetings"]
target_col_name = "speakers_history"

print("Starting smart aggregation (Appending new meetings & updating organizations)...")

try:
    # 4. Define the Aggregation Pipeline
    pipeline = [
        # Stage 1: Filter out meetings that have no public comments
        {
            "$match": {
                "PublicComments": {"$exists": True, "$ne": []}
            }
        },
        # Stage 2: 'Unwind' the comments array
        {
            "$unwind": "$PublicComments"
        },
        # Stage 3: Group by the Speaker's Name
        {
            "$group": {
                "_id": "$PublicComments.Speaker", 
                
                # NEW: Grab a unique list of organizations they spoke at in this batch
                "organizations": {
                    "$addToSet": "$organization" 
                },
                
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
        # Stage 4: Clean up output format
        {
            "$project": {
                "_id": 1,
                "speaker_name": "$_id",
                "organizations": 1, # NEW: Include the organizations array
                "engagements": 1
            }
        },
        # Stage 5: The "Smart Append" Merge
        {
            "$merge": {
                "into": target_col_name,
                "on": "_id",
                "whenMatched": [
                    # Step A: Find the meetings in the NEW data that aren't in the OLD data
                    {
                        "$set": {
                            "new_engagements_to_add": {
                                "$filter": {
                                    "input": "$$new.engagements",
                                    "as": "incoming_eng",
                                    "cond": {
                                        "$not": {
                                            "$in": [
                                                "$$incoming_eng.meeting_seoId", 
                                                {"$ifNull": ["$engagements.meeting_seoId", []]}
                                            ]
                                        }
                                    }
                                }
                            }
                        }
                    },
                    # Step B: Append the filtered meetings AND combine the organizations
                    {
                        "$set": {
                            "engagements": {
                                "$concatArrays": [
                                    {"$ifNull": ["$engagements", []]}, 
                                    "$new_engagements_to_add"
                                ]
                            },
                            # NEW: $setUnion combines the old organizations with the new ones 
                            # and automatically removes any duplicates!
                            "organizations": {
                                "$setUnion": [
                                    {"$ifNull": ["$organizations", []]},
                                    "$$new.organizations"
                                ]
                            }
                        }
                    },
                    # Step C: Recalculate the total_comments based on the new array size
                    {
                        "$set": {
                            "total_comments": {"$size": "$engagements"}
                        }
                    },
                    # Step D: Clean up our temporary variable
                    {
                        "$unset": "new_engagements_to_add"
                    }
                ],
                "whenNotMatched": "insert"
            }
        }
    ]

    # 5. Run the Pipeline
    source_col.aggregate(pipeline)
    
    print(f"Success! Checked for new meetings and appended them to '{target_col_name}' safely.")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    client.close()