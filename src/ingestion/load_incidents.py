"""
Loads sample_incidents.json into the MongoDB 'incidents' collection.
Run this once to seed the database. Safe to re-run — it clears existing
incidents first so you don't get duplicates.
"""
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.db.connection import get_db


def load_incidents():
    db = get_db()
    collection_name = os.getenv("MONGODB_INCIDENTS_COLLECTION", "incidents")
    collection = db[collection_name]

    # Load the JSON file
    data_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "sample_incidents", "sample_incidents.json"
    )
    with open(data_path, "r") as f:
        incidents = json.load(f)

    # Clear existing data so re-running this script doesn't create duplicates
    deleted = collection.delete_many({})
    print(f"Cleared {deleted.deleted_count} existing documents.")

    # Add source_type field to each (matches our schema decision)
    for incident in incidents:
        incident["source_type"] = "ticket"

    # Insert all at once
    result = collection.insert_many(incidents)
    print(f"Inserted {len(result.inserted_ids)} incidents into '{collection_name}'.")

    # Quick sanity check - print one document back
    sample = collection.find_one({"incident_id": "INC-101"})
    print("\nSample document check:")
    print(sample)


if __name__ == "__main__":
    load_incidents()