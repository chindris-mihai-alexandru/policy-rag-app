"""Acme Corp Policy RAG — Configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=str(Path(__file__).resolve().parent.parent / ".env"), override=True)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
CHROMA_PERSIST_DIR = str(BASE_DIR / os.getenv("CHROMA_PERSIST_DIR", "chroma_db"))

# Embedding model
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Groq LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Retrieval
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "5"))

# Collection name
CHROMA_COLLECTION = "acme_policies"

# Guardrails
MAX_OUTPUT_TOKENS = 1024
