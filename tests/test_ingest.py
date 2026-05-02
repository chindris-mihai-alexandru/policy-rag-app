"""Tests for the document ingestion pipeline."""

from pathlib import Path

from src.config import DOCS_DIR


def test_docs_directory_exists():
    """Test that the docs directory exists."""
    assert Path(DOCS_DIR).exists()
    assert Path(DOCS_DIR).is_dir()


def test_docs_have_markdown_files():
    """Test that docs/ contains markdown files."""
    md_files = list(Path(DOCS_DIR).glob("*.md"))
    assert len(md_files) >= 5, f"Expected at least 5 markdown files, found {len(md_files)}"


def test_all_expected_docs_present():
    """Test that all 10 expected policy documents are present."""
    expected = [
        "pto-and-leave-policy.md",
        "remote-work-policy.md",
        "expense-reimbursement-policy.md",
        "information-security-policy.md",
        "code-of-conduct.md",
        "holiday-schedule.md",
        "benefits-overview.md",
        "onboarding-guide.md",
        "performance-review-policy.md",
        "acceptable-use-policy.md",
    ]
    for filename in expected:
        fpath = Path(DOCS_DIR) / filename
        assert fpath.exists(), f"Missing expected document: {filename}"


def test_docs_are_not_empty():
    """Test that all docs have content."""
    for fpath in Path(DOCS_DIR).glob("*.md"):
        content = fpath.read_text(encoding="utf-8")
        assert len(content) > 100, f"Document {fpath.name} appears too short ({len(content)} chars)"


def test_docs_have_policy_id():
    """Test that each document has a Policy ID."""
    for fpath in Path(DOCS_DIR).glob("*.md"):
        content = fpath.read_text(encoding="utf-8")
        assert "Policy ID:" in content, f"Document {fpath.name} missing Policy ID"


def test_load_and_chunk():
    """Test that documents can be loaded and chunked."""
    from src.ingest import _load_and_chunk_documents

    chunks = _load_and_chunk_documents()
    assert len(chunks) > 50, f"Expected >50 chunks, got {len(chunks)}"

    # Check chunk structure
    for chunk in chunks[:5]:
        assert "text" in chunk
        assert "metadata" in chunk
        assert "source" in chunk["metadata"]
        assert "file" in chunk["metadata"]
        assert len(chunk["text"]) > 0
