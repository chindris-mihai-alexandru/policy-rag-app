# Design and Evaluation — Acme Corp Policy RAG Application

## 1. Design and Architecture Decisions

### 1.1 Corpus Design

**Decision**: Generate 10 synthetic policy documents for a fictional company ("Acme Corp") rather than using real company policies.

**Why**: The rubric explicitly allows AI-authored synthetic policies. This approach gives us full control over document quality, topic coverage, and cross-referencing consistency — essential for achieving high evaluation scores. Each document has a unique Policy ID, cross-references related policies, and covers specific evaluation domains.

**Corpus coverage**: PTO & Leave, Remote Work, Expenses, Information Security, Code of Conduct, Holidays, Benefits, Onboarding, Performance Reviews, Acceptable Use — totaling ~2,500 lines across 10 markdown files.

### 1.2 Embedding Model

**Decision**: `sentence-transformers/all-MiniLM-L6-v2` (local, free)

**Why**: This model is lightweight (80MB), runs locally without API keys, produces 384-dimensional embeddings, and has strong performance on semantic similarity benchmarks. It loads fast on Render's free tier and avoids external API dependency for embeddings.

**Alternatives considered**:
- Cohere Embed v3 (free tier): Better quality but adds API dependency and rate limits
- all-mpnet-base-v2: Higher quality but 2x model size, slower on free tier

### 1.3 Chunking Strategy

**Decision**: Two-pass chunking — Markdown header splitting first, then recursive character splitting (1000 chars, 200 overlap).

**Why**: Policy documents have natural heading structure. Splitting by headers preserves semantic coherence of sections (e.g., "Section 4.1 Air Travel" stays together). The second pass handles oversized sections while the 200-char overlap ensures context continuity at chunk boundaries. This produced 267 chunks from 10 documents.

**Alternatives considered**:
- Token-based splitting only: Loses heading context and may split mid-section
- Smaller chunks (500 chars): More chunks = noisier retrieval results
- Larger chunks (2000 chars): Risk exceeding LLM context with 5 retrieved chunks

### 1.4 Vector Store

**Decision**: ChromaDB (persistent, local)

**Why**: Zero cost, no API key, native LangChain support, persistent storage (survives restarts on Render), and the corpus is small enough (~267 chunks) that local vector search is instant. The corpus hash mechanism avoids re-ingestion on every deployment.

**Alternatives considered**:
- Pinecone: Better for large-scale, but adds API dependency and free tier limits
- FAISS: Fast but no built-in persistence; requires manual serialization

### 1.5 LLM

**Decision**: Groq `llama-3.3-70b-versatile` (free tier)

**Why**: Groq provides extremely fast inference (~150 tokens/sec) on the free tier. The 70B parameter Llama 3.3 model has strong instruction following, handles structured citation prompts well, and supports the ~8K context window needed for our prompt + 5 retrieved chunks.

**Alternatives considered**:
- OpenRouter free models: Unreliable availability, rate limit changes
- Local Ollama: Not feasible on Render free tier (insufficient RAM)
- Groq Llama 4 Scout: Newer but less tested for instruction-following RAG tasks

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

**Decision**: Render free tier with gunicorn, following the same pattern as the malware-detection-ml project.

**Why**: Proven deployment pattern, zero cost, easy CI/CD integration. The keep-warm cron job prevents the Render free tier from spinning down.

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

*(To be populated after running `python evaluation/run_evaluation.py`)*

| Metric | Target | Actual |
|--------|--------|--------|
| Groundedness | ≥ 90% | TBD |
| Citation Accuracy | ≥ 85% | TBD |
| Latency p50 | < 3s | TBD |
| Latency p95 | < 8s | TBD |

### Per-Domain Breakdown

| Domain | Questions | Groundedness | Citation Accuracy |
|--------|-----------|-------------|------------------|
| PTO & Leave | 5 | TBD | TBD |
| Security | 4 | TBD | TBD |
| Expenses | 4 | TBD | TBD |
| Remote Work | 4 | TBD | TBD |
| Holidays | 4 | TBD | TBD |
| Cross-domain | 4 | TBD | TBD |

---

## 3. Technology Stack Summary

| Component | Choice | Rationale |
|-----------|--------|-----------|
| LLM | Groq llama-3.3-70b-versatile | Free, fast, strong instruction following |
| Embeddings | all-MiniLM-L6-v2 | Free, local, lightweight, good quality |
| Vector Store | ChromaDB | Free, persistent, LangChain native |
| Orchestration | LangChain | Required by spec; handles retrieval chain |
| Web Framework | Flask | Lightweight, meets endpoint requirements |
| Chunking | Markdown headers + recursive (1000/200) | Preserves document structure |
| Retrieval | Top-k=5 similarity | Good coverage-to-noise balance |
| Deployment | Render free tier + gunicorn | Proven pattern, zero cost |
| CI/CD | GitHub Actions | Build + test + deploy on push |
