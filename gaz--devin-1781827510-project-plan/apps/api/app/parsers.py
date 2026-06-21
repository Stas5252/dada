import io
import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
import docx

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
    """Extract visible text from a webpage URL."""
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
        raise ValueError(f"Failed to extract text from URL {url}: {e}")

def extract_text(filename: str, file_bytes: bytes) -> str:
    """Extract text from a file based on its extension."""
    ext = filename.lower().split('.')[-1]
    if ext == 'pdf':
        return parse_pdf(file_bytes)
    elif ext in ('docx', 'doc'):
        return parse_docx(file_bytes)
    else:
        # Default to UTF-8 decoding for txt, md, csv, etc.
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1")
