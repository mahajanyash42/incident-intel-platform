# AI Incident Intelligence and Root-Cause Analysis Platform

An AI agent that ingests incident tickets, technical runbooks (PDFs), and error screenshots,
then uses RAG + a LangGraph agent to produce cited, evidence-backed root-cause analysis and
remediation recommendations for SRE/DevOps incidents.

Built for [Course Name] under Professor Bharti Motwani.

## What it does

An on-call engineer describes an incident (optionally attaching a screenshot of an error). The
system:
1. Extracts text from any attached screenshot via OCR
2. Searches historical incident tickets for similar past incidents (MongoDB Atlas Vector Search)
3. Searches technical runbooks for relevant documented failure patterns and procedures
4. Synthesizes both sources into a root-cause report with explicit citations
5. If no strong historical match exists, explicitly flags the incident as novel rather than
   fabricating a confident-sounding but unsupported answer

## Architecture

See `docs/architecture.png` for the full diagram. In short:

```
Screenshot (optional) --> OCR (pytesseract) --\
                                                >-- Combined incident text
Text description ------------------------------/
                                |
                                v
                     LangGraph Agent (gpt-4o-mini)
                    /                            \
      search_similar_incidents          search_technical_documents
                    \                            /
              MongoDB Atlas Vector Search (2 collections)
                                |
                                v
                Root-cause report with citations
                     (Streamlit UI)
```

## Tech stack

- **MongoDB Atlas** — document storage + Atlas Vector Search for semantic retrieval
- **OpenAI** — `text-embedding-3-small` for embeddings, `gpt-4o-mini` for agent reasoning
- **LangGraph / LangChain** — agent orchestration and tool calling
- **pytesseract** — OCR for error screenshots
- **pypdf** — PDF text extraction for technical runbooks
- **Streamlit** — user interface

## Current scope (v1 — academic submission)

- MongoDB collections for incidents (35 sample tickets) and technical docs (4 runbooks,
  chunked by section)
- Atlas Vector Search indexes on both collections (1536-dim, cosine similarity)
- OCR pipeline tested end-to-end against 5 sample screenshots — all correctly retrieve their
  intended matching incident
- Empirically calibrated confidence threshold (0.70) distinguishing strong matches from novel
  incidents, based on measured similarity scores (~0.81-0.87 for relevant matches vs. ~0.60 for
  unrelated queries)
- LangGraph agent with 3 tools: `search_similar_incidents`, `search_technical_documents`, and
  report synthesis
- Streamlit UI with text input and optional screenshot upload

## Roadmap (v2 — planned after submission)

- Human-in-the-loop escalation workflow
- Additional agent tools (log analysis, resolution/escalation recommendation)
- Formal evaluation harness (retrieval precision, hallucination rate, citation accuracy,
  latency/cost tracking)
- Deployment (Streamlit Community Cloud / Render)
- Polished UI, possible FastAPI backend

## Setup

### 1. Install dependencies
```bash
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. System dependency for OCR
`pytesseract` needs the Tesseract binary installed separately:
- Mac: `brew install tesseract`
- Ubuntu/Debian: `sudo apt install tesseract-ocr`
- Windows: install from https://github.com/UB-Mannheim/tesseract/wiki

### 3. Configure environment
```bash
cp .env.example .env
```
Fill in your MongoDB Atlas URI and OpenAI API key.

### 4. Seed the database
```bash
python src/ingestion/load_incidents.py
python src/ingestion/load_documents.py
python src/ingestion/generate_embeddings.py
```

### 5. Set up Atlas Vector Search indexes
In the Atlas dashboard, create a Vector Search index named `vector_index` on both the
`incidents` and `technical_docs` collections:
```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1536,
      "similarity": "cosine"
    }
  ]
}
```

### 6. Run the app
```bash
streamlit run app/main.py
```

## Project structure
```
incident-intel-platform/
├── app/
│   └── main.py                  # Streamlit UI
├── data/
│   ├── sample_incidents/        # 35 seed incident tickets (JSON)
│   ├── sample_docs/             # 4 PDF runbooks (payments, auth, search, database)
│   └── sample_screenshots/      # 5 synthetic error screenshots for OCR testing
├── src/
│   ├── db/
│   │   └── connection.py        # MongoDB connection singleton
│   ├── ingestion/
│   │   ├── load_incidents.py    # Seeds the incidents collection
│   │   ├── load_documents.py    # Parses + chunks PDFs into technical_docs
│   │   ├── generate_embeddings.py  # Embeds both collections
│   │   └── ocr_pipeline.py      # OCR extraction + retrieval test
│   ├── rag/
│   │   └── retrieval.py         # Vector search functions with confidence scoring
│   └── agent/
│       ├── tools.py             # LangChain tool wrappers
│       └── graph.py             # LangGraph agent definition
├── requirements.txt
└── .env.example
```

## Example use case

An engineer reports: *"Checkout API returning 504 errors, users unable to complete payment."*

The system retrieves historically similar incidents (e.g. a prior connection-pool exhaustion
event on the same service), cross-references the relevant runbook section, and returns a report
citing both sources with a recommended remediation — rather than a generic, unsupported answer.

If a genuinely novel incident is reported (no historical precedent), the system explicitly says
so rather than fabricating a confident but unsupported root cause.s