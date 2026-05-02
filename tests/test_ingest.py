"""Tests for the document ingestion pipeline."""

from pathlib import Path

from src.config import DOCS_DIR


def test_docs_directory_exists():
    """Test that the docs directory exists."""
    assert Path(DOCS_DIR).exists()
    assert Path(DOCS_DIR).is_dir()


def test_docs_have_pdf_files():
    """Test that docs/ contains PDF files."""
    pdf_files = list(Path(DOCS_DIR).glob("*.pdf"))
    assert len(pdf_files) >= 5, f"Expected at least 5 PDF files, found {len(pdf_files)}"


def test_all_expected_docs_present():
    """Test that all 10 synthetic Acme policy PDFs are present, plus the public handbook."""
    expected = [
        "pto-and-leave-policy.pdf",
        "remote-work-policy.pdf",
        "expense-reimbursement-policy.pdf",
        "information-security-policy.pdf",
        "code-of-conduct.pdf",
        "holiday-schedule.pdf",
        "benefits-overview.pdf",
        "onboarding-guide.pdf",
        "performance-review-policy.pdf",
        "acceptable-use-policy.pdf",
        "public_counsel_employee_handbook.pdf",
    ]
    for filename in expected:
        fpath = Path(DOCS_DIR) / filename
        assert fpath.exists(), f"Missing expected document: {filename}"


def test_docs_are_not_empty():
    """Test that all PDFs have content (non-zero file size)."""
    for fpath in Path(DOCS_DIR).glob("*.pdf"):
        size = fpath.stat().st_size
        assert size > 1000, f"PDF {fpath.name} appears too small ({size} bytes)"


def test_no_markdown_files_in_docs():
    """Corpus should be PDF-only — no markdown files."""
    md_files = list(Path(DOCS_DIR).glob("*.md"))
    assert len(md_files) == 0, f"Found unexpected markdown files: {[f.name for f in md_files]}"


def test_corpus_page_count_in_range():
    """Total corpus should be between 30 and 120 pages per rubric guidelines."""
    from pypdf import PdfReader
    total = 0
    for fpath in sorted(Path(DOCS_DIR).glob("*.pdf")):
        try:
            total += len(PdfReader(str(fpath)).pages)
        except Exception:
            pass
    assert 30 <= total <= 120, f"Corpus page count {total} outside allowed range 30-120"


def test_load_and_chunk():
    """Test that documents can be loaded and chunked."""
    from src.ingest import _load_and_chunk_documents

    chunks = _load_and_chunk_documents()
    assert len(chunks) > 50, f"Expected >50 chunks, got {len(chunks)}"

    for chunk in chunks[:5]:
        assert "text" in chunk
        assert "metadata" in chunk
        assert "source" in chunk["metadata"]
        assert "file" in chunk["metadata"]
        assert len(chunk["text"]) > 0
