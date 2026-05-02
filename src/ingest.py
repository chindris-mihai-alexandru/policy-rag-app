"""Acme Corp Policy RAG — Document ingestion pipeline.

Loads markdown policy documents, chunks them, embeds with HuggingFace,
and stores in ChromaDB.
"""

import hashlib
import os
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import FastEmbedEmbeddings
from src.config import FASTEMBED_CACHE_DIR
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from src.config import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DOCS_DIR,
    EMBEDDING_MODEL,
)


def _get_embeddings() -> FastEmbedEmbeddings:
    """Return the FastEmbed embedding model (ONNX-based, no torch)."""
    return FastEmbedEmbeddings(model_name=EMBEDDING_MODEL, cache_dir=FASTEMBED_CACHE_DIR)


def _get_chroma_client():
    """Return a persistent ChromaDB client."""
    import chromadb

    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def _compute_corpus_hash() -> str:
    """Compute a hash of all doc files to detect changes."""
    h = hashlib.sha256()
    for pattern in ("*.md", "*.pdf", "*.txt"):
        for fpath in sorted(Path(DOCS_DIR).glob(pattern)):
            h.update(fpath.read_bytes())
    return h.hexdigest()[:16]


def _load_and_chunk_documents():
    """Load markdown docs and split into chunks with metadata."""
    # Markdown header-based splitting first
    headers_to_split = [
        ("#", "heading_1"),
        ("##", "heading_2"),
        ("###", "heading_3"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split,
        strip_headers=False,
    )

    # Then recursive character splitting for size control
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    all_chunks = []

    for fpath in sorted(Path(DOCS_DIR).glob("*.md")):
        content = fpath.read_text(encoding="utf-8")
        doc_id = fpath.stem

        # First pass: split by markdown headers
        header_splits = md_splitter.split_text(content)

        # Second pass: split large sections into smaller chunks
        for doc in header_splits:
            sub_chunks = text_splitter.split_text(doc.page_content)
            for i, chunk_text in enumerate(sub_chunks):
                metadata = {
                    "source": doc_id,
                    "file": fpath.name,
                    **doc.metadata,
                }
                all_chunks.append({"text": chunk_text, "metadata": metadata})

    # Load PDF files
    for fpath in sorted(Path(DOCS_DIR).glob("*.pdf")):
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(fpath))
            full_text = "\n\n".join(
                page.extract_text() or "" for page in reader.pages
            )
            doc_id = fpath.stem
            sub_chunks = text_splitter.split_text(full_text)
            for chunk_text in sub_chunks:
                if chunk_text.strip():
                    all_chunks.append({
                        "text": chunk_text,
                        "metadata": {"source": doc_id, "file": fpath.name},
                    })
        except Exception as e:
            print(f"Warning: could not load {fpath.name}: {e}")

    return all_chunks


def ingest_documents(force: bool = False) -> dict:
    """Ingest documents into ChromaDB.

    Args:
        force: If True, re-ingest even if collection exists and is current.

    Returns:
        dict with status information.
    """
    client = _get_chroma_client()
    corpus_hash = _compute_corpus_hash()

    # Check if collection already exists and is current
    # chromadb v0.6.0: list_collections() returns collection names (strings) directly
    existing_collections = list(client.list_collections())
    if CHROMA_COLLECTION in existing_collections and not force:
        collection = client.get_collection(CHROMA_COLLECTION)
        stored_meta = collection.metadata or {}
        if stored_meta.get("corpus_hash") == corpus_hash:
            return {
                "status": "skipped",
                "message": "Collection already up to date",
                "num_chunks": collection.count(),
            }

    # Delete existing collection if present
    if CHROMA_COLLECTION in existing_collections:
        client.delete_collection(CHROMA_COLLECTION)

    # Load and chunk documents
    chunks = _load_and_chunk_documents()

    if not chunks:
        return {"status": "error", "message": "No documents found in docs/"}

    # Create embeddings
    embeddings = _get_embeddings()
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Generate unique IDs
    ids = [f"chunk_{i:04d}" for i in range(len(chunks))]

    # Embed all texts
    embedding_vectors = embeddings.embed_documents(texts)

    # Create collection and add documents
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"corpus_hash": corpus_hash},
    )

    # Add in batches of 100
    batch_size = 100
    for start in range(0, len(chunks), batch_size):
        end = min(start + batch_size, len(chunks))
        collection.add(
            ids=ids[start:end],
            documents=texts[start:end],
            metadatas=metadatas[start:end],
            embeddings=embedding_vectors[start:end],
        )

    return {
        "status": "success",
        "message": f"Ingested {len(chunks)} chunks from {len(list(Path(DOCS_DIR).glob('*.md')))} documents",
        "num_chunks": len(chunks),
        "corpus_hash": corpus_hash,
    }


if __name__ == "__main__":
    result = ingest_documents(force=True)
    print(result)
