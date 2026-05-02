# Demo Speaker Script — Acme Corp Policy RAG App
**Duration**: 5–10 minutes | **POC**: Mihai Chindris | **Date**: 2026-05-02

---

## 🎬 Opening (30 sec)

> "Hi, I'm Mihai. I built a Retrieval-Augmented Generation application that lets employees ask plain-English questions about company HR policies and get accurate, cited answers — powered by a real LLM but grounded in a curated policy corpus."

---

## 1. Problem Statement (1 min)

> "Employees waste time hunting through dense HR policy PDFs for simple answers. Existing solutions either hallucinate or require expensive enterprise search platforms. My goal was to build a RAG chatbot that's accurate, citable, and runs on free-tier infrastructure."

---

## 2. Architecture Walkthrough (2 min)

> "The stack is intentionally lean:"

- **Corpus**: 17 documents — 10 synthetic Acme Corp policies I authored, plus 7 real open-source documents: Basecamp's employee handbook and 3 real public PDF handbooks from Public Counsel, Beach Haven NJ, and JIAN.
- **Embeddings**: HuggingFace `all-MiniLM-L6-v2` runs locally — no external embedding API, no cost.
- **Vector Store**: ChromaDB — in-memory at runtime, re-ingests from docs on startup.
- **LLM**: Groq's `llama-3.3-70b-versatile` — fast inference, free tier.
- **Framework**: LangChain for the RAG chain, Flask for the API, plain HTML/JS for the frontend.
- **Deployment**: Render free tier, GitHub Actions for CI/CD and keep-warm pings.

---

## 3. Live Demo (3 min)

*Open https://policy-rag-app-v2td.onrender.com*

**Ask these 3 questions in order:**

### Q1 — Simple factual lookup:
> Type: *"How many PTO days do new employees receive?"*

Point out:
- Answer cites `[pto-and-leave-policy]` inline
- Correct answer: 15 days for 0-2 year tenure

### Q2 — Security policy:
> Type: *"Is SMS-based two-factor authentication allowed?"*

Point out:
- Answer says "No" with the reason (SIM-swap vulnerabilities)
- Cites `[information-security-policy]`

### Q3 — Cross-domain query:
> Type: *"What is the 401k company match and when am I eligible for remote work?"*

Point out:
- Synthesises across two documents: `[benefits-overview]` and `[remote-work-policy]`
- Demonstrates multi-doc retrieval in a single answer

### Q4 — Out-of-scope guardrail:
> Type: *"Write me a Python script to scrape LinkedIn"*

Point out:
- Guardrail fires — app politely declines out-of-scope requests
- This is an input validation layer in `guardrails.py`

---

## 4. Evaluation Results (1 min)

> "I ran an automated 25-question evaluation suite using Groq itself as the LLM judge:"

| Metric | Result |
|--------|--------|
| Groundedness | 84% |
| Citation Accuracy | 88% |
| Latency p50 | 5.6s |
| Latency p95 | 7.0s |
| Successful queries | 25/25 |

> "Groundedness measures whether every claim in the answer is supported by the retrieved context. Citation accuracy measures whether the correct source document was cited. Both metrics are automated — no manual labelling required."

---

## 5. Key Design Decisions (1 min)

> "Three decisions I'd highlight:"

1. **Real public corpus** — I used actual open-source employee handbooks alongside synthetic policies, giving the retriever realistic noise to navigate.
2. **LLM-as-judge** — Using the same Groq model to evaluate groundedness is efficient and reproducible without a separate annotation pipeline.
3. **Free-tier-first** — Every component (embeddings, vector store, LLM, hosting) runs at zero cost, which matters for maintainability.

---

## 6. Closing (30 sec)

> "The repo is at github.com/chindris-mihai-alexandru/policy-rag-app — it has full CI/CD, 30 passing tests, and design documentation. Happy to take questions."

---

*Tips: Keep the browser tab open before presenting. The app cold-starts in ~30s after inactivity — ping it once before your demo by visiting the URL.*
