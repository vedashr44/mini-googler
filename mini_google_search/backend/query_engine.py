import math
from typing import Dict, List, Tuple

from ..utils import config
from ..utils.caching import get_cache_backend
from ..utils.text_cleaning import preprocess
from .indexer import Indexer


class QueryEngine:
    def __init__(self):
        self.indexer = Indexer()
        self.indexer.load_index()
        self.cache = get_cache_backend()

    # ----- Ranking functions -----
    def _bm25_scores(self, query_terms: List[str]) -> Dict[str, float]:
        idx = self.indexer.index
        scores: Dict[str, float] = {}
        k1 = config.BM25_K1
        b = config.BM25_B

        candidate_docs = set()
        for term in set(query_terms):
            postings = idx.inverted_index.get(term)
            if postings:
                candidate_docs.update(postings.keys())

        for doc_id in candidate_docs:
            dl = idx.doc_lengths.get(doc_id, 0)
            denom_norm = k1 * (1 - b + b * dl / (idx.avgdl + 1e-9))
            s = 0.0
            for term in query_terms:
                postings = idx.inverted_index.get(term)
                if not postings or doc_id not in postings:
                    continue
                tf = postings[doc_id]
                idf = idx.idf.get(term, 0.0)
                s += idf * (tf * (k1 + 1)) / (tf + denom_norm)
            if s != 0.0:
                scores[doc_id] = s
        return scores

    def _tfidf_scores(self, query_terms: List[str]) -> Dict[str, float]:
        idx = self.indexer.index
        scores: Dict[str, float] = {}
        # Query tf
        q_tf: Dict[str, int] = {}
        for t in query_terms:
            q_tf[t] = q_tf.get(t, 0) + 1

        candidate_docs = set()
        for term in set(query_terms):
            postings = idx.inverted_index.get(term)
            if postings:
                candidate_docs.update(postings.keys())

        for doc_id in candidate_docs:
            s = 0.0
            for term, qf in q_tf.items():
                postings = idx.inverted_index.get(term)
                if not postings or doc_id not in postings:
                    continue
                df = idx.doc_freq.get(term, 1)
                idf = math.log((idx.N + 1) / df) + 1.0
                tf_d = postings[doc_id]
                s += (tf_d * idf) * (qf * idf)
            if s != 0.0:
                scores[doc_id] = s
        return scores

    # ----- Public API -----
    def search(self, query: str, k: int = None, ranking: str | None = None) -> List[Dict]:
        if not query or not query.strip():
            return []
        k = k or config.MAX_RESULTS
        mode = (ranking or config.RANKING_MODE).lower()
        if mode not in {"bm25", "tfidf"}:
            mode = config.RANKING_MODE
        key = f"q:{mode}:{k}:{query.strip().lower()}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        terms = preprocess(query)
        if mode == "tfidf":
            scores = self._tfidf_scores(terms)
        else:
            scores = self._bm25_scores(terms)

        ranked: List[Tuple[str, float]] = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
        results: List[Dict] = []
        for doc_id, score in ranked:
            doc = self.indexer.index.documents[doc_id]
            snippet = self._build_snippet(doc["content"], terms)
            results.append(
                {
                    "doc_id": doc_id,
                    "title": doc["title"],
                    "url": doc.get("url") or "",
                    "score": round(float(score), 4),
                    "snippet": snippet,
                }
            )

        self.cache.set(key, results)
        return results

    @staticmethod
    def _build_snippet(text: str, terms: List[str], window: int = 160) -> str:
        low = text.lower()
        pos = -1
        for t in terms:
            p = low.find(t)
            if p != -1 and (pos == -1 or p < pos):
                pos = p
        if pos == -1:
            snippet = (text[:window] + "...") if len(text) > window else text
            return QueryEngine._highlight(snippet, terms)
        start = max(0, pos - window // 2)
        end = min(len(text), start + window)
        snip = text[start:end]
        snippet = ("..." if start > 0 else "") + snip + ("..." if end < len(text) else "")
        return QueryEngine._highlight(snippet, terms)

    @staticmethod
    def _highlight(snippet: str, terms: List[str]) -> str:
        import re

        if not terms:
            return snippet
        # Escape and sort by length desc to avoid overlapping replacements
        parts = sorted({re.escape(t) for t in terms if t}, key=len, reverse=True)
        if not parts:
            return snippet
        pattern = re.compile(r"(" + "|".join(parts) + r")", re.IGNORECASE)
        return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", snippet)
