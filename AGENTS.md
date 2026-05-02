# AGENTS.md

This file provides guidance to agents (i.e., ADAL) when working with code in this repository.

## Essential Commands

```bash
# Setup (one-time)
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then add OPENROUTER_API_KEY

# Ingest or rebuild ChromaDB locally after cloning or changing docs/
python3 -c "from src.ingest import ingest_documents; print(ingest_documents(force=True))"

# Run the Flask app locally
python3 -m src.app  # http://localhost:5000

# Run all tests
python3 -m pytest tests/ -v --tb=short

# Run focused tests
python3 -m pytest tests/test_app.py -v --tb=short
python3 -m pytest tests/test_guardrails.py -v --tb=short
python3 -m pytest tests/test_ingest.py -v --tb=short
python3 -m pytest tests/test_health.py -v --tb=short

# Run evaluation; requires OPENROUTER_API_KEY and makes live LLM calls
python3 evaluation/run_evaluation.py

# Test streaming /chat manually; -N keeps curl from buffering SSE output
curl -N -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the PTO policy?"}'

# DigitalOcean App Platform checks
doctl apps list
doctl apps get 4aba105d-e74f-451d-811e-fe802f758ac2
```

## Critical Gotchas

- **Use `python3`, not bare `python`, locally** — this environment may not have a `python` executable.
- **`/chat` is Server-Sent Events (SSE), not normal JSON** — successful and validation responses stream lines shaped like `data: {...}\n\n`. Tests parse SSE via `_extract_sse_data()` in `tests/test_app.py`.
- **Missing question is the exception** — `POST /chat {}` still returns regular JSON with HTTP 400; invalid question strings return SSE with a `chunk`.
- **OPENROUTER_API_KEY required for real `/chat` answers and evaluation** — unit tests do not require a live key.
- **Ingest before local RAG use** — `chroma_db/` and `models_cache/` are generated artifacts and gitignored. Run ingestion locally after cloning.
- **DigitalOcean build handles model warmup + ingestion** — `.do/app.yaml` runs FastEmbed warmup and `ingest_documents(force=True)` during build.
- **Do not add `.python-version` lightly** — DigitalOcean previously failed downloading Python `3.12.13`; leaving DO on its buildpack default worked. CI still tests Python 3.12 via GitHub Actions.
- **ChromaDB v0.6.x `list_collections()` returns strings** — never use `.name` on returned values. Existing checks use `list(client.list_collections())`.
- **Chroma telemetry warnings are harmless** — `Failed to send telemetry event...` does not indicate app failure.
- **Templates/static are outside `src/`** — Flask config in `src/app.py` uses `template_folder="../templates"` and `static_folder="../static"`.
- **README.md is stale in places** — trust this file and source files for current OpenRouter/FastEmbed/DigitalOcean/SSE behavior.

## Non-Obvious Architecture

### Request + Streaming Flow

```text
Browser
  GET /                         -> Flask renders templates/index.html
  POST /chat {"question": "..."} -> Flask validates input
                                      |
                                      | invalid string
                                      v
                                  SSE stream with validation error chunk
                                      |
                                      | valid question
                                      v
src.rag_chain.ask_stream()
  1. Embed query with FastEmbed BAAI/bge-small-en-v1.5
  2. Query ChromaDB collection "acme_policies"
  3. Send retrieved sources FIRST as SSE: {"type":"sources","sources":[...]}
  4. Stream OpenRouter/LangChain chunks as SSE: {"chunk":"..."}
  5. Append guardrail note if validate_output() adds one
  6. End with SSE: {"type":"done"}

static/chat.js
  - Reads the response stream with ReadableStream.getReader()
  - Removes skeleton when first source/chunk arrives
  - Renders markdown incrementally with marked.js
  - Uses the pre-sent source list to dynamically badge/link source mentions
  - Adds source chips, Copy button, and Retry button when appropriate
```

### Citation Handling

Citation robustness is intentionally split between backend prompt discipline and frontend repair:

- `rag_chain.SYSTEM_PROMPT` tells the model to use exact ASCII bracket citations like `[pto-and-leave-policy]` and avoid `Source 1` / full-width brackets.
- `_format_context()` labels context chunks as `Document Name: [doc-id]` to reduce numbered-source hallucinations.
- `ask_stream()` emits the retrieved source list before text generation.
- `static/chat.js::formatAnswer(text, activeSources)` dynamically links any mention of known retrieved doc IDs, even if the model omits brackets or uses odd brackets.
- Source chips at the bottom link to `/docs/<file>.pdf`; inline source badges link to the same PDFs.

If citation behavior regresses, inspect `static/chat.js` first, then the prompt/context format in `src/rag_chain.py`.

### Ingestion Flow

```text
docs/*.pdf
  -> pypdf PdfReader extracts text
  -> RecursiveCharacterTextSplitter(chunk_size=1000, overlap=200)
  -> FastEmbed embed_documents() using project-local models_cache/
  -> ChromaDB PersistentClient(path=CHROMA_PERSIST_DIR)
  -> collection "acme_policies"
```

Ingestion uses a corpus hash over `*.md`, `*.pdf`, and `*.txt`; current corpus is PDF-only. `force=False` skips if collection metadata hash matches.

### Startup / Deployment Flow

```text
DigitalOcean build_command
  pip install -r requirements.txt
  -> FastEmbed warmup into models_cache/
  -> ingest_documents(force=True) into chroma_db/

Runtime
  gunicorn src.app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1 --threads 2
  -> src.app imports
  -> background _startup() runs only if OPENROUTER_API_KEY exists
  -> ingest_documents(force=False) should skip
  -> warm_up() initializes embeddings + ChatOpenAI wrapper
```

`rag_chain._get_chroma_collection()` has an on-demand ingest fallback if the collection is missing.

## Key Entry Points

| Need | File | Notes |
|---|---|---|
| Flask routes | `src/app.py` | `/`, `/chat` SSE, `/docs/<filename>`, `/health`, `/healthz` |
| RAG + streaming | `src/rag_chain.py` | `ask_stream(question)` is the main path; `warm_up()` runs at startup |
| Input/output guardrails | `src/guardrails.py` | Input rejects invalid/off-topic before LLM; output adds citation note if missing |
| Ingestion | `src/ingest.py` | PDF loading, chunking, corpus hash, Chroma write |
| Config/env | `src/config.py` | OpenRouter, Chroma paths, FastEmbed cache, chunk sizes |
| Frontend behavior | `static/chat.js` | SSE parsing, markdown rendering, source linking, retry/copy UX |
| Frontend style | `static/style.css` | Full-width layout, Quantic-inspired navy/gold palette, responsive tweaks |
| HTML shell | `templates/index.html` | marked.js CDN, suggested-question chips, favicon |
| App Platform spec | `.do/app.yaml` | DO build/run commands and secret env var declaration |
| CI | `.github/workflows/ci-cd.yml` | Install, import check, pytest; DO auto-deploys on push |
| Keep-warm | `.github/workflows/keep-warm.yml` | Historical name may mention Render; pings health URL |
| Evaluation | `evaluation/run_evaluation.py` | Live 25-question eval; writes `evaluation/eval_results.json` |

## Config & Environment

Loaded in `src/config.py` via `python-dotenv` from project-root `.env`.

| Variable | Default | Required |
|---|---:|---|
| `OPENROUTER_API_KEY` | empty | Yes for `/chat` and evaluation |
| `OPENROUTER_MODEL` | `openai/gpt-oss-20b:free` | No |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | No |
| `CHROMA_PERSIST_DIR` | `chroma_db` | No |
| `CHUNK_SIZE` | `1000` | No |
| `CHUNK_OVERLAP` | `200` | No |
| `RETRIEVAL_K` | `5` | No |

OpenRouter headers in `rag_chain._get_llm()` include repository referer and title.

## Corpus Details

- `docs/` contains 11 PDFs (~111 pages):
  - 10 synthetic Acme Corp policy PDFs
  - 1 real public document: `public_counsel_employee_handbook.pdf`
- The app exposes PDFs through `GET /docs/<filename>` for source review.
- Latest known automated evaluation: **100% groundedness**, **92% citation accuracy**.

## Testing Notes

- Tests are designed to run without `OPENROUTER_API_KEY`.
- `tests/test_app.py` validates `/chat` guardrail paths by parsing SSE chunks, not `response.get_json()`.
- `test_chat_missing_question` remains regular JSON/400 because the request is malformed before SSE setup.
- `tests/test_ingest.py::test_load_and_chunk` may initialize embedding dependencies/cache and can be slower on first run.
- CI uses Python 3.12 even though DigitalOcean runtime may default to a newer Python version.

## Deployment Notes

- Live app: `https://sea-turtle-app-gnq2r.ondigitalocean.app`
- DigitalOcean app ID used in prior CLI checks: `4aba105d-e74f-451d-811e-fe802f758ac2`
- DO App Platform auto-deploys from GitHub `main`.
- Render is obsolete and can remain deleted; stale Render references should be removed if found.
- If DO build fails after Python changes, first suspect buildpack/runtime version support before changing app code.

## Known Issues & History

| Issue | Root Cause | Fix |
|---|---|---|
| Render 502 / OOM | Runtime re-ingest + free-tier memory constraints | Moved to DO; build-time ingest; startup skip |
| Render suspension | Free-tier compute limits | Migrated to DigitalOcean App Platform |
| Chroma collection check breakage | ChromaDB API changed across versions | Use `list(client.list_collections())` strings |
| `/chat` tests failing after streaming | Tests expected JSON but endpoint returns SSE | Added SSE parser helper in `tests/test_app.py` |
| Citation text not clickable | Model varied citation formatting | Send sources first; dynamic frontend source linking |
| Full-width `【source】` citations | LLM citation style hallucination | Prompt rule + frontend source-link repair |
