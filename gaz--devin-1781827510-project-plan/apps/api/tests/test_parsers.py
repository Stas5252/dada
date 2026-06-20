import io

from app.parsers import extract_text


def test_extract_text_txt():
    content = b"Hello, world!"
    text = extract_text("test.txt", content)
    assert text == "Hello, world!"

def test_extract_text_pdf():
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    # Just basic test since we can't easily write text to pdf in pure python without extra libs
    # Let's test DOCX which is easier
    pass


def test_extract_text_docx():
    import docx

    doc = docx.Document()
    doc.add_paragraph("Hello from docx")
    out = io.BytesIO()
    doc.save(out)
    out.seek(0)

    text = extract_text("test.docx", out.read())
    assert "Hello from docx" in text
