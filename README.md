# 🏢 Acme Corp Policy RAG Application

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?logo=langchain&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.6.3-FF6B35)
![OpenRouter](https://img.shields.io/badge/OpenRouter-gpt--oss--20b-6366F1)
![FastEmbed](https://img.shields.io/badge/FastEmbed-BAAI%2Fbge--small-00B4D8)
![CI](https://img.shields.io/badge/CI-passing-brightgreen?logo=githubactions&logoColor=white)
![License](https://img.shields.io/badge/License-Educational-lightgrey)

A production-quality Retrieval-Augmented Generation (RAG) application that answers employee questions about company policies and procedures. Built for the Quantic MSSE AI Engineering Project.

## 🎯 Features

- **RAG Pipeline**: LangChain + ChromaDB + OpenRouter LLM for accurate, cited answers
- **11 Policy Documents**: Corpus of 10 synthetic Acme Corp policies + 1 real public handbook (~111 pages total)
- **Citation System**: Every answer includes source document references with clickable links to the source PDFs
- **Guardrails**: Refuses off-topic questions, validates input/output, enforces citation requirements
- **Web Chat UI**: Full-width responsive chat interface with real-time streaming (Server-Sent Events)
- **REST API**: `/chat` endpoint (SSE streaming), `/health` and `/healthz` for status checks
- **Evaluation Suite**: 25 questions with automated groundedness (100%) and citation accuracy (92%) metrics
- **CI/CD**: GitHub Actions for testing; DigitalOcean App Platform auto-deploys on push to `main`
- **Deployment**: DigitalOcean App Platform — live at https://sea-turtle-app-gnq2r.ondigitalocean.app

## 🏗️ Architecture

```
User → Flask Web App (SSE) → LangChain RAG Pipeline → Streamed Answer + Citations
                                  ├── ChromaDB v0.6.3 (persistent vector store)
                                  ├── FastEmbed BAAI/bge-small-en-v1.5 (local ONNX embeddings)
                                  └── OpenRouter → gpt-oss-20b:free (LLM)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- A free [OpenRouter API key](https://openrouter.ai)

### Setup

```bash
# Clone the repo
git clone https://github.com/chindris-mihai-alexandru/policy-rag-app.git
cd policy-rag-app

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# Ingest documents into ChromaDB
python3 -c "from src.ingest import ingest_documents; print(ingest_documents(force=True))"

# Run the app
python3 -m src.app
```

Visit [http://localhost:5000](http://localhost:5000) to use the chat interface.

### API Usage

```bash
# Health check
curl http://localhost:5000/health

# Ask a question
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How many PTO days do new employees get?"}'
```

## 📁 Project Structure

```
policy-rag-app/
├── docs/                    # 10 policy documents (Acme Corp)
├── src/
│   ├── app.py              # Flask web app (/, /chat, /health)
│   ├── config.py           # Configuration & env vars
│   ├── ingest.py           # Document loading, chunking, embedding
│   ├── rag_chain.py        # LangChain RAG pipeline
│   └── guardrails.py       # Input/output validation
├── templates/index.html     # Chat UI
├── static/                  # CSS & JavaScript
├── tests/                   # 30 test cases
├── evaluation/              # 25-question eval suite
├── .github/workflows/       # CI/CD + keep-warm
├── design-and-evaluation.md # Design choices & eval results
├── ai-tooling.md           # AI tools usage
└── deployed.md             # Deployed URL
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_health.py -v      # Smoke test
python -m pytest tests/test_app.py -v          # Endpoint tests
python -m pytest tests/test_guardrails.py -v   # Guardrail tests
python -m pytest tests/test_ingest.py -v       # Ingestion tests
```

## 📊 Evaluation

```bash
# Run the evaluation suite (requires OPENROUTER_API_KEY)
python3 evaluation/run_evaluation.py
```

Results are saved to `evaluation/eval_results.json`.

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | OpenRouter `gpt-oss-20b:free` |
| Embeddings | FastEmbed `BAAI/bge-small-en-v1.5` (local ONNX) |
| Vector Store | ChromaDB v0.6.3 (persistent, local) |
| Orchestration | LangChain |
| Web Framework | Flask (SSE streaming) |
| Deployment | DigitalOcean App Platform |
| CI/CD | GitHub Actions + DO GitHub App |

## 📄 License

This project was created for educational purposes as part of the Quantic MSSE AI Engineering curriculum.
