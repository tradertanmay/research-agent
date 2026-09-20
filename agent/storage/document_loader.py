import io
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

from agent.config import settings

@dataclass
class UploadedDocument:
    doc_id: str
    filename: str
    file_type: str
    size_bytes: int
    char_count: int
    page_count: int
    text: str
    saved_path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UploadedDocument":
        return cls(**data)


class DocumentLoader:
    def __init__(self, upload_dir: Optional[Path] = None):
        self.upload_dir = upload_dir or (settings.vault_dir / "uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_and_extract(self, filename: str, file_bytes: bytes) -> UploadedDocument:
        """Extract text from uploaded PDF or text-based document and persist to vault."""
        doc_id = str(uuid.uuid4())[:8]
        ext = Path(filename).suffix.lower()
        size_bytes = len(file_bytes)
        text = ""
        page_count = 1

        if ext == ".pdf":
            file_type = "pdf"
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                page_count = len(reader.pages)
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    extracted = page.extract_text()
                    if extracted and extracted.strip():
                        pages_text.append(f"--- Page {idx + 1} ---\n" + extracted.strip())
                text = "\n\n".join(pages_text)
            except Exception as e:
                text = f"[PDF Parsing Error: {str(e)}]"
        elif ext in (".txt", ".md", ".json", ".csv"):
            file_type = ext.lstrip(".")
            text = file_bytes.decode("utf-8", errors="replace")
        else:
            file_type = ext.lstrip(".") or "unknown"
            text = file_bytes.decode("utf-8", errors="replace")

        # Clean text
        text = text.strip()
        char_count = len(text)

        # Save raw file
        saved_file_name = f"{doc_id}_{filename}"
        saved_path = self.upload_dir / saved_file_name
        with open(saved_path, "wb") as f:
            f.write(file_bytes)

        doc = UploadedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            size_bytes=size_bytes,
            char_count=char_count,
            page_count=page_count,
            text=text,
            saved_path=str(saved_path),
        )

        # Save metadata and extracted text
        meta_file = self.upload_dir / f"{doc_id}_meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(doc.to_dict(), f, indent=2, ensure_ascii=False)

        return doc

    def get_document(self, doc_id: str) -> Optional[UploadedDocument]:
        """Load document metadata and parsed text by doc_id."""
        meta_file = self.upload_dir / f"{doc_id}_meta.json"
        if not meta_file.exists():
            return None
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return UploadedDocument.from_dict(data)
        except Exception:
            return None

    def list_documents(self, doc_ids: Optional[List[str]] = None) -> List[UploadedDocument]:
        """List documents matching IDs, or all stored documents."""
        docs = []
        if doc_ids:
            for d_id in doc_ids:
                doc = self.get_document(d_id)
                if doc:
                    docs.append(doc)
            return docs

        for meta_file in sorted(self.upload_dir.glob("*_meta.json"), reverse=True):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                docs.append(UploadedDocument.from_dict(data))
            except Exception:
                continue
        return docs


# Global loader instance
document_loader = DocumentLoader()
