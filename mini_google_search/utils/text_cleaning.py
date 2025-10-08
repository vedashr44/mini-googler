import re
from typing import List


_STOPWORDS = {
    "a","an","the","and","or","but","if","then","else","when","at","by","for","from","in","into","of","on","to","with","as","is","are","was","were","be","been","being","it","its","that","this","these","those","will","would","can","could","should","may","might","we","you","they","he","she","them","his","her","their","our","us","i"
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> List[str]:
    if not text:
        return []
    text = normalize_text(text)
    return text.split()


def remove_stopwords(tokens: List[str]) -> List[str]:
    return [t for t in tokens if t not in _STOPWORDS]


def simple_stem(token: str) -> str:
    # Naive and fast stemming to keep dependencies minimal
    for suf in ("ing", "ed", "ly", "s"):
        if token.endswith(suf) and len(token) > len(suf) + 2:
            return token[: -len(suf)]
    return token


def lemmatize(tokens: List[str]) -> List[str]:
    return [simple_stem(t) for t in tokens]


def preprocess(text: str) -> List[str]:
    return lemmatize(remove_stopwords(tokenize(text)))

