from fastapi import FastAPI, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
from typing import List
from pathlib import Path

from ..utils import config
from .indexer import Indexer
from .query_engine import QueryEngine


class SearchResponse(BaseModel):
    results: list


app = FastAPI(title="Mini Google Search")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    global _engine
    # Ensure an index exists; if not, attempt to build
    try:
        _ = Indexer().load_index()
    except AssertionError:
        idx = Indexer()
        idx.build_index(config.DATA_DIR)
        idx.save_index()
    _engine = QueryEngine()


@app.get("/health")
def health():
    return {"status": "ok", "ranking": config.RANKING_MODE}


@app.get("/")
def root():
    return RedirectResponse(url="/docs", status_code=302)


@app.post("/index")
def rebuild_index():
    idx = Indexer()
    idx.build_index(config.DATA_DIR)
    idx.save_index()
    # reload engine
    global _engine
    _engine = QueryEngine()
    return {"indexed": idx.index.N}


@app.get("/search", response_model=SearchResponse)
def search(q: str = Query("", min_length=1), k: int = Query(config.MAX_RESULTS, ge=1, le=100), ranking: str | None = Query(None)):
    results = _engine.search(q, k, ranking=ranking)
    return {"results": results}


@app.get("/settings")
def get_settings():
    return {"ranking": config.RANKING_MODE}


def _extract_pdf_text_bytes(data: bytes) -> str:
    # Try pdfminer first, fallback to PyPDF2
    try:
        from io import BytesIO
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract

            t = pdfminer_extract(BytesIO(data))
            if t:
                return t.strip()
        except Exception:
            pass
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(BytesIO(data))
            parts = []
            for p in reader.pages:
                parts.append((p.extract_text() or ""))
            return "\n".join(parts).strip()
        except Exception:
            return ""
    except Exception:
        return ""


@app.post("/upload")
async def upload(files: List[UploadFile] = File(...)):
    data_dir = Path(config.DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    saved = 0
    saved_paths: list[str] = []
    for f in files:
        name = Path(f.filename or "upload").name
        stem = Path(name).stem
        suffix = Path(name).suffix.lower()
        target = data_dir / f"{stem}.txt"
        if target.exists():
            i = 1
            while (data_dir / f"{stem}_{i}.txt").exists():
                i += 1
            target = data_dir / f"{stem}_{i}.txt"

        data = await f.read()
        content = ""
        if suffix == ".txt" or (f.content_type or "").endswith("plain"):
            try:
                content = data.decode("utf-8", errors="ignore")
            except Exception:
                content = ""
        elif suffix == ".pdf" or (f.content_type or "").endswith("pdf"):
            content = _extract_pdf_text_bytes(data)
        else:
            # skip unsupported types silently
            content = ""

        if not content:
            continue
        if not content.startswith(stem):
            content = f"{stem}\n" + content
        target.write_text(content, encoding="utf-8", errors="ignore")
        saved += 1
        saved_paths.append(str(target))

    # rebuild index if we saved anything
    if saved:
        idx = Indexer()
        idx.build_index(data_dir)
        idx.save_index()
        global _engine
        _engine = QueryEngine()
        total = idx.index.N
    else:
        total = 0
    return {"saved": saved, "indexed": total, "paths": saved_paths}
