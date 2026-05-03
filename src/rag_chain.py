"""Acme Corp Policy RAG — Retrieval-Augmented Generation chain.

Uses LangChain with ChromaDB retriever and OpenRouter LLM to answer
policy questions with citations.
"""

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import FastEmbedEmbeddings

from src.config import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL,
    FASTEMBED_CACHE_DIR,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    MAX_OUTPUT_TOKENS,
    RETRIEVAL_K,
)

# System prompt with guardrails baked in
SYSTEM_PROMPT = """\
You are the Acme Corp Policy Assistant. Your role is to answer employee questions \
about company policies and procedures based ONLY on the provided context from \
official Acme Corp policy documents.

RULES:
1. Answer ONLY using information from the provided context passages. Do not use outside knowledge.
2. If the context does not contain enough information to answer the question, say: "I don't have enough information in our policy documents to answer that question. Please contact HR at hr@acmecorp.com or extension x4500 for further assistance."
3. ALWAYS cite your sources inline using the exact document name in standard ASCII square brackets, e.g., [pto-and-leave-policy]. Do NOT use "Source 1", full-width brackets like "【...】", or any other numbering format.
4. Keep answers concise and well-structured. Use bullet points or numbered lists when appropriate.
5. If a question is unrelated to Acme Corp policies, respond: "I can only answer questions about Acme Corp company policies and procedures. Please rephrase your question or contact HR for other inquiries."
6. Never fabricate policy details. If unsure, direct the employee to HR.
7. When quoting specific numbers, always cite the exact source document.
"""

HUMAN_PROMPT = """\
Context passages from Acme Corp policy documents:
{context}

---

Employee question: {question}

Provide a helpful, accurate answer with citations to the source documents."""


# Module-level singletons — loaded once at worker boot, not per-request
_embeddings: FastEmbedEmbeddings | None = None
_llm: ChatOpenAI | None = None


def _get_embeddings() -> FastEmbedEmbeddings:
    """Return the FastEmbed embedding model (singleton, ONNX-based, no torch)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = FastEmbedEmbeddings(model_name=EMBEDDING_MODEL, cache_dir=FASTEMBED_CACHE_DIR)
    return _embeddings


def _get_llm() -> ChatOpenAI:
    """Return the OpenRouter LLM instance (singleton)."""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            model=OPENROUTER_MODEL,
            temperature=0.1,
            max_tokens=MAX_OUTPUT_TOKENS,
            default_headers={
                "HTTP-Referer": "https://github.com/chindris-mihai-alexandru/policy-rag-app",
                "X-Title": "Acme Corp Policy RAG",
            },
        )
    return _llm


def _get_chroma_collection():
    """Return a ChromaDB collection handle, triggering ingest if missing."""
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    # chromadb v0.6.0: list_collections() returns collection names (strings) directly
    existing = list(client.list_collections())
    if CHROMA_COLLECTION not in existing:
        # Build-time DB didn't persist (ephemeral FS) — ingest on demand
        print(f"[rag_chain] collection '{CHROMA_COLLECTION}' not found — triggering ingest...")
        from src.ingest import ingest_documents
        result = ingest_documents(force=True)
        print(f"[rag_chain] on-demand ingest: {result}")
    return client.get_collection(CHROMA_COLLECTION)


def _retrieve_context(question: str, k: int = None) -> list[dict]:
    """Retrieve relevant chunks from ChromaDB."""
    if k is None:
        k = RETRIEVAL_K

    embeddings = _get_embeddings()
    query_embedding = embeddings.embed_query(question)

    collection = _get_chroma_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    retrieved = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            retrieved.append(
                {
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "file": meta.get("file", "unknown"),
                    "metadata": meta,
                    "distance": dist,
                }
            )

    return retrieved


def _format_context(retrieved_chunks: list[dict]) -> str:
    """Format retrieved chunks into a context string for the prompt."""
    parts = []
    for chunk in retrieved_chunks:
        source = chunk["source"]
        text = chunk["text"]
        parts.append(f"Document Name: [{source}]\n{text}")
    return "\n\n---\n\n".join(parts)


def warm_up():
    """Pre-load the embedding model and LLM at startup to avoid first-request latency."""
    _get_embeddings()
    _get_llm()


import json

def ask_stream(question: str):
    """Answer a policy question using RAG (streaming).

    Args:
        question: The employee's question about Acme Corp policies.

    Yields:
        JSON strings formatted for Server-Sent Events (SSE).
    """
    try:
        retrieved = _retrieve_context(question)

        if not retrieved:
            yield f"data: {json.dumps({'chunk': 'I don\'t have enough information in our policy documents to answer that question. Please contact HR at hr@acmecorp.com or extension x4500 for further assistance.'})}\n\n"
            yield f"data: {json.dumps({'sources': [], 'done': True})}\n\n"
            return

        context_str = _format_context(retrieved)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", HUMAN_PROMPT),
            ]
        )

        llm = _get_llm()
        chain = prompt | llm
        
        # Prepare sources IMMEDIATELY to send to the UI first
        source_snippets = []
        seen_sources = set()
        for chunk in retrieved:
            src = chunk["source"]
            if src not in seen_sources:
                seen_sources.add(src)
                source_snippets.append(
                    {
                        "doc_id": src,
                        "file": chunk["file"],
                        "snippet": chunk["text"][:200] + "..."
                        if len(chunk["text"]) > 200
                        else chunk["text"],
                    }
                )

        # Yield sources FIRST so the UI can render chips and prep dynamic linking instantly
        yield f"data: {json.dumps({'type': 'sources', 'sources': source_snippets})}\n\n"

        # Stream the chunks
        full_answer = ""
        for chunk in chain.stream({"context": context_str, "question": question}):
            if chunk.content:
                full_answer += chunk.content
                yield f"data: {json.dumps({'chunk': chunk.content})}\n\n"

        # Optional: Apply output guardrails to the full answer
        from src.guardrails import validate_output
        validated = validate_output(full_answer)
        if validated != full_answer and len(validated) > len(full_answer):
            # Guardrail added a note, send it as a final chunk
            added_text = validated[len(full_answer):]
            yield f"data: {json.dumps({'chunk': added_text})}\n\n"

        # Yield final metadata
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
