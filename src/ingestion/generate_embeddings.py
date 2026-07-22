"""
Generates embeddings for all documents in the 'incidents' and 'technical_docs'
collections using OpenAI's text-embedding-3-small, and writes them back onto
each document under the 'embedding' field.

Safe to re-run - it overwrites embeddings each time rather than duplicating.
"""
import os
import sys

from openai import OpenAI
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.db.connection import get_db

load_dotenv(override=True)  # load .env file if present, override any existing env vars

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

BATCH_SIZE = 20  # send texts to OpenAI in small batches rather than one at a time


def get_embeddings_batch(texts: list) -> list:
    """Calls OpenAI's embedding API for a batch of texts, returns list of vectors in the same order."""
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def embed_incidents():
    db = get_db()
    collection = db[os.getenv("MONGODB_INCIDENTS_COLLECTION", "incidents")]

    incidents = list(collection.find({}))
    print(f"Embedding {len(incidents)} incidents...")

    for i in range(0, len(incidents), BATCH_SIZE):
        batch = incidents[i:i + BATCH_SIZE]
        # Concatenate title + description so embeddings capture both symptom and resolution context
        texts = [f"{doc['title']}. {doc['description']}" for doc in batch]
        embeddings = get_embeddings_batch(texts)

        for doc, embedding in zip(batch, embeddings):
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"embedding": embedding}}
            )
        print(f"  Embedded {min(i + BATCH_SIZE, len(incidents))}/{len(incidents)}")

    print("Incidents embedding complete.\n")


def embed_documents():
    db = get_db()
    collection = db[os.getenv("MONGODB_DOCS_COLLECTION", "technical_docs")]

    docs = list(collection.find({}))
    print(f"Embedding {len(docs)} document chunks...")

    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i:i + BATCH_SIZE]
        texts = [doc["chunk_text"] for doc in batch]
        embeddings = get_embeddings_batch(texts)

        for doc, embedding in zip(batch, embeddings):
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"embedding": embedding}}
            )
        print(f"  Embedded {min(i + BATCH_SIZE, len(docs))}/{len(docs)}")

    print("Document chunks embedding complete.\n")


if __name__ == "__main__":
    embed_incidents()
    embed_documents()

    # Sanity check
    db = get_db()
    sample = db[os.getenv("MONGODB_INCIDENTS_COLLECTION", "incidents")].find_one({"incident_id": "INC-101"})
    print("Sample check - embedding length:", len(sample["embedding"]))
    print("First 5 values:", sample["embedding"][:5])