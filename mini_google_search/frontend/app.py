import os
from pathlib import Path
import sys

import streamlit as st

# Ensure project root is on sys.path so `mini_google_search` imports work
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

API_URL = os.getenv("API_URL")
# Normalize to avoid double slashes like //upload
API_BASE = API_URL.rstrip("/") if API_URL else None


def search_via_api(query: str, k: int):
    import requests

    base = API_BASE or ""
    resp = requests.get(f"{base}/search", params={"q": query, "k": k}, timeout=10)
    resp.raise_for_status()
    return resp.json()["results"]


def search_local(query: str, k: int):
    from mini_google_search.backend.query_engine import QueryEngine

    engine = QueryEngine()
    return engine.search(query, k)


def extract_pdf_text(file) -> str:
    # Try pdfminer.six first, then fall back to PyPDF2
    try:
        data = file.read()
        from io import BytesIO
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract

            text = pdfminer_extract(BytesIO(data))
            if text:
                return text.strip()
        except Exception:
            pass
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(BytesIO(data))
            parts = []
            for page in reader.pages:
                txt = page.extract_text() or ""
                parts.append(txt)
            return "\n".join(parts).strip()
        except Exception:
            return ""
    except Exception:
        return ""


def ingest_files(uploaded_files) -> tuple[int, int]:
    # Save uploaded files and rebuild index, locally or via API
    import requests
    from mini_google_search.utils import config
    from mini_google_search.backend.indexer import Indexer

    if API_BASE:
        # Send files directly to the API /upload endpoint
        files = []
        for uf in uploaded_files:
            data = uf.read()
            content_type = "application/pdf" if uf.name.lower().endswith(".pdf") else "text/plain"
            files.append(("files", (uf.name, data, content_type)))
        try:
            resp = requests.post(f"{API_BASE}/upload", files=files, timeout=60)
            resp.raise_for_status()
            j = resp.json()
            saved = int(j.get("saved", 0))
            total = int(j.get("indexed", 0))
        finally:
            for uf in uploaded_files:
                uf.close()
        return saved, total

    # Local path (no API): write to data dir and rebuild
    data_dir = Path(config.DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    for uf in uploaded_files:
        name = Path(uf.name).name
        suffix = Path(name).suffix.lower()
        stem = Path(name).stem
        target = data_dir / f"{stem}.txt"
        if target.exists():
            i = 1
            while (data_dir / f"{stem}_{i}.txt").exists():
                i += 1
            target = data_dir / f"{stem}_{i}.txt"
        try:
            if suffix == ".txt":
                content = uf.read().decode("utf-8", errors="ignore")
            elif suffix == ".pdf":
                content = extract_pdf_text(uf)
                if not content:
                    continue
            else:
                continue
            if not content.startswith(stem):
                content = f"{stem}\n" + content
            target.write_text(content, encoding="utf-8", errors="ignore")
            saved += 1
        finally:
            uf.close()

    idx = Indexer()
    idx.build_index(data_dir)
    idx.save_index()
    try:
        from mini_google_search.backend.indexer import Indexer as _I

        _i = _I()
        _i.load_index()
        total = _i.index.N
    except Exception:
        total = 0
    return saved, total


st.set_page_config(page_title="Mini Google Search", page_icon="🔎", layout="centered")
st.title("🔎 Mini Google Search")
st.caption("Upload .txt/.pdf, then search with BM25/TF‑IDF")

with st.sidebar:
    st.header("Settings")
    ranking_mode = st.radio("Ranking", options=["bm25", "tfidf"], index=0, horizontal=False)

# Corpus status panel
from mini_google_search.utils import config as _cfg

data_dir = Path(_cfg.DATA_DIR)
index_dir = Path(_cfg.INDEX_DIR)
num_txt = len(list(data_dir.glob("**/*.txt"))) if data_dir.exists() else 0
try:
    from mini_google_search.backend.indexer import Indexer as _I

    _i = _I()
    _i.load_index()
    indexed_docs = _i.index.N
except Exception:
    indexed_docs = 0

with st.expander("Corpus status", expanded=False):
    st.write(f"Data dir: {data_dir}")
    st.write(f"Index dir: {index_dir}")
    st.write(f".txt files found: {num_txt}")
    st.write(f"Indexed documents: {indexed_docs}")
    st.write(f"Using API: {'Yes' if API_BASE else 'No'}")

st.subheader("Add Documents")
uploads = st.file_uploader("Upload .txt or .pdf files", type=["txt", "pdf"], accept_multiple_files=True)
if uploads:
    if st.button("Add to corpus and rebuild index"):
        with st.spinner("Ingesting and indexing..."):
            saved, total = ingest_files(uploads)
        st.success(f"Added {saved} file(s). Corpus now has {total} documents.")

if st.button("Rebuild index"):
    with st.spinner("Rebuilding index..."):
        from mini_google_search.backend.indexer import Indexer as _I
        idx = _I()
        if API_BASE:
            import requests

            try:
                requests.post(f"{API_BASE}/index", timeout=20)
            except Exception as e:
                st.error(f"API rebuild failed: {e}")
        else:
            idx.build_index(data_dir)
            idx.save_index()
    st.success("Index rebuilt.")

query = st.text_input("Search query", "machine learning")
topk = st.slider("Top K", min_value=1, max_value=50, value=10)

if st.button("Search"):
    if not query.strip():
        st.warning("Please enter a query.")
    else:
        with st.spinner("Searching..."):
            try:
                if API_BASE:
                    import requests

                    resp = requests.get(
                        f"{API_BASE}/search",
                        params={"q": query, "k": topk, "ranking": ranking_mode},
                        timeout=20,
                    )
                    resp.raise_for_status()
                    results = resp.json()["results"]
                else:
                    results = search_local(query, topk)
            except Exception as e:
                st.error(f"Search failed: {e}")
                results = []

        if not results:
            st.info("No results found.")
        else:
            for r in results:
                st.markdown(f"### {r['title']}")
                st.markdown(r["snippet"], unsafe_allow_html=True)
                st.caption(f"Score: {r['score']}  •  Doc: {r['doc_id']}")
                st.divider()
