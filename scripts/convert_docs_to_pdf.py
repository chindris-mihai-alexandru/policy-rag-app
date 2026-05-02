"""Convert synthetic Acme Corp markdown policy documents to PDFs using fpdf2."""

import re
from pathlib import Path

from fpdf import FPDF


DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


class PolicyPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Acme Corp - Official Policy Document", align="C")
        self.ln(4)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def clean_text(text: str) -> str:
    """Remove markdown syntax for plain text rendering."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Replace common unicode chars that latin-1 can't encode
    text = text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u2022", "*").replace("\u00e2\u0080\u0099", "'")
    # Drop any remaining non-latin-1 characters
    text = text.encode("latin-1", errors="ignore").decode("latin-1")
    return text.strip()


def convert_md_to_pdf(md_path: Path, out_path: Path) -> int:
    pdf = PolicyPDF()
    pdf.set_margins(15, 20, 15)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    content = md_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    for line in lines:
        stripped = line.rstrip()

        if stripped.startswith("# ") and not stripped.startswith("## "):
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(30, 30, 80)
            pdf.multi_cell(0, 10, clean_text(stripped[2:]))
            pdf.ln(3)

        elif stripped.startswith("## ") and not stripped.startswith("### "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(50, 50, 120)
            pdf.ln(4)
            pdf.multi_cell(0, 8, clean_text(stripped[3:]))
            pdf.set_draw_color(180, 180, 220)
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.ln(3)

        elif stripped.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(60, 60, 140)
            pdf.ln(3)
            pdf.multi_cell(0, 7, clean_text(stripped[4:]))
            pdf.ln(2)

        elif stripped.startswith(("- ", "* ", "+ ")):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            text = clean_text(stripped[2:])
            pdf.set_x(15)
            pdf.multi_cell(180, 6, "  - " + text)

        elif re.match(r"^\d+\.\s", stripped):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            num = re.match(r"^(\d+)\.", stripped).group(1)
            text = clean_text(re.sub(r"^\d+\.\s", "", stripped))
            pdf.set_x(15)
            pdf.multi_cell(180, 6, f"  {num}. {text}")

        elif stripped.startswith("|") and "---" in stripped:
            continue

        elif stripped.startswith("|"):
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(30, 30, 30)
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            col_w = min(40, 175 // max(len(cells), 1))
            pdf.set_x(15)
            for cell in cells:
                pdf.cell(col_w, 6, clean_text(cell)[:30], border=1)
            pdf.ln()

        elif stripped == "":
            pdf.ln(3)

        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.set_x(15)
            pdf.multi_cell(180, 6, clean_text(stripped))

    pdf.output(str(out_path))
    pages = pdf.page
    print(f"  {md_path.name} -> {out_path.name} ({pages} pages)")
    return pages


SYNTHETIC_DOCS = [
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


if __name__ == "__main__":
    total_pages = 0
    total_files = 0
    for doc_name in SYNTHETIC_DOCS:
        md_path = DOCS_DIR / doc_name
        if not md_path.exists():
            print(f"  WARNING: {doc_name} not found, skipping")
            continue
        pdf_name = doc_name.replace(".md", ".pdf")
        out_path = DOCS_DIR / pdf_name
        pages = convert_md_to_pdf(md_path, out_path)
        total_pages += pages
        total_files += 1

    print(f"\nConverted {total_files} files, {total_pages} pages total (synthetic only)")
    print(f"Plus public_counsel_employee_handbook.pdf (~40 pages)")
    print(f"Grand total estimate: ~{total_pages + 40} pages")
