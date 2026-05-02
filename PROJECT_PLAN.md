# Policy RAG Application — Project Plan
**Date:** 2026-05-02
**Author:** Mihai (with AdaL AI assistance)
**Goal:** Score 5/5 on Quantic MSSE AI Engineering Project rubric

---

## TL;DR
Build a production-quality RAG application over synthetic company policy documents using LangChain + HuggingFace embeddings + ChromaDB + Groq LLM, served via Flask, deployed on Render with CI/CD via GitHub Actions. Evaluate with 25 questions across 6 policy domains.

---

## 1. Corpus Strategy

### Source Documents (AI-generated synthetic policies)
Since no real employer policies are available, we will **generate a coherent set of synthetic company policy documents** for a fictional company called **"Acme Corp"**. This approach is explicitly permitted by the rubric ("author them yourself with AI assistance") and gives us full control over coverage and quality.

We will also incorporate content patterns from these open-source references:
- [OpenGov Foundation HR Manual](https://github.com/opengovfoundation/hr-manual) — CC-licensed, covers PTO, leave, expenses, conduct
- [Center for Open Science Policies](https://github.com/CenterForOpenScience/Policies-and-Procedures) — public domain, covers travel, data privacy, acceptable use

### Document Set (10 files, ~60-80 pages total)
| # | Filename | Topic | Format | ~Pages |
|---|----------|-------|--------|--------|
| 1 | `pto-and-leave-policy.md` | PTO, sick leave, FMLA, parental leave | Markdown | 6-8 |
| 2 | `remote-work-policy.md` | Remote/hybrid work, equipment, expectations | Markdown | 5-7 |
| 3 | `expense-reimbursement-policy.md` | Travel, meals, supplies, approval process | Markdown | 6-8 |
| 4 | `information-security-policy.md` | Data classification, passwords, devices, incident response | Markdown | 8-10 |
| 5 | `code-of-conduct.md` | Ethics, harassment, conflicts of interest, reporting | Markdown | 7-9 |
| 6 | `holiday-schedule.md` | Company holidays 2026, floating holidays, religious observance | Markdown | 3-4 |
| 7 | `benefits-overview.md` | Health, dental, vision, 401k, life insurance | Markdown | 6-8 |
| 8 | `onboarding-guide.md` | New hire checklist, first 90 days, tools & access | Markdown | 5-7 |
| 9 | `performance-review-policy.md` | Review cycles, ratings, PIPs, promotions | Markdown | 5-6 |
| 10 | `acceptable-use-policy.md` | Company systems, internet, email, social media | Markdown | 4-5 |

**Total: ~55-72 pages across 10 documents covering all 6 required evaluation domains**

---

## 2. Architecture & Tech Stack

```
┌─────────────────────────────────────────────────────┐
│                    Flask Web App                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │  / (UI)  │  │ /chat    │  │ /health           │  │
│  │  HTML +  │  │ POST API │  │ JSON status       │  │
│  │  JS chat │  │          │  │                   │  │
│  └────┬─────┘  └────┬─────┘  └───────────────────┘  │
│       │              │                                │
│       └──────┬───────┘                                │
│              ▼                                        │
│  ┌───────────────────────────────────────────┐       │
│  │         LangChain RAG Pipeline            │       │
│  │  ┌─────────────┐  ┌────────────────────┐  │       │
│  │  │ Retriever   │  │ Prompt Template    │  │       │
│  │  │ (ChromaDB   │  │ (citations +      │  │       │
│  │  │  + MMR/sim) │  │  guardrails)      │  │       │
│  │  └──────┬──────┘  └────────┬───────────┘  │       │
│  │         │                  │               │       │
│  │         ▼                  ▼               │       │
│  │  ┌─────────────┐  ┌────────────────────┐  │       │
│  │  │ ChromaDB    │  │ Groq LLM          │  │       │
│  │  │ (persistent)│  │ (llama-3.3-70b)   │  │       │
│  │  └─────────────┘  └────────────────────┘  │       │
│  │         ▲                                  │       │
│  │  ┌─────────────┐                          │       │
│  │  │ HuggingFace │                          │       │
│  │  │ Embeddings  │                          │       │
│  │  │ (MiniLM-L6) │                          │       │
│  │  └─────────────┘                          │       │
│  └───────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
```

### Key Technology Choices
| Component | Choice | Rationale |
|-----------|--------|-----------|
| **LLM** | Groq `llama-3.3-70b-versatile` | Free tier, fast inference (~6000 tokens/min), strong instruction following |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | Free, local, 384-dim, good for semantic search |
| **Vector Store** | ChromaDB (persistent, local) | Zero cost, no API key, LangChain native support |
| **Orchestration** | LangChain | Required by spec; handles retrieval chain, prompt templates |
| **Web Framework** | Flask | Lightweight, meets endpoint requirements |
| **Chunking** | Markdown header-based + recursive character (1000 tokens, 200 overlap) | Preserves document structure, good for policy docs |
| **Retrieval** | Top-k=5 with MMR diversity | Balance relevance and coverage |
| **Deployment** | Render free tier + gunicorn | Matches existing malware-detection-ml pattern |
| **CI/CD** | GitHub Actions | Build check + test + deploy webhook on push to main |

---

## 3. Folder Structure

```
policy-rag-app/
├── README.md                          # Setup & run instructions
├── requirements.txt                   # Pinned dependencies
├── render.yaml                        # Render deployment config
├── Procfile                           # gunicorn start command
├── .env.example                       # Template for env vars
├── .gitignore
│
├── docs/                              # Policy corpus (10 markdown files)
│   ├── pto-and-leave-policy.md
│   ├── remote-work-policy.md
│   ├── expense-reimbursement-policy.md
│   ├── information-security-policy.md
│   ├── code-of-conduct.md
│   ├── holiday-schedule.md
│   ├── benefits-overview.md
│   ├── onboarding-guide.md
│   ├── performance-review-policy.md
│   └── acceptable-use-policy.md
│
├── src/
│   ├── __init__.py
│   ├── app.py                         # Flask app (/, /chat, /health)
│   ├── config.py                      # Configuration & env vars
│   ├── ingest.py                      # Document loading, chunking, embedding
│   ├── rag_chain.py                   # LangChain RAG pipeline
│   └── guardrails.py                  # Input/output guardrails
│
├── templates/
│   └── index.html                     # Chat UI
│
├── static/
│   ├── style.css
│   └── chat.js
│
├── chroma_db/                         # Persistent vector store (gitignored)
│
├── tests/
│   ├── __init__.py
│   ├── test_ingest.py                 # Ingestion unit tests
│   ├── test_rag_chain.py             # RAG pipeline tests
│   ├── test_app.py                    # Flask endpoint tests
│   └── test_health.py                # Smoke test
│
├── evaluation/
│   ├── eval_questions.json            # 25 evaluation questions + gold answers
│   ├── run_evaluation.py             # Automated eval script
│   └── eval_results.json             # Output: metrics & per-question results
│
├── .github/
│   └── workflows/
│       ├── ci-cd.yml                  # Build + test + deploy on push/PR
│       └── keep-warm.yml             # Ping health endpoint every 10 min
│
├── design-and-evaluation.md           # Design choices & eval results
├── ai-tooling.md                      # AI tools usage description
└── deployed.md                        # Link to deployed app
```

---

## 4. Implementation Sequence

### Phase 1: Foundation (Steps 1-3)
1. **Initialize repo & dependencies** — Create git repo, `requirements.txt`, `.gitignore`, `.env.example`
2. **Generate corpus** — Write all 10 policy documents under `docs/`
3. **Build ingestion pipeline** — `src/ingest.py`: load markdown, chunk, embed, store in ChromaDB

### Phase 2: RAG Pipeline (Steps 4-5)
4. **Build RAG chain** — `src/rag_chain.py`: LangChain retrieval chain with Groq, citation extraction, prompt template
5. **Add guardrails** — `src/guardrails.py`: out-of-corpus detection, length limits, citation enforcement

### Phase 3: Web App (Steps 6-7)
6. **Flask app** — `src/app.py`: `/`, `/chat`, `/health` endpoints
7. **Chat UI** — `templates/index.html`, `static/`: clean, functional chat interface with citations

### Phase 4: Testing & CI/CD (Steps 8-9)
8. **Tests** — Unit tests for ingestion, RAG chain, Flask endpoints, health check
9. **GitHub Actions** — CI/CD pipeline (install + test + deploy) + keep-warm scheduler

### Phase 5: Deployment (Step 10)
10. **Render deployment** — `render.yaml`, gunicorn config, env vars, verify public URL

### Phase 6: Evaluation & Documentation (Steps 11-13)
11. **Evaluation** — 25 questions, compute groundedness %, citation accuracy %, p50/p95 latency
12. **Documentation** — `design-and-evaluation.md`, `ai-tooling.md`, `deployed.md`, `README.md`
13. **Demo script** — Full timed speaker notes for 5-10 min Tella video

---

## 5. Evaluation Plan

### Question Set (25 questions across 6 domains)
| Domain | # Questions | Example |
|--------|-------------|---------|
| PTO & Leave | 5 | "How many PTO days do new employees receive?" |
| Security | 4 | "What is the password complexity requirement?" |
| Expenses | 4 | "What is the per-meal reimbursement limit for business travel?" |
| Remote Work | 4 | "What equipment does Acme provide for remote workers?" |
| Holidays | 4 | "Is Juneteenth a company holiday?" |
| Cross-domain | 4 | "Can I expense a co-working space while working remotely?" |

### Metrics
| Metric | Type | Target |
|--------|------|--------|
| **Groundedness** | Quality | ≥ 90% |
| **Citation Accuracy** | Quality | ≥ 85% |
| **Latency p50** | System | < 3s |
| **Latency p95** | System | < 8s |

### Evaluation Method
- **Groundedness**: LLM-as-judge (Groq) checks if answer is fully supported by retrieved context
- **Citation Accuracy**: Automated check that cited doc IDs match the source of the answer content
- **Latency**: Timed end-to-end from request to response for all 25 questions

---

## 6. Key Dependencies (requirements.txt preview)

```
flask>=3.1,<4
gunicorn>=23.0,<24
langchain>=0.3,<0.4
langchain-community>=0.3,<0.4
langchain-groq>=0.2,<0.3
langchain-huggingface>=0.1,<0.2
chromadb>=0.5,<1.0
sentence-transformers>=3.0,<4
python-dotenv>=1.0,<2
pytest>=8.0,<9
```

---

## 7. Deployment Configuration

### render.yaml (mirrors malware-detection-ml pattern)
```yaml
services:
  - type: web
    name: policy-rag-app
    runtime: python
    buildCommand: pip install -r requirements.txt && python -c "from src.ingest import ingest_documents; ingest_documents()"
    startCommand: gunicorn src.app:app --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 30 --workers 1 --threads 2
    envVars:
      - key: PYTHON_VERSION
        value: "3.12.9"
      - key: GROQ_API_KEY
        fromSecret: GROQ_API_KEY
    plan: free
```

### GitHub Actions CI/CD (mirrors existing pattern)
- On push/PR to main: install deps → run pytest → deploy webhook
- Keep-warm: cron every 10 min pinging `/health`

---

## NEXT STEP AND MODEL RECOMMENDATION

### What was just completed:
- ✅ Read and analyzed the full project rubric (7-page PDF)
- ✅ Analyzed existing Render deployment pattern (render.yaml + CI/CD + keep-warm)
- ✅ Searched for and evaluated open-source policy document sources
- ✅ Confirmed Groq free tier availability (llama-3.3-70b-versatile)
- ✅ Created project folder at the specified location
- ✅ Produced comprehensive project plan with folder structure, architecture, and implementation sequence

### Next task:
**Phase 1, Steps 1-2**: Initialize the repository with all config files (`requirements.txt`, `.gitignore`, `.env.example`, `render.yaml`, `Procfile`) and generate all 10 synthetic policy documents for the `docs/` folder. This is the largest content-generation step (~60-80 pages of coherent policy text).

### Recommended model for next task:
**Claude Opus 4.6 (1M context)** or **GPT-5.5 (extended context)** — The next step requires generating ~60-80 pages of coherent, cross-referenced policy documents plus all repo config files. This is a large content generation task that benefits from extended context to maintain consistency across all 10 documents. Claude Opus 4.6 1M is ideal because it can hold the entire corpus in context while generating, ensuring cross-document consistency (e.g., PTO policy referencing the holiday schedule, expense policy referencing remote work equipment allowances).
