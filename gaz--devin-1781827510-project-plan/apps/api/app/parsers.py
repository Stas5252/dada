import io
import time

import docx
import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader


def parse_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    reader = PdfReader(io.BytesIO(file_bytes))
    text = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)
    return "\n\n".join(text)

def parse_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file."""
    doc = docx.Document(io.BytesIO(file_bytes))
    text = []
    for paragraph in doc.paragraphs:
        if paragraph.text:
            text.append(paragraph.text)
    return "\n\n".join(text)


def parse_url(url: str) -> str:
    """Extract visible text from a webpage URL with exponential backoff retries."""
    import ipaddress
    import socket
    import urllib.parse

    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme not in ("http", "https"):
        raise ValueError("Invalid URL scheme")
    if parsed_url.hostname is None:
        raise ValueError("URL hostname is required")

    try:
        ip = socket.gethostbyname(parsed_url.hostname)
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
            raise ValueError("Access to private IP addresses is forbidden")
    except Exception as e:
        raise ValueError(f"URL validation failed: {str(e)}") from e

    max_retries = 3
    backoff = 1.0
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = httpx.get(url, timeout=10.0, follow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()

            text = soup.get_text(separator="\n")

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            return text
        except Exception as e:
            last_exc = e
            if attempt == max_retries:
                break
            time.sleep(backoff)
            backoff *= 2.0

    raise ValueError(f"Failed to extract text from URL {url} after {max_retries} attempts: {last_exc}") from last_exc

def extract_text(filename: str, file_bytes: bytes) -> str:
    """Extract text from a file based on its extension."""
    ext = filename.lower().split(".")[-1]
    if ext == "pdf":
        return parse_pdf(file_bytes)
    if ext in ("docx", "doc"):
        return parse_docx(file_bytes)

    # Default to UTF-8 decoding for txt, md, csv, etc.
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")
