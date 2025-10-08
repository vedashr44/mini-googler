Mini Google Search Engine – Scalable Information Retrieval System

Overview
- Implements a small-scale search engine with preprocessing, inverted indexing, TF-IDF and BM25 ranking, and a simple API + Streamlit UI.
- Pure-Python core (no heavy ML deps required). Optional external services (Redis, embeddings) are pluggable later.

Quick Start
- Prepare corpus: put `.txt` files in `mini_google_search/data/`. Filenames are used as titles; first line may act as a nicer title.

Indexing
- Python path: `mini_google_search`
- Build index (programmatic):
  from mini_google_search.backend.indexer import Indexer
  idx = Indexer()
  idx.build_index("mini_google_search/data")
  idx.save_index()

API (FastAPI)
- Run:
  uvicorn mini_google_search.backend.api:app --reload --port 8000
- Endpoints:
  - GET /health
  - POST /index          # rebuilds the index from data folder
  - GET /search?q=term&k=10[&ranking=bm25|tfidf]
  - GET /settings
  - POST /upload         # multipart file(s) upload (.txt/.pdf); reindexes

Frontend (Streamlit)
- Run without API (direct engine):
  streamlit run mini_google_search/frontend/app.py
- Or set API usage:
  set API_URL=http://localhost:8000
  streamlit run mini_google_search/frontend/app.py

Config
- See `mini_google_search/utils/config.py` for tunables: data path, index path, ranking mode, and cache size.

Notes
- BM25 is the default; TF-IDF available. Embedding search is left as an optional extension.
- For Redis caching, install `redis` and set `REDIS_URL`, otherwise an in-memory LRU is used.

Deployment on GCP (Cloud Run - Always Free)
- Prereqs: Install gcloud SDK, enable Cloud Run and Artifact Registry, choose a project and region with Always Free (e.g., us-central1).
- Build + Deploy:
  1) gcloud auth login
  2) gcloud config set project YOUR_PROJECT
  3) gcloud builds submit --tag "us-central1-docker.pkg.dev/YOUR_PROJECT/containers/mini-google:latest"
  4) gcloud run deploy mini-google-api \
       --image us-central1-docker.pkg.dev/YOUR_PROJECT/containers/mini-google:latest \
       --region us-central1 --allow-unauthenticated --platform managed --port 8080
- The service URL exposes `/docs`, `/search`, `/health`.
- Always Free covers a small monthly quota; stay within limits to keep costs at $0.
