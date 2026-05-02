# AGENTS.md

This file provides guidance to agents (i.e., ADAL) when working with code in this repository.

## Essential Commands

```bash
# Setup (one-time)
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then add GROQ_API_KEY

# Ingest documents into ChromaDB (required before first run or after doc changes)
python -c "from src.ingest import ingest_documents; print(ingest_documents(force=True))"

# Run the app locally
python -m src.app  # serves on http://localhost:5000

# Run all tests (30 tests, ~5s, no API key needed)
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_health.py -v
python -m pytest tests/test_guardrails.py -v
python -m pytest tests/test_app.py -v
python -m pytest tests/test_ingest.py -v

# Run evaluation (REQUIRES GROQ_API_KEY in .env, ~3-5 min, hits Groq API)
python evaluation/run_evaluation.py
```

## Critical Gotchas

- **GROQ_API_KEY required for /chat and evaluation** — tests in `test_app.py` and `test_guardrails.py` do NOT hit the LLM; they test guardrails and Flask routing only. But `/chat` with a valid policy question and `run_evaluation.py` require a live key.
- **Ingest before first run** — ChromaDB is gitignored (`chroma_db/`). After cloning, you must run the ingest command before the app can answer questions. On Render, the `buildCommand` in `render.yaml` handles this automatically.
- **ChromaDB corpus hash** — Ingestion is idempotent. It hashes all `docs/*.md` files and skips re-ingestion if unchanged. Use `force=True` to override.
- **ChromaDB telemetry warnings** — You'll see `Failed to send telemetry event` messages from ChromaDB. These are harmless and don't affect functionality.
- **Import paths use `src.` prefix** — The app is run as `python -m src.app`, not `python src/app.py`. All imports use `from src.config import ...` style. The evaluation script manually adds the project root to `sys.path`.
- **Templates/static are outside src/** — Flask is configured with `template_folder="../templates"` and `static_folder="../static"` relative to `src/app.py`. If you move `app.py`, these paths break.
- **Groq rate limits on free tier** — The evaluation script has a 2-second sleep between questions to avoid rate limiting. If you hit 429 errors, increase the delay.

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
                 1. _get_embeddings() → HuggingFace MiniLM-L6-v2 (local)
                 2. embed query → ChromaDB.query(top_k=5)
                 3. _format_context() → builds numbered source blocks
                 4. ChatPromptTemplate(system + human) → Groq API
                 5. Parse response → extract sources
                          ↓
               → guardrails.validate_output(answer)
                          ↓
               → JSON {answer, sources[], latency_ms}
```

### Ingestion Flow

```
docs/*.md → MarkdownHeaderTextSplitter (by #/##/###)
          → RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
          → HuggingFace embed_documents()
          → ChromaDB collection "acme_policies" (persistent in chroma_db/)
```

Each chunk carries metadata: `{source: "pto-and-leave-policy", file: "pto-and-leave-policy.md", heading_1: ..., heading_2: ...}`.

### Guardrails (two layers)

1. **Input** (`guardrails.validate_input`): Rejects empty, too-short (<3 chars), too-long (>500 chars), and off-topic questions (regex patterns for code requests, weather, recipes, etc.). Runs BEFORE any LLM call.
2. **Output** (`guardrails.validate_output`): Truncates >4000 chars, checks for `[doc-name]` citation markers, appends a verification note if citations are missing (unless the response is an out-of-scope message).

### LLM Prompt Strategy

The system prompt in `rag_chain.py` enforces 7 rules: answer only from context, cite with `[doc-name]`, refuse off-topic, never fabricate, etc. The human prompt template injects numbered `[Source N: doc-name]` blocks. This makes citation extraction reliable via regex.

## Key Entry Points

| What | File | Notes |
|------|------|-------|
| Flask app | `src/app.py` | Routes: `/`, `/chat`, `/health` |
| RAG pipeline | `src/rag_chain.py` | `ask(question)` is the main entry |
| Ingestion | `src/ingest.py` | `ingest_documents(force=bool)` |
| Config | `src/config.py` | All env vars with defaults |
| Guardrails | `src/guardrails.py` | `validate_input()`, `validate_output()` |
| Chat UI | `templates/index.html` + `static/chat.js` | Vanilla JS, no build step |
| Evaluation | `evaluation/run_evaluation.py` | Runs 25 questions, writes `eval_results.json` |
| CI/CD | `.github/workflows/ci-cd.yml` | install → import check → pytest → deploy webhook |
| Keep-warm | `.github/workflows/keep-warm.yml` | Cron every 10 min, pings `/health` |
| Render config | `render.yaml` | Build: pip install + ingest; Start: gunicorn |

## Config & Environment

All config lives in `src/config.py`, loaded from `.env` via `python-dotenv`:

| Variable | Default | Required |
|----------|---------|----------|
| `GROQ_API_KEY` | *(none)* | Yes (for /chat and eval) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | No |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | No |
| `CHROMA_PERSIST_DIR` | `chroma_db` | No |
| `CHUNK_SIZE` | `1000` | No |
| `CHUNK_OVERLAP` | `200` | No |
| `RETRIEVAL_K` | `5` | No |

## Corpus Details

10 markdown files in `docs/`, all for fictional "Acme Corp". Each has a `Policy ID:` header (e.g., `ACME-HR-001`). Documents cross-reference each other by policy ID. The evaluation questions map to specific documents via `expected_source` in `eval_questions.json`.

Key cross-references:
- PTO policy → Holiday Schedule (`ACME-HR-006`)
- Remote Work → Expense Policy (`ACME-FIN-001`) for travel reimbursement
- Remote Work → Info Security (`ACME-IT-001`) for device/VPN requirements
- Acceptable Use → Info Security (`ACME-IT-001`) and Code of Conduct (`ACME-HR-005`)
- Onboarding → references nearly all other policies

## Deployment (Render)

Follows the same pattern as `malware-detection-ml`:
- `render.yaml`: buildCommand runs `pip install` then ingestion; startCommand runs gunicorn
- GitHub secrets needed: `RENDER_DEPLOY_HOOK_URL`, `APP_HEALTH_URL`, `GROQ_API_KEY`
- Keep-warm pings `/health` every 10 min via GitHub Actions cron
- Single worker + 2 threads (free tier memory constraint)
- Embedding model downloads on first build (~80MB), cached in Render's build layer

## Testing Notes

- All 30 tests run without `GROQ_API_KEY` — they test guardrails, Flask routing, and ingestion only
- `test_ingest.py::test_load_and_chunk` downloads the embedding model on first run (~80MB), takes ~20s; subsequent runs ~5s
- No mocking of the LLM — integration tests for RAG quality are in `evaluation/run_evaluation.py`, not pytest
- CI runs `python -c "from src.app import app"` as an import smoke test before pytest
