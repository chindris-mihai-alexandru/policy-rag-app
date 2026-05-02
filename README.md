# 🏢 Acme Corp Policy RAG Application

A production-quality Retrieval-Augmented Generation (RAG) application that answers employee questions about company policies and procedures. Built for the Quantic MSSE AI Engineering Project.

## 🎯 Features

- **RAG Pipeline**: LangChain + ChromaDB + Groq LLM for accurate, cited answers
- **10 Policy Documents**: Comprehensive synthetic corpus covering PTO, remote work, expenses, security, benefits, holidays, and more
- **Citation System**: Every answer includes source document references and snippets
- **Guardrails**: Refuses off-topic questions, validates input/output, enforces citation requirements
- **Web Chat UI**: Clean, responsive chat interface with real-time responses
- **REST API**: `/chat` endpoint for programmatic access
- **Evaluation Suite**: 25 questions with automated groundedness and citation accuracy metrics
- **CI/CD**: GitHub Actions for testing and deployment
- **Deployment**: Render free tier with keep-warm scheduler

## 🏗️ Architecture

```
User → Flask Web App → LangChain RAG Pipeline → Answer + Citations
                            ├── ChromaDB (vector store, local)
                            ├── HuggingFace Embeddings (all-MiniLM-L6-v2)
                            └── Groq LLM (llama-3.3-70b-versatile)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- A free [Groq API key](https://console.groq.com)

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
# Edit .env and add your GROQ_API_KEY

# Ingest documents into ChromaDB
python -c "from src.ingest import ingest_documents; print(ingest_documents(force=True))"

# Run the app
python -m src.app
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
# Run the evaluation suite (requires GROQ_API_KEY)
python evaluation/run_evaluation.py
```

Results are saved to `evaluation/eval_results.json`.

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | Groq (llama-3.3-70b-versatile) |
| Embeddings | HuggingFace (all-MiniLM-L6-v2) |
| Vector Store | ChromaDB (persistent, local) |
| Orchestration | LangChain |
| Web Framework | Flask |
| Deployment | Render (free tier) |
| CI/CD | GitHub Actions |

## 📄 License

This project was created for educational purposes as part of the Quantic MSSE AI Engineering curriculum.
