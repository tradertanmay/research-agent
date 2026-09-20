import io
import unittest
from starlette.testclient import TestClient
from agent.web.server import app
from agent.storage.document_loader import DocumentLoader, UploadedDocument
from pypdf import PdfWriter

class TestDocumentUpload(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.loader = DocumentLoader()

    def test_text_document_extraction(self):
        content = b"This is a test research document on battery chemistry.\nEnergy density: 450 Wh/kg."
        doc = self.loader.save_and_extract("battery_spec.txt", content)

        self.assertIsNotNone(doc.doc_id)
        self.assertEqual(doc.filename, "battery_spec.txt")
        self.assertEqual(doc.file_type, "txt")
        self.assertIn("Energy density: 450 Wh/kg", doc.text)
        self.assertEqual(doc.page_count, 1)

        # Test retrieval
        retrieved = self.loader.get_document(doc.doc_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.doc_id, doc.doc_id)
        self.assertEqual(retrieved.text, doc.text)

    def test_pdf_document_extraction(self):
        # Generate a minimal valid PDF in memory
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        pdf_bytes_io = io.BytesIO()
        writer.write(pdf_bytes_io)
        pdf_bytes = pdf_bytes_io.getvalue()

        doc = self.loader.save_and_extract("sample_paper.pdf", pdf_bytes)
        self.assertIsNotNone(doc.doc_id)
        self.assertEqual(doc.filename, "sample_paper.pdf")
        self.assertEqual(doc.file_type, "pdf")
        self.assertEqual(doc.page_count, 1)

    def test_api_upload_endpoint(self):
        # 1. Valid file upload
        files = {"file": ("test_doc.md", b"# Quantum Dot Research\n\nHigh efficiency emission.", "text/markdown")}
        res = self.client.post("/api/upload", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("doc_id", data)
        self.assertEqual(data["filename"], "test_doc.md")
        self.assertEqual(data["file_type"], "md")
        self.assertIn("Quantum Dot Research", data["preview"])

        # 2. Empty file rejected
        res_empty = self.client.post("/api/upload", files={"file": ("empty.txt", b"", "text/plain")})
        self.assertEqual(res_empty.status_code, 400)

if __name__ == "__main__":
    unittest.main()
