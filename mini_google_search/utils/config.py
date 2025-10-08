import os
from pathlib import Path


# Paths
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("MGS_DATA_DIR", ROOT_DIR / "mini_google_search" / "data"))
INDEX_DIR = Path(os.getenv("MGS_INDEX_DIR", ROOT_DIR / "mini_google_search" / "backend" / "index"))


# Ranking
RANKING_MODE = os.getenv("MGS_RANKING", "bm25").lower()  # options: "bm25", "tfidf"
MAX_RESULTS = int(os.getenv("MGS_MAX_RESULTS", "10"))


# BM25 parameters
BM25_K1 = float(os.getenv("MGS_BM25_K1", "1.5"))
BM25_B = float(os.getenv("MGS_BM25_B", "0.75"))


# Caching
CACHE_SIZE = int(os.getenv("MGS_CACHE_SIZE", "256"))
REDIS_URL = os.getenv("REDIS_URL")  # optional


# API/UI
API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
API_HOST = os.getenv("API_HOST", "0.0.0.0")

