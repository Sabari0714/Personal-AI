"""
ROLEX AI — Document Intelligence
Read / write / search / extract / summarize / analyze / convert / index documents.
Local-first processing with graceful handling of optional dependencies.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.documents")

SUPPORTED = (".txt", ".md", ".csv", ".json", ".pdf", ".docx", ".xlsx", ".pptx")


class DocumentError(Exception):
    pass


class DocumentManager:
    def __init__(self):
        self.db = get_db()

    # -- extraction ---------------------------------------------------------
    def extract_text(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            raise DocumentError(f"File not found: {path}")
        suffix = p.suffix.lower()
        try:
            if suffix in (".txt", ".md"):
                return p.read_text(encoding="utf-8", errors="replace")
            if suffix == ".csv":
                return self._read_csv(p)
            if suffix == ".json":
                return json.dumps(json.loads(p.read_text(encoding="utf-8", errors="replace")),
                                  indent=2, ensure_ascii=False)
            if suffix == ".pdf":
                return self._read_pdf(p)
            if suffix == ".docx":
                return self._read_docx(p)
            if suffix == ".xlsx":
                return self._read_xlsx(p)
            if suffix == ".pptx":
                return self._read_pptx(p)
            raise DocumentError(f"Unsupported format: {suffix}")
        except DocumentError:
            raise
        except Exception as e:
            log.error("Extraction failed for %s: %s", path, e)
            raise DocumentError(f"Could not read {p.name}: {e}")

    def _read_csv(self, p: Path) -> str:
        rows = []
        with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i > 5000:
                    rows.append("... (truncated)")
                    break
                rows.append(" | ".join(row))
        return "\n".join(rows)

    def _read_pdf(self, p: Path) -> str:
        # Try pypdf, then pdfminer, then pdftotext CLI
        try:
            from pypdf import PdfReader  # type: ignore
            reader = PdfReader(str(p))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            pass
        try:
            from PyPDF2 import PdfReader  # type: ignore
            reader = PdfReader(str(p))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            pass
        try:
            import subprocess
            out = subprocess.run(["pdftotext", "-layout", str(p), "-"],
                                 capture_output=True, text=True, timeout=60)
            if out.returncode == 0:
                return out.stdout
        except Exception:
            pass
        raise DocumentError("PDF support requires 'pypdf' or the 'pdftotext' tool.")

    def _read_docx(self, p: Path) -> str:
        try:
            import docx  # type: ignore
            d = docx.Document(str(p))
            return "\n".join(par.text for par in d.paragraphs)
        except Exception:
            pass
        try:
            import subprocess
            out = subprocess.run(["antiword", str(p)], capture_output=True, text=True, timeout=60)
            if out.returncode == 0:
                return out.stdout
        except Exception:
            pass
        raise DocumentError("DOCX support requires 'python-docx' or 'antiword'.")

    def _read_xlsx(self, p: Path) -> str:
        try:
            import openpyxl  # type: ignore
            wb = openpyxl.load_workbook(str(p), read_only=True, data_only=True)
            lines = []
            for ws in wb.worksheets:
                lines.append(f"# Sheet: {ws.title}")
                for row in ws.iter_rows(values_only=True):
                    lines.append(" | ".join("" if c is None else str(c) for c in row))
            return "\n".join(lines)
        except Exception as e:
            raise DocumentError(f"XLSX support requires 'openpyxl'. ({e})")

    def _read_pptx(self, p: Path) -> str:
        try:
            from pptx import Presentation  # type: ignore
            prs = Presentation(str(p))
            lines = []
            for i, slide in enumerate(prs.slides, 1):
                lines.append(f"# Slide {i}")
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        lines.append(shape.text)
            return "\n".join(lines)
        except Exception as e:
            raise DocumentError(f"PPTX support requires 'python-pptx'. ({e})")

    # -- operations ---------------------------------------------------------
    def summarize(self, text: str, max_sentences: int = 5) -> str:
        """Local extractive summary (no external AI required)."""
        if not text or not text.strip():
            return "No content to summarize."
        import re
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        if len(sentences) <= max_sentences:
            return " ".join(sentences)
        # Score by word frequency
        words = re.findall(r"\w+", text.lower())
        freq: Dict[str, int] = {}
        for w in words:
            if len(w) > 3:
                freq[w] = freq.get(w, 0) + 1
        scored = []
        for idx, s in enumerate(sentences):
            score = sum(freq.get(w, 0) for w in re.findall(r"\w+", s.lower()))
            scored.append((score, idx, s))
        top = sorted(scored, reverse=True)[:max_sentences]
        top_sorted = sorted(top, key=lambda x: x[1])
        return " ".join(s for _, _, s in top_sorted)

    def analyze(self, path: str) -> dict:
        text = self.extract_text(path)
        words = text.split()
        return {
            "path": str(path),
            "characters": len(text),
            "words": len(words),
            "lines": text.count("\n") + 1,
            "summary": self.summarize(text),
        }

    def index(self, path: str) -> int:
        p = Path(path)
        text = self.extract_text(path)
        meta = json.dumps({"suffix": p.suffix.lower()})
        cur = self.db.execute(
            "INSERT INTO documents(path, name, doc_type, size, content, meta, indexed_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (str(p), p.name, p.suffix.lower(), p.stat().st_size if p.exists() else 0,
             text, meta, time.time()),
        )
        log.info("Indexed document: %s", p.name)
        return cur.lastrowid

    def search(self, term: str, limit: int = 20) -> List[dict]:
        like = f"%{term}%"
        rows = self.db.query(
            "SELECT id, path, name, doc_type, indexed_at FROM documents "
            "WHERE content LIKE ? OR name LIKE ? LIMIT ?",
            (like, like, limit),
        )
        return [dict(r) for r in rows]

    def list_indexed(self, limit: int = 100) -> List[dict]:
        rows = self.db.query(
            "SELECT id, path, name, doc_type, size, indexed_at FROM documents "
            "ORDER BY indexed_at DESC LIMIT ?", (limit,),
        )
        return [dict(r) for r in rows]

    def write(self, path: str, content: str) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return str(p)


_docs: Optional[DocumentManager] = None


def get_documents() -> DocumentManager:
    global _docs
    if _docs is None:
        _docs = DocumentManager()
    return _docs
