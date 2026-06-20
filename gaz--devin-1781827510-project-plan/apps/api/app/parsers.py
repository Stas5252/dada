import io

from fastapi import HTTPException


def extract_text_from_pdf(content_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content_bytes))
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        return "\n\n".join(text)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse PDF file: {str(exc)}",
        ) from exc


def extract_text_from_docx(content_bytes: bytes) -> str:
    try:
        import docx

        doc = docx.Document(io.BytesIO(content_bytes))
        text = [paragraph.text for paragraph in doc.paragraphs if paragraph.text]
        return "\n".join(text)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse DOCX file: {str(exc)}",
        ) from exc


def extract_text(filename: str, content_bytes: bytes) -> str:
    ext = filename.lower().split(".")[-1]

    if ext == "pdf":
        return extract_text_from_pdf(content_bytes)
    elif ext == "docx":
        return extract_text_from_docx(content_bytes)
    else:
        # Fallback to UTF-8 decoding for txt, md, csv, etc.
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Only UTF-8 text, PDF, and DOCX files are supported. "
                    f"Failed to decode {ext}."
                ),
            ) from exc
