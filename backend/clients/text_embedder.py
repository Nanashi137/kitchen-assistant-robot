import json
import math
import re
from collections import defaultdict
from typing import Dict, List, Optional, Union

import httpx
from scipy.sparse import csr_matrix


class DenseEmbedder:
    def __init__(self, url: str, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.timeout = timeout

    async def embed(self, texts: Union[str, List[str]]) -> List[List[float]]:
        if isinstance(texts, str):
            inputs = [texts]
        elif isinstance(texts, list) and all(isinstance(t, str) for t in texts):
            inputs = texts
        else:
            raise TypeError("texts must be a str or List[str]")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.url}/embed",
                json={"inputs": inputs},
            )

        resp.raise_for_status()
        embeddings = resp.json()

        if not isinstance(embeddings, list):
            raise ValueError("Unexpected response format from TEI server")

        return embeddings


class SparseEmbedder:
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25,
    ):
        self.k1 = k1
        self.b = b
        self.epsilon = epsilon

        # Learned parameters
        self.corpus_size: int = 0
        self.avgdl: float = 0.0
        self.idf: Dict[str, float] = {}
        self.term_to_index: Dict[str, int] = {}
        self.term_document_frequencies: Dict[str, int] = {}

    def preprocess(self, text: str) -> str:
        text = str(text).lower()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s]", "", text)
        text = text.strip()
        return text

    def _tokenize(self, text: str) -> List[str]:
        cleaned = self.preprocess(text)
        if not cleaned:
            return []
        return cleaned.split()

    def fit(self, corpus: List[str]):
        if not corpus:
            return

        tokenized_corpus = [self._tokenize(doc) for doc in corpus]

        # Compute statistics
        term_doc_freq = defaultdict(int)
        total_word_count = 0

        for tokens in tokenized_corpus:
            seen = set()
            total_word_count += len(tokens)
            for term in tokens:
                if term not in seen:
                    term_doc_freq[term] += 1
                    seen.add(term)

        self.corpus_size = len(corpus)
        self.avgdl = (
            total_word_count / self.corpus_size if self.corpus_size > 0 else 1.0
        )

        idf_sum = 0.0
        negative_idfs = []

        for term, df in term_doc_freq.items():
            idf = math.log((self.corpus_size - df + 0.5) / (df + 0.5))
            self.idf[term] = idf
            idf_sum += idf
            if idf < 0:
                negative_idfs.append(term)

        if self.idf:
            avg_idf = idf_sum / len(self.idf)
            eps = self.epsilon * avg_idf
            for term in negative_idfs:
                self.idf[term] = eps

        self.term_to_index = {term: i for i, term in enumerate(sorted(self.idf.keys()))}
        self.term_document_frequencies = term_doc_freq

    def embed(
        self, texts: Union[str, List[str]], normalize: bool = False
    ) -> Union[Dict[int, float], List[Dict[int, float]]]:
        single_input = isinstance(texts, str)
        if single_input:
            texts = [texts]

        embeddings = []

        for text in texts:
            tokens = self._tokenize(text)
            if not tokens or not self.idf:
                embeddings.append({})
                continue

            doc_len = len(tokens)
            freq = defaultdict(int)
            for t in tokens:
                freq[t] += 1

            sparse_dict = {}
            for term, count in freq.items():
                if term not in self.idf:
                    continue
                idf_val = self.idf[term]
                numerator = count * (self.k1 + 1)
                denominator = count + self.k1 * (
                    1 - self.b + self.b * doc_len / self.avgdl
                )
                weight = idf_val * (numerator / denominator)
                idx = self.term_to_index.get(term)
                if idx is not None:
                    sparse_dict[idx] = weight

            if normalize and sparse_dict:
                norm = math.sqrt(sum(v**2 for v in sparse_dict.values()))
                if norm > 0:
                    for k in sparse_dict:
                        sparse_dict[k] /= norm

            embeddings.append(sparse_dict)

        return embeddings[0] if single_input else embeddings

    def get_vocabulary_size(self) -> int:
        return len(self.term_to_index)

    def save(self, path: str):
        data = {
            "k1": self.k1,
            "b": self.b,
            "epsilon": self.epsilon,
            "corpus_size": self.corpus_size,
            "avgdl": self.avgdl,
            "idf": self.idf,
            "term_to_index": self.term_to_index,
            "term_document_frequencies": self.term_document_frequencies,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        instance = cls(k1=data["k1"], b=data["b"], epsilon=data["epsilon"])
        instance.corpus_size = data["corpus_size"]
        instance.avgdl = data["avgdl"]
        instance.idf = data["idf"]
        instance.term_to_index = data["term_to_index"]
        instance.term_document_frequencies = data["term_document_frequencies"]
        return instance
