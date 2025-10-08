import json
import math
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from ..utils import config
from ..utils.text_cleaning import preprocess


@dataclass
class Index:
    inverted_index: Dict[str, Dict[str, int]] = field(default_factory=dict)
    doc_lengths: Dict[str, int] = field(default_factory=dict)
    documents: Dict[str, Dict[str, str]] = field(default_factory=dict)  # id -> {title, content, url}
    doc_freq: Dict[str, int] = field(default_factory=dict)
    idf: Dict[str, float] = field(default_factory=dict)
    N: int = 0
    avgdl: float = 0.0


class Indexer:
    def __init__(self):
        self.index = Index()

    def build_index(self, data_dir: str | Path) -> None:
        data_dir = Path(data_dir)
        assert data_dir.exists(), f"Data directory not found: {data_dir}"

        documents: Dict[str, Dict[str, str]] = {}
        inverted: Dict[str, Dict[str, int]] = {}
        doc_lengths: Dict[str, int] = {}

        for path in sorted(data_dir.glob("**/*.txt")):
            doc_id = str(path.relative_to(data_dir))
            content = path.read_text(encoding="utf-8", errors="ignore")
            if not content.strip():
                continue
            lines = content.splitlines()
            title = lines[0].strip() if lines else path.stem
            url = ""
            documents[doc_id] = {"title": title, "content": content, "url": url}

            tokens = preprocess(content)
            doc_lengths[doc_id] = len(tokens)
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            for term, freq in tf.items():
                postings = inverted.setdefault(term, {})
                postings[doc_id] = freq

        N = len(documents)
        avgdl = sum(doc_lengths.values()) / N if N else 0.0

        # Compute document frequency and idf (BM25-style)
        doc_freq = {term: len(postings) for term, postings in inverted.items()}
        idf = {}
        for term, df in doc_freq.items():
            idf_val = math.log((N - df + 0.5) / (df + 0.5) + 1)
            idf[term] = idf_val

        self.index = Index(
            inverted_index=inverted,
            doc_lengths=doc_lengths,
            documents=documents,
            doc_freq=doc_freq,
            idf=idf,
            N=N,
            avgdl=avgdl,
        )

    def save_index(self, index_dir: str | Path | None = None) -> Path:
        index_dir = Path(index_dir) if index_dir else Path(config.INDEX_DIR)
        index_dir.mkdir(parents=True, exist_ok=True)
        out_path = index_dir / "index.pkl"
        with out_path.open("wb") as f:
            pickle.dump(self.index, f)
        # Save compact metadata for debugging
        meta = {
            "N": self.index.N,
            "avgdl": self.index.avgdl,
            "terms": len(self.index.inverted_index),
        }
        (index_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return out_path

    def load_index(self, index_dir: str | Path | None = None) -> None:
        index_dir = Path(index_dir) if index_dir else Path(config.INDEX_DIR)
        pkl = index_dir / "index.pkl"
        assert pkl.exists(), f"Index not found at {pkl}. Build it first."
        with pkl.open("rb") as f:
            self.index = pickle.load(f)

