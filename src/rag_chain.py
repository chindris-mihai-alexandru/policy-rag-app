"""Acme Corp Policy RAG — Retrieval-Augmented Generation chain.

Uses LangChain with ChromaDB retriever and OpenRouter LLM to answer
policy questions with citations.
"""

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings

from src.config import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL,
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
1. Answer ONLY using information from the provided context passages. Do not use \
outside knowledge.
2. If the context does not contain enough information to answer the question, say: \
"I don't have enough information in our policy documents to answer that question. \
Please contact HR at hr@acmecorp.com or extension x4500 for further assistance."
3. ALWAYS cite your sources using the document name in square brackets, e.g., \
[pto-and-leave-policy]. Cite every document you reference.
4. Keep answers concise and well-structured. Use bullet points or numbered lists \
when appropriate.
5. If a question is unrelated to Acme Corp policies (e.g., general knowledge, \
personal advice, coding help), respond: "I can only answer questions about Acme \
Corp company policies and procedures. Please rephrase your question or contact \
HR for other inquiries."
6. Never fabricate policy details. If unsure, direct the employee to HR.
7. When quoting specific numbers (days, dollars, percentages), always cite the \
exact source document.
"""

HUMAN_PROMPT = """\
Context passages from Acme Corp policy documents:
{context}

---

Employee question: {question}

Provide a helpful, accurate answer with citations to the source documents."""


# Module-level singletons — loaded once at worker boot, not per-request
_embeddings: HuggingFaceEmbeddings | None = None
_llm: ChatOpenAI | None = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Return the HuggingFace embedding model (singleton)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
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
    """Return a ChromaDB collection handle."""
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
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
    for i, chunk in enumerate(retrieved_chunks, 1):
        source = chunk["source"]
        text = chunk["text"]
        parts.append(f"[Source {i}: {source}]\n{text}")
    return "\n\n---\n\n".join(parts)


def warm_up():
    """Pre-load the embedding model and LLM at startup to avoid first-request latency."""
    _get_embeddings()
    _get_llm()


def ask(question: str) -> dict:
    """Answer a policy question using RAG.

    Args:
        question: The employee's question about Acme Corp policies.

    Returns:
        dict with 'answer', 'sources', and 'chunks' keys.
    """
    retrieved = _retrieve_context(question)

    if not retrieved:
        return {
            "answer": (
                "I don't have enough information in our policy documents "
                "to answer that question. Please contact HR at "
                "hr@acmecorp.com or extension x4500 for further assistance."
            ),
            "sources": [],
            "chunks": [],
        }

    context_str = _format_context(retrieved)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ]
    )

    llm = _get_llm()
    chain = prompt | llm
    response = chain.invoke({"context": context_str, "question": question})

    sources = list(dict.fromkeys(chunk["source"] for chunk in retrieved))

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

    return {
        "answer": response.content,
        "sources": source_snippets,
        "chunks": [
            {
                "text": c["text"],
                "source": c["source"],
                "distance": c["distance"],
            }
            for c in retrieved
        ],
    }
