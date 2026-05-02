# Design and Evaluation — Acme Corp Policy RAG Application

## 1. Design and Architecture Decisions

### 1.1 Corpus Design

**Decision**: Generate 10 synthetic policy documents for a fictional company ("Acme Corp") rather than using real company policies.

**Why**: The rubric explicitly allows AI-authored synthetic policies. This approach gives us full control over document quality, topic coverage, and cross-referencing consistency — essential for achieving high evaluation scores. Each document has a unique Policy ID, cross-references related policies, and covers specific evaluation domains.

**Corpus coverage**: PTO & Leave, Remote Work, Expenses, Information Security, Code of Conduct, Holidays, Benefits, Onboarding, Performance Reviews, Acceptable Use — totaling ~2,500 lines across 10 markdown files.

### 1.2 Embedding Model

**Decision**: `BAAI/bge-small-en-v1.5` via [FastEmbed](https://github.com/qdrant/fastembed) (local, free)

**Why**: FastEmbed is a lightweight, ONNX-optimized embedding library purpose-built for production inference. `bge-small-en-v1.5` (133MB) produces 384-dimensional embeddings and consistently outperforms MiniLM-L6 on MTEB retrieval benchmarks while remaining fast enough for build-time ingestion on DigitalOcean. It runs entirely locally — no API key required — and the model files are cached to `models_cache/` during the DO build phase to avoid re-downloading at startup.

**Alternatives considered**:
- `all-MiniLM-L6-v2` (sentence-transformers): Slightly smaller but lower retrieval accuracy on MTEB; also requires `torch` which is heavier than the FastEmbed ONNX stack
- Cohere Embed v3: Better quality but adds API dependency and rate limits
- OpenAI `text-embedding-3-small`: High quality but adds per-token cost and external API dependency

### 1.3 Chunking Strategy

**Decision**: Recursive character splitting (1000 chars, 200 overlap) applied to PDF-extracted text.

**Why**: The corpus is PDF-only (11 files). `pypdf` extracts plain text, so Markdown header splitting is not applicable. `RecursiveCharacterTextSplitter` with 1000-char chunks and 200-char overlap balances retrieval precision (chunks small enough to be specific) with context continuity (overlap prevents losing cross-sentence context at boundaries). The 200-char overlap ensures that key facts near a chunk boundary appear in both adjacent chunks.

**Alternatives considered**:
- Smaller chunks (500 chars): More granular but noisier retrieval; increases chunk count and retrieval latency
- Larger chunks (2000 chars): Risk saturating LLM context when 5 chunks are concatenated into the prompt
- Semantic chunking: More accurate but requires a heavier NLP pipeline; unnecessary for short, structured policy documents

### 1.4 Vector Store

**Decision**: ChromaDB (persistent, local)

**Why**: Zero cost, no API key, native LangChain support, persistent storage (survives restarts on Render), and the corpus is small enough (~267 chunks) that local vector search is instant. The corpus hash mechanism avoids re-ingestion on every deployment.

**Alternatives considered**:
- Pinecone: Better for large-scale, but adds API dependency and free tier limits
- FAISS: Fast but no built-in persistence; requires manual serialization

### 1.5 LLM

**Decision**: OpenRouter `openai/gpt-oss-20b:free`

**Why**: OpenRouter provides a unified API gateway over dozens of hosted models with a single API key. The `gpt-oss-20b:free` model (GPT-4o Mini class) has strong instruction-following, reliably formats bracket citations, and is available on the free tier with no per-token cost. Routing through OpenRouter decouples the app from any single provider — swapping models is a single `OPENROUTER_MODEL` env var change without code changes.

**Alternatives considered**:
- Groq `llama-3.3-70b-versatile`: Very fast but Groq's free tier has strict rate limits that caused failures during automated 25-question evaluation runs
- Local Ollama: Not feasible on DigitalOcean basic-xxs (insufficient RAM for 7B+ models)
- OpenRouter `google/gemini-flash-1.5`: Good quality but inconsistent citation bracket formatting in early testing

### 1.6 Retrieval Strategy

**Decision**: Top-k=5 with embedding similarity search.

**Why**: k=5 provides good coverage without overwhelming the LLM context. Our testing shows that relevant answers typically appear in the top 3 results, with positions 4-5 providing supporting context from related policies. The 384-dim MiniLM embeddings provide effective semantic matching for policy questions.

### 1.7 Prompt Engineering

**Decision**: System prompt with explicit rules for citation format, out-of-scope handling, and factual grounding.

**Why**: The system prompt enforces 7 rules that directly map to evaluation criteria:
1. Answer only from context (→ groundedness)
2. Explicit fallback message for missing info (→ graceful degradation)
3. Always cite sources in `[doc-name]` format (→ citation accuracy)
4. Concise, structured answers (→ readability)
5. Refuse off-topic questions (→ guardrails)
6. Never fabricate (→ groundedness)
7. Cite numbers explicitly (→ citation accuracy)

### 1.8 Guardrails

**Decision**: Two-layer guardrails — input validation (regex patterns for off-topic detection, length limits) and output validation (citation checking, length truncation).

**Why**: Input guardrails catch obvious off-topic questions before they hit the LLM (saving API calls). Output guardrails ensure every response either contains citations or is a recognized out-of-scope message. This prevents the LLM from occasionally "forgetting" to cite sources.

### 1.9 Web Application

**Decision**: Flask with a clean chat UI (vanilla HTML/CSS/JS).

**Why**: Flask is lightweight and meets the endpoint requirements (/, /chat, /health). The chat UI uses vanilla JavaScript without React/Vue to minimize bundle size and deployment complexity on the free tier. The interface shows source documents and response latency for transparency.

### 1.10 Deployment

**Decision**: DigitalOcean App Platform (basic-xxs) with Gunicorn.

**Why**: DigitalOcean App Platform offers a persistent build layer (no re-ingestion cold-start penalty), a reliable always-on runtime, and was fully covered by the $200 Quantic student credit. The build command pre-warms the FastEmbed model and ingests all PDFs into ChromaDB once, so runtime startup is fast. Auto-deploy from GitHub `main` via the DO GitHub App integration provides seamless CI/CD.

**Migration from Render**: The app was initially deployed on Render free tier but encountered OOM crashes during runtime ChromaDB ingestion (free tier limit ~512MB). DigitalOcean's build phase has more headroom, and the persistent disk avoids re-ingesting on every restart. The Render service has been deleted.

---

## 2. Evaluation Approach

### 2.1 Evaluation Set

25 questions across 6 domains:
- **PTO & Leave** (5 questions): Accrual rates, carryover, parental leave, sick days, advance notice
- **Security** (4 questions): Password requirements, MFA, device reporting, encryption standards
- **Expenses** (4 questions): Meal limits, hotel rates, submission deadlines, professional development
- **Remote Work** (4 questions): Core hours, equipment, internet stipend, co-working space policy
- **Holidays** (4 questions): Juneteenth, floating holidays, year-end closure, holiday pay
- **Cross-domain** (4 questions): 401(k) match, onboarding-to-remote timeline, gift limits, approved AI tools

Each question has an expected answer and expected source document for automated evaluation.

### 2.2 Metrics

| Metric | Definition | Method |
|--------|-----------|--------|
| **Groundedness** | % of answers whose content is factually supported by retrieved context | LLM-as-judge (Groq llama-3.3-70b) evaluates each answer against its retrieved context chunks |
| **Citation Accuracy** | % of answers that correctly cite the expected source document | Automated regex check for `[expected-source]` in the answer |
| **Latency p50** | Median end-to-end response time | Timed from question submission to answer return |
| **Latency p95** | 95th percentile response time | Sorted latency array, index at 95% |

### 2.3 Evaluation Results

*Results from automated evaluation run on 2026-05-02 against 25 questions using OpenRouter `openai/gpt-oss-20b:free` as both the RAG LLM and the LLM-as-judge. Corpus: 10 synthetic Acme PDFs + 1 real public handbook PDF (111 pages total).*

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Groundedness | ≥ 90% | **100.0%** | ✅ Exceeded |
| Citation Accuracy | ≥ 85% | **92.0%** | ✅ Exceeded |
| Latency p50 | < 6s | **4,751ms** | ✅ Met |
| Latency p95 | < 10s | **9,477ms** | ✅ Met |
| Latency mean | — | **5,175ms** | ✅ |
| Successful queries | 25/25 | **100%** | ✅ Met |

### Per-Domain Breakdown

| Domain | Questions | Groundedness | Citation Accuracy |
|--------|-----------|-------------|------------------|
| PTO & Leave | 5 | 100.0% | 80.0% |
| Security | 4 | 100.0% | 100.0% |
| Expenses | 4 | 100.0% | 100.0% |
| Remote Work | 4 | 100.0% | 100.0% |
| Holidays | 4 | 100.0% | 100.0% |
| Cross-domain | 4 | 100.0% | 75.0% |

---

## 3. Technology Stack Summary

| Component | Choice | Rationale |
|-----------|--------|-----------|
| LLM | OpenRouter `openai/gpt-oss-20b:free` | Free, provider-agnostic, reliable citation formatting |
| Embeddings | FastEmbed `BAAI/bge-small-en-v1.5` | Free, local ONNX-optimized, strong MTEB retrieval scores |
| Vector Store | ChromaDB v0.6.3 | Free, persistent, LangChain native |
| Orchestration | LangChain | Required by spec; handles retrieval chain |
| Web Framework | Flask (SSE streaming) | Lightweight, real-time token streaming via Server-Sent Events |
| Chunking | Recursive character (1000/200) | Good precision-to-noise balance for PDF corpus |
| Retrieval | Top-k=5 similarity | Good coverage-to-noise balance |
| Deployment | DigitalOcean App Platform + Gunicorn | Persistent build layer, always-on, $200 student credit |
| CI/CD | GitHub Actions + DO GitHub App | Tests on push; auto-deploy to DO on merge to main |
