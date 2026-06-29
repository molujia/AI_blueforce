"""Document loading helpers for the lightweight GraphRAG pipeline."""

from __future__ import annotations

import csv
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree


@dataclass(frozen=True)
class LoadedDocument:
    path: str
    source_id: str
    format: str
    text: str


def load_documents(paths: Iterable[str | Path]) -> list[LoadedDocument]:
    documents: list[LoadedDocument] = []
    for path in paths:
        file_path = Path(path)
        if file_path.exists() and file_path.is_file():
            documents.append(load_document(file_path))
        elif file_path.exists() and file_path.is_dir():
            for child in sorted(file_path.rglob("*")):
                if child.is_file() and child.suffix.lower() in {".txt", ".md", ".json", ".csv", ".docx", ".pdf"}:
                    documents.append(load_document(child))
    return documents


def load_document(path: str | Path) -> LoadedDocument:
    file_path = Path(path)
    suffix = file_path.suffix.lower().lstrip(".") or "text"
    if suffix in {"txt", "md"}:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    elif suffix == "json":
        text = _load_json_text(file_path)
    elif suffix == "csv":
        text = _load_csv_text(file_path)
    elif suffix == "docx":
        text = _load_docx_text(file_path)
    elif suffix == "pdf":
        text = _load_pdf_text(file_path)
    else:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    return LoadedDocument(path=str(file_path), source_id=file_path.name, format=suffix, text=_normalize_text(text))


def chunk_document(document: LoadedDocument, *, max_chars: int = 1200) -> list[dict[str, str]]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", document.text) if part.strip()]
    chunks: list[dict[str, str]] = []
    current = ""
    for paragraph in paragraphs or [document.text]:
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(_chunk(document, len(chunks), current))
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip() if current else paragraph
    if current:
        chunks.append(_chunk(document, len(chunks), current))
    return chunks


def _chunk(document: LoadedDocument, index: int, text: str) -> dict[str, str]:
    return {"chunk_id": f"{document.source_id}#chunk-{index}", "source_id": document.source_id, "text": text}


def _load_json_text(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return json.dumps(data, ensure_ascii=False, indent=2)


def _load_csv_text(path: Path) -> str:
    rows: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            rows.append(" | ".join(row))
    return "\n".join(rows)


def _load_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{namespace}p"):
        texts = [node.text or "" for node in paragraph.iter(f"{namespace}t")]
        if any(texts):
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


def _load_pdf_text(path: Path) -> str:
    # Dependency-free fallback: many PDFs expose enough uncompressed literal text
    # for smoke tests and source IDs. Production can swap in pypdf/pdfplumber.
    data = path.read_bytes()
    decoded = data.decode("latin-1", errors="ignore")
    literal_strings = re.findall(r"\(([^()]{3,})\)", decoded)
    if literal_strings:
        return "\n".join(literal_strings)
    words = re.findall(r"[A-Za-z][A-Za-z0-9,.;:'\-/]{3,}", decoded)
    return " ".join(words[:5000]) or path.name


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()