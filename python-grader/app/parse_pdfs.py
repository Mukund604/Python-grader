import fitz
from pathlib import Path


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts and returns plain text from a PDF.
    All pages are concatenated in reading order.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Input file is not a PDF")

    doc = fitz.open(pdf_path)

    if doc.page_count == 0:
        doc.close()
        raise ValueError("PDF has no pages")

    extracted_text = []

    for page in doc:
        text = page.get_text("text").strip()
        if text:
            extracted_text.append(text)

    doc.close()

    if not extracted_text:
        raise ValueError("No extractable text found in PDF")

    # Join pages with clear separation
    return "\n\n--- PAGE BREAK ---\n\n".join(extracted_text)


# teacher_pdf = "/Users/mukund604/Documents/GitHub/graderight-academic-suite/python-grader/sample-pdfs/teacher.pdf"
# pdf = (extract_text_from_pdf(teacher_pdf))
# print(pdf)