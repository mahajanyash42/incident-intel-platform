"""
LangChain tool definitions wrapping our existing retrieval functions.
These are what the LangGraph agent will call autonomously.
"""
import os
import sys

from langchain_core.tools import tool

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.rag.retrieval import search_similar_incidents, search_technical_documents


@tool
def search_similar_incidents_tool(query: str) -> str:
    """
    Search historical incident tickets for past incidents similar to the
    given description. Use this to find precedent for a current issue -
    e.g. whether this exact kind of failure has happened before, and how
    it was resolved. Returns matched incidents with similarity confidence.
    """
    output = search_similar_incidents(query, top_k=3)

    if not output["results"]:
        return "No historical incidents found in the database."

    lines = []
    if not output["has_strong_match"]:
        lines.append("NOTE: No strong match found. These results have low confidence and may not be relevant - treat as weak signal only, not solid evidence.\n")

    for r in output["results"]:
        lines.append(
            f"[{r['incident_id']}] {r['title']} (confidence: {r['score']:.2f})\n"
            f"  Service: {r['service']} | Severity: {r['severity']} | Date: {r['date']}\n"
            f"  Details: {r['description']}\n"
        )
    return "\n".join(lines)


@tool
def search_technical_documents_tool(query: str) -> str:
    """
    Search technical runbooks and documentation for relevant guidance on
    diagnosing or resolving a described issue. Use this to find official
    documented procedures, known failure patterns, and escalation criteria
    for a given service or symptom.
    """
    output = search_technical_documents(query, top_k=3)

    if not output["results"]:
        return "No technical documentation found in the database."

    lines = []
    if not output["has_strong_match"]:
        lines.append("NOTE: No strong match found. These results have low confidence - treat as weak signal only.\n")

    for r in output["results"]:
        lines.append(
            f"[{r['source_file']} - {r['section']}] (confidence: {r['score']:.2f})\n"
            f"  {r['chunk_text']}\n"
        )
    return "\n".join(lines)

if __name__ == "__main__":
    print("=== Testing search_similar_incidents_tool ===\n")
    result = search_similar_incidents_tool.invoke(
        "Checkout is failing with timeout errors, users seeing 504s on payment page"
    )
    print(result)

    print("\n" + "=" * 60 + "\n")

    print("=== Testing search_technical_documents_tool ===\n")
    result = search_technical_documents_tool.invoke(
        "connection pool exhaustion causing timeouts"
    )
    print(result)