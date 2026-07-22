"""
Loads PDF runbooks into the MongoDB 'technical_docs' collection.
Splits each PDF into section-based chunks (Service Overview, Common Failure
Patterns, Diagnostic Steps, Escalation Criteria) rather than fixed-size chunks,
since these documents have clean, meaningful section boundaries.
"""
import os
import re
import sys
import glob

from pypdf import PdfReader

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.db.connection import get_db

# The section headers used consistently across all runbook PDFs
SECTION_HEADERS = [
    "Service Overview",
    "Common Failure Patterns",
    "Diagnostic Steps",
    "Escalation Criteria",
]

# Lines that are repeated header/footer noise on every page - strip these out
NOISE_PATTERNS = [
    r"Internal Use Only.*",
    r".*RUNBOOK TIER-\d.*",
    r"SERVICE RUNBOOK",
]


def clean_text(raw_text: str) -> str:
    """Removes repeated header/footer noise lines from extracted PDF text."""
    lines = raw_text.split("\n")
    cleaned = []
    for line in lines:
        if any(re.match(pattern, line.strip()) for pattern in NOISE_PATTERNS):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def split_into_sections(text: str, service_name: str, source_file: str) -> list:
    """Splits cleaned text into one chunk per section header."""
    # Build a regex that matches "1 Service Overview", "2 Common Failure Patterns", etc.
    header_pattern = r"\n?\d\s(" + "|".join(SECTION_HEADERS) + r")\n"
    parts = re.split(header_pattern, text)

    # re.split with a capturing group returns: [before_first_match, header1, content1, header2, content2, ...]
    chunks = []
    # parts[0] is anything before the first section header (title/overview banner) - skip it
    for i in range(1, len(parts), 2):
        header = parts[i]
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if content:
            chunks.append({
                "doc_id": f"{service_name}-{header.lower().replace(' ', '-')}",
                "source_file": source_file,
                "section": header,
                "chunk_text": f"{header}: {content}",
                "source_type": "document",
            })
    return chunks


def load_documents():
    db = get_db()
    collection_name = os.getenv("MONGODB_DOCS_COLLECTION", "technical_docs")
    collection = db[collection_name]

    deleted = collection.delete_many({})
    print(f"Cleared {deleted.deleted_count} existing document chunks.")

    docs_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_docs")
    pdf_files = glob.glob(os.path.join(docs_path, "*.pdf"))

    all_chunks = []
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        # infer service name from filename, e.g. "Payments_Gateway_Runbook.pdf" -> "payments-gateway"
        service_name = filename.replace("_Runbook.pdf", "").replace("_", "-").lower()

        reader = PdfReader(pdf_path)
        raw_text = ""
        for page in reader.pages:
            raw_text += page.extract_text() + "\n"

        cleaned = clean_text(raw_text)
        chunks = split_into_sections(cleaned, service_name, filename)

        print(f"{filename}: extracted {len(chunks)} section chunks")
        all_chunks.extend(chunks)

    if all_chunks:
        result = collection.insert_many(all_chunks)
        print(f"\nInserted {len(result.inserted_ids)} total chunks into '{collection_name}'.")

    # Sanity check - print one chunk back
    sample = collection.find_one({"section": "Common Failure Patterns"})
    print("\nSample chunk check:")
    print(sample)


if __name__ == "__main__":
    load_documents()