"""
Hybrid FAISS + BM25 RAG provider for health supply chain knowledge.

Uses TF-IDF vectors indexed in FAISS (IndexFlatIP) for semantic similarity
and rank_bm25 for keyword matching, merged via reciprocal rank fusion.
Indices are lazily initialized on first retrieve() call.
"""

from __future__ import annotations

import logging
from typing import Any

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer

from src.rag.knowledge_base import KNOWLEDGE_BASE, KnowledgeChunk

log = logging.getLogger(__name__)


class RAGProvider:
    """Hybrid FAISS + BM25 retrieval-augmented generation provider.

    Lazily builds indices on first retrieve() call. Returns deduplicated,
    relevance-scored chunks via reciprocal rank fusion of both retrieval methods.
    """

    def __init__(self):
        self._chunks: list[KnowledgeChunk] = KNOWLEDGE_BASE
        self._bm25: BM25Okapi | None = None
        self._faiss_index: faiss.IndexFlatIP | None = None
        self._tfidf: TfidfVectorizer | None = None
        self._tfidf_matrix: np.ndarray | None = None
        self._initialized = False

    def _initialize(self) -> None:
        """Build BM25 and FAISS indices from the knowledge base."""
        if self._initialized:
            return

        texts = [self._chunk_text(c) for c in self._chunks]

        # BM25 index
        tokenized = [t.lower().split() for t in texts]
        self._bm25 = BM25Okapi(tokenized)

        # TF-IDF + FAISS index
        self._tfidf = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
        )
        tfidf_matrix = self._tfidf.fit_transform(texts).toarray().astype(np.float32)

        # Normalize for cosine similarity via inner product
        norms = np.linalg.norm(tfidf_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1  # avoid division by zero
        tfidf_matrix = tfidf_matrix / norms
        self._tfidf_matrix = tfidf_matrix

        # Build FAISS inner-product index
        dim = tfidf_matrix.shape[1]
        self._faiss_index = faiss.IndexFlatIP(dim)
        self._faiss_index.add(tfidf_matrix)

        self._initialized = True
        log.info(
            "RAG indices built: %d chunks, %d TF-IDF features, FAISS dim=%d",
            len(self._chunks), tfidf_matrix.shape[1], dim,
        )

    @staticmethod
    def _chunk_text(chunk: KnowledgeChunk) -> str:
        """Combine chunk fields into a single searchable text."""
        return f"{chunk.title}. {chunk.category}. {chunk.text}"

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Retrieve top-k relevant knowledge chunks via hybrid search.

        Runs BM25 keyword search and FAISS semantic search in parallel,
        then merges results using reciprocal rank fusion.

        Parameters
        ----------
        query : str
            Natural language query.
        top_k : int
            Number of chunks to return.

        Returns
        -------
        list[dict]
            Each dict: {id, title, source, category, text, relevance_score}.
        """
        self._initialize()

        n = len(self._chunks)
        k_retrieve = min(n, top_k * 3)  # over-retrieve for fusion

        # BM25 retrieval
        bm25_scores = self._bm25.get_scores(query.lower().split())
        bm25_ranking = np.argsort(bm25_scores)[::-1][:k_retrieve]

        # FAISS retrieval
        query_vec = self._tfidf.transform([query]).toarray().astype(np.float32)
        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            query_vec = query_vec / query_norm
        faiss_scores, faiss_indices = self._faiss_index.search(query_vec, k_retrieve)
        faiss_ranking = faiss_indices[0]

        # Reciprocal Rank Fusion (RRF)
        # RRF score = sum(1 / (k + rank)) across retrieval methods
        rrf_k = 60  # standard RRF constant
        rrf_scores: dict[int, float] = {}

        for rank, idx in enumerate(bm25_ranking):
            idx = int(idx)
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (rrf_k + rank + 1)

        for rank, idx in enumerate(faiss_ranking):
            idx = int(idx)
            if idx < 0:  # FAISS can return -1 for empty results
                continue
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (rrf_k + rank + 1)

        # Sort by RRF score and take top_k
        sorted_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)
        top_indices = sorted_indices[:top_k]

        # Normalize scores to 0-1 range
        if top_indices:
            max_score = rrf_scores[top_indices[0]]
            min_score = rrf_scores[top_indices[-1]] if len(top_indices) > 1 else max_score
        else:
            max_score = min_score = 1.0

        results = []
        for idx in top_indices:
            chunk = self._chunks[idx]
            raw_score = rrf_scores[idx]
            # Normalize: best result gets 1.0
            if max_score > min_score:
                normalized = 0.5 + 0.5 * (raw_score - min_score) / (max_score - min_score)
            else:
                normalized = 1.0

            results.append({
                "id": chunk.id,
                "title": chunk.title,
                "source": chunk.source,
                "category": chunk.category,
                "text": chunk.text,
                "relevance_score": round(normalized, 4),
            })

        return results

    def retrieve_by_category(
        self, query: str, category: str, top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve chunks filtered to a specific category."""
        all_results = self.retrieve(query, top_k=top_k * 3)
        filtered = [r for r in all_results if r["category"] == category]
        return filtered[:top_k]

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    @property
    def categories(self) -> list[str]:
        return sorted(set(c.category for c in self._chunks))
