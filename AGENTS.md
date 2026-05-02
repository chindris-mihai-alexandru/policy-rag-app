# AGENTS.md

This file provides guidance to agents (i.e., ADAL) when working with code in this repository.

## Essential Commands

```bash
# Setup (one-time)
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then add OPENROUTER_API_KEY

# Ingest documents into ChromaDB (required before first run or after doc changes)
python -c "from src.ingest import ingest_documents; print(ingest_documents(force=True))"

# Run the app locally
python -m src.app  # serves on http://localhost:5000

# Run all tests
python -m pytest tests/ -v

# Run evaluation (~3-5 min, hits OpenRouter API)
python evaluation/run_evaluation.py
```

## Critical Gotchas

- **OPENROUTER_API_KEY required for /chat and evaluation** — tests do NOT hit the LLM. `/chat` and `run_evaluation.py` require a live key.
- **Ingest before first run** — ChromaDB is gitignored (`chroma_db/`). After cloning, run ingest. On DigitalOcean, the `build_command` in `.do/app.yaml` handles this.
- **ChromaDB v0.6.0 API** — `list_collections()` returns **strings** (collection names), NOT Collection objects. Never call `.name` on the result. See `ingest.py` and `rag_chain.py`.
- **ChromaDB corpus hash** — Ingestion is idempotent. It hashes all `docs/*.pdf` files and skips re-ingestion if unchanged. Use `force=True` to override.
- **ChromaDB telemetry warnings** — `Failed to send telemetry event` messages are harmless.
- **Import paths use `src.` prefix** — Run as `python -m src.app`. All imports: `from src.config import ...`.
- **Templates/static are outside src/** — Flask uses `template_folder="../templates"` and `static_folder="../static"` relative to `src/app.py`.
- **Ephemeral filesystem on DigitalOcean App Platform** — `chroma_db/` and `models_cache/` are rebuilt each deploy via the custom build command. The startup thread uses `force=False` so it skips re-ingest if the build already populated the DB.
- **Python 3.14 on DO** — DigitalOcean buildpack defaults to Python 3.14 (no `.python-version` file pinned). Add one if breakage occurs.

## Architecture & Data Flow

### Request Flow

```
User (browser) → GET / → Flask serves templates/index.html
                          ↓ (user types question)
Browser JS     → POST /chat {question: "..."}
                          ↓
Flask app.py   → guardrails.validate_input(question)
                          ↓ (if valid)
               → rag_chain.ask(question)
                          ↓
                 1. _get_embeddings() → FastEmbed BAAI/bge-small-en-v1.5 (ONNX, local)
                 2. embed query → ChromaDB.query(top_k=5)
                 3. _format_context() → builds numbered source blocks
                 4. ChatPromptTemplate(system + human) → OpenRouter API
                 5. Parse response → extract sources
                          ↓
               → guardrails.validate_output(answer)
                          ↓
               → JSON {answer, sources[], latency_ms}
                          ↓
Browser JS     → marked.parse(answer) → rendered HTML with tables/lists/headers
               → source chips → click → GET /docs/<file>.pdf → opens PDF
```

### Ingestion Flow

```
docs/*.pdf → pypdf PdfReader (full text extraction per page)
           → RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
           → FastEmbed embed_documents() [ONNX, no torch]
           → ChromaDB collection "acme_policies" (persistent in chroma_db/)
```

Each chunk carries metadata: `{source: "pto-and-leave-policy", file: "pto-and-leave-policy.pdf"}`.

### Guardrails (two layers)

1. **Input** (`guardrails.validate_input`): Rejects empty, too-short (<3 chars), too-long (>500 chars), and off-topic questions. Runs BEFORE any LLM call.
2. **Output** (`guardrails.validate_output`): Truncates >4000 chars, checks for `[doc-name]` citation markers, appends a verification note if missing.

### LLM Prompt Strategy

System prompt in `rag_chain.py` enforces 7 rules: answer only from context, cite with `[doc-name]`, refuse off-topic, never fabricate. Human prompt injects `[Source N: doc-name]` blocks for reliable citation extraction.

## Key Entry Points

| What | File | Notes |
|------|------|-------|
| Flask app | `src/app.py` | Routes: `/`, `/chat`, `/docs/<filename>`, `/health`, `/healthz` |
| RAG pipeline | `src/rag_chain.py` | `ask(question)` is the main entry |
| Ingestion | `src/ingest.py` | `ingest_documents(force=bool)` |
| Config | `src/config.py` | All env vars with defaults |
| Guardrails | `src/guardrails.py` | `validate_input()`, `validate_output()` |
| Chat UI | `templates/index.html` + `static/chat.js` + `static/style.css` | Vanilla JS + marked.js (CDN) |
| Evaluation | `evaluation/run_evaluation.py` | 25 questions → `eval_results.json` |
| CI/CD | `.github/workflows/ci-cd.yml` | install → import check → pytest |
| Keep-warm | `.github/workflows/keep-warm.yml` | Cron every 10 min, pings `/healthz` |
| DO config | `.do/app.yaml` | Build: pip + embed warmup + ingest; Start: gunicorn |

## Config & Environment

All config lives in `src/config.py`, loaded from `.env` via `python-dotenv`:

| Variable | Default | Required |
|----------|---------|----------|
| `OPENROUTER_API_KEY` | *(none)* | Yes (for /chat and eval) |
| `OPENROUTER_MODEL` | `openai/gpt-oss-20b:free` | No |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | No |
| `CHROMA_PERSIST_DIR` | `chroma_db` | No |
| `CHUNK_SIZE` | `1000` | No |
| `CHUNK_OVERLAP` | `200` | No |
| `RETRIEVAL_K` | `5` | No |

## Corpus Details

11 PDF files in `docs/` (~111 pages total):
- 10 synthetic Acme Corp policies (HR, IT, Finance topics)
- 1 real public document: `public_counsel_employee_handbook.pdf`

Eval results: **100% Groundedness**, **92% Citation Accuracy** (25-question automated run).

## Deployment (DigitalOcean App Platform)

- **Live URL**: https://sea-turtle-app-gnq2r.ondigitalocean.app
- **Cost**: ~$5/mo (covered by GitHub Student Pack $200 DO credit)
- **No sleep/suspension** — always-on, no cold-start 502s
- `.do/app.yaml`: build_command runs pip + embed model warmup + ingest; run_command is gunicorn
- Build caches dependencies via Heroku buildpack layer
- `OPENROUTER_API_KEY` is stored as a secret env var in DO dashboard
- Single worker + 2 threads (512MB RAM instance)
- Keep-warm GitHub Action pings `/healthz` every 10 min

## Frontend (UI)

- **Markdown rendering**: `marked.js` v9 (CDN) — handles tables, headers, lists, bold, code
- **Source chips**: Clickable pill buttons → `GET /docs/<file>.pdf` → opens the actual policy PDF in a new browser tab
- **No build step** — plain HTML/CSS/JS, no webpack/npm

## Known Issues & History

| Issue | Root Cause | Fix Applied |
|-------|-----------|-------------|
| 502 on Render | `list_collections()` returned Collection objects in older chromadb, strings in v0.6.0 | Fixed both `ingest.py` and `rag_chain.py` to use `list(client.list_collections())` directly |
| Render free tier suspensions | Monthly compute hour cap hit | Migrated to DigitalOcean App Platform |
| First-boot re-ingest OOM | Build-time DB not detected at runtime (same chromadb bug) | Fixed by chromadb v0.6.0 fix above |
| Chat error on first deploy | `_get_chroma_collection()` crashed if collection missing | Added auto-ingest fallback in `rag_chain.py` |
