"""
Vector search retrieval against the 'incidents' and 'technical_docs' collections.
Takes a text query, embeds it with the same model used during ingestion,
and searches MongoDB Atlas Vector Search for the most similar matches.
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

# Empirically calibrated: relevant matches scored ~0.81-0.87, an unrelated
# query scored ~0.60 on our test data. 0.70 sits in the gap between them.
CONFIDENCE_THRESHOLD = 0.70


def embed_query(text: str) -> list:
    """Converts a text query into the same kind of vector used for stored documents."""
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[text])
    return response.data[0].embedding


def search_similar_incidents(query_text: str, top_k: int = 3) -> dict:
    """
    Searches the 'incidents' collection for the most semantically similar
    past incidents to the given query text.
    """
    db = get_db()
    collection = db[os.getenv("MONGODB_INCIDENTS_COLLECTION", "incidents")]

    query_vector = embed_query(query_text)

    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": 100,
                "limit": top_k
            }
        },
        {
            "$project": {
                "_id": 0,
                "incident_id": 1,
                "title": 1,
                "description": 1,
                "service": 1,
                "severity": 1,
                "date": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]

    results = list(collection.aggregate(pipeline))
    has_strong_match = bool(results) and results[0]["score"] >= CONFIDENCE_THRESHOLD

    return {
        "results": results,
        "has_strong_match": has_strong_match
    }


def search_technical_documents(query_text: str, top_k: int = 3) -> dict:
    """
    Searches the 'technical_docs' collection (PDF runbook chunks) for the
    most semantically similar sections to the given query text.
    """
    db = get_db()
    collection = db[os.getenv("MONGODB_DOCS_COLLECTION", "technical_docs")]

    query_vector = embed_query(query_text)

    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": 100,
                "limit": top_k
            }
        },
        {
            "$project": {
                "_id": 0,
                "doc_id": 1,
                "source_file": 1,
                "section": 1,
                "chunk_text": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]

    results = list(collection.aggregate(pipeline))
    has_strong_match = bool(results) and results[0]["score"] >= CONFIDENCE_THRESHOLD

    return {
        "results": results,
        "has_strong_match": has_strong_match
    }


if __name__ == "__main__":
    test_queries = [
        "Checkout is failing with timeout errors, users seeing 504s on payment page",
        "Employee cafeteria menu changed to vegetarian options only",
    ]

    print("=== Testing search_similar_incidents ===\n")
    for test_query in test_queries:
        print(f"Query: {test_query}")
        output = search_similar_incidents(test_query, top_k=3)
        confidence_label = "STRONG MATCH" if output["has_strong_match"] else "NO STRONG MATCH (possible novel incident)"
        print(f"Confidence: {confidence_label}\n")
        for r in output["results"]:
            print(f"  [{r['score']:.3f}] {r['incident_id']} — {r['title']}")
        print("\n" + "-" * 60 + "\n")

    print("\n=== Testing search_technical_documents ===\n")
    doc_query = "connection pool exhaustion causing timeouts"
    print(f"Query: {doc_query}")
    doc_output = search_technical_documents(doc_query, top_k=3)
    confidence_label = "STRONG MATCH" if doc_output["has_strong_match"] else "NO STRONG MATCH"
    print(f"Confidence: {confidence_label}\n")
    for r in doc_output["results"]:
        print(f"  [{r['score']:.3f}] {r['source_file']} — {r['section']}")