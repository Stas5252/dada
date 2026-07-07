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
    """Extract visible text from a webpage URL with exponential backoff retries, SSRF protection, and size limits."""
    import ipaddress
    import socket
    import urllib.parse
    import httpx

    def validate_url(check_url: str) -> None:
        parsed = urllib.parse.urlparse(check_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Invalid URL scheme")
        if parsed.hostname is None:
            raise ValueError("URL hostname is required")
        try:
            ip = socket.gethostbyname(parsed.hostname)
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                raise ValueError("Access to private IP addresses is forbidden")
        except Exception as e:
            raise ValueError(f"URL validation failed: {str(e)}") from e

    max_retries = 3
    backoff = 1.0
    last_exc: Exception | None = None
    max_size = 5 * 1024 * 1024  # 5 MB

    for attempt in range(max_retries + 1):
        try:
            current_url = url
            redirects = 0
            response = None
            
            with httpx.Client(timeout=10.0, follow_redirects=False) as client:
                while redirects < 5:
                    validate_url(current_url)
                    response = client.get(current_url)
                    if response.is_redirect:
                        current_url = str(response.next_request.url)
                        redirects += 1
                        continue
                    break
                
                if response is None or response.is_redirect:
                    raise ValueError("Too many redirects")
                
                response.raise_for_status()
                
                # Check Content-Length if present
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > max_size:
                    raise ValueError("File is too large")

                content = response.content
                if len(content) > max_size:
                    raise ValueError("File is too large")

            soup = BeautifulSoup(content.decode("utf-8", errors="replace"), "html.parser")

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
