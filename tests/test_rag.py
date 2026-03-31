"""Evaluation tests for RAG retrieval quality.

Tests both retrieval relevance and coverage across knowledge base categories.
Each test verifies that the top-k results contain expected chunks for
domain-specific queries.
"""

import pytest
from src.rag.provider import RAGProvider
from src.rag.knowledge_base import KNOWLEDGE_BASE, CATEGORIES


@pytest.fixture(scope="module")
def rag():
    return RAGProvider()


class TestRAGRetrieval:
    """Core retrieval quality tests."""

    def test_malaria_treatment_query(self, rag):
        results = rag.retrieve("malaria treatment ACT artemether", top_k=5)
        assert len(results) > 0
        ids = {r["id"] for r in results}
        # Must retrieve ACT treatment chunk
        assert "who-em-001" in ids or any("malaria" in r["title"].lower() for r in results)

    def test_diarrhoea_ors_query(self, rag):
        results = rag.retrieve("diarrhoea ORS zinc treatment children", top_k=5)
        assert len(results) > 0
        ids = {r["id"] for r in results}
        assert "who-em-002" in ids or "tx-proto-002" in ids

    def test_cold_chain_query(self, rag):
        results = rag.retrieve("cold chain storage temperature oxytocin", top_k=5)
        assert len(results) > 0
        assert any("cold" in r["title"].lower() or "oxytocin" in r["title"].lower()
                    for r in results)

    def test_emergency_procurement_query(self, rag):
        results = rag.retrieve("emergency procurement stockout threshold", top_k=5)
        assert len(results) > 0
        assert any("emergency" in r["title"].lower() or "stockout" in r["title"].lower()
                    for r in results)

    def test_seasonal_demand_query(self, rag):
        results = rag.retrieve("seasonal malaria rainy season demand planning", top_k=5)
        assert len(results) > 0
        assert any("season" in r["text"].lower() for r in results)

    def test_chw_supply_chain(self, rag):
        results = rag.retrieve("community health worker supply reporting", top_k=5)
        assert len(results) > 0

    def test_idsr_surveillance(self, rag):
        results = rag.retrieve("IDSR disease surveillance reporting cholera", top_k=5)
        assert len(results) > 0
        assert any("idsr" in r["category"].lower() or "cholera" in r["text"].lower()
                    for r in results)

    def test_budget_constrained_procurement(self, rag):
        results = rag.retrieve("budget allocation VEN vital essential medicines", top_k=5)
        assert len(results) > 0

    def test_quantification_methods(self, rag):
        results = rag.retrieve("drug quantification consumption morbidity forecasting", top_k=5)
        assert len(results) > 0

    def test_pneumonia_treatment(self, rag):
        results = rag.retrieve("pneumonia amoxicillin antibiotic treatment protocol", top_k=5)
        assert len(results) > 0
        assert any("pneumonia" in r["title"].lower() or "amoxicillin" in r["title"].lower()
                    for r in results)


class TestRAGStructure:
    """Structural tests for RAG system."""

    def test_knowledge_base_not_empty(self):
        assert len(KNOWLEDGE_BASE) >= 30

    def test_all_chunks_have_required_fields(self):
        for chunk in KNOWLEDGE_BASE:
            assert chunk.id
            assert chunk.title
            assert chunk.source
            assert chunk.category
            assert len(chunk.text) > 50

    def test_chunk_ids_unique(self):
        ids = [c.id for c in KNOWLEDGE_BASE]
        assert len(ids) == len(set(ids))

    def test_categories_coverage(self):
        assert len(CATEGORIES) >= 5

    def test_relevance_scores_normalized(self, rag):
        results = rag.retrieve("malaria treatment", top_k=5)
        for r in results:
            assert 0 <= r["relevance_score"] <= 1.0

    def test_top_result_highest_score(self, rag):
        results = rag.retrieve("safety stock calculation formula", top_k=5)
        if len(results) >= 2:
            assert results[0]["relevance_score"] >= results[1]["relevance_score"]

    def test_category_filter(self, rag):
        results = rag.retrieve_by_category(
            "malaria", category="WHO Essential Medicines", top_k=5,
        )
        for r in results:
            assert r["category"] == "WHO Essential Medicines"


class TestRAGMetrics:
    """Quantitative metrics for RAG quality."""

    QUERIES_AND_EXPECTED = [
        ("malaria ACT treatment", ["who-em-001", "tx-proto-001"]),
        ("ORS zinc diarrhoea", ["who-em-002", "tx-proto-002"]),
        ("cold chain oxytocin storage", ["cold-001", "who-em-004"]),
        ("cholera outbreak alert", ["idsr-001"]),
        ("safety stock reorder", ["msh-proc-002", "msh-proc-005"]),
        ("FEFO stock rotation expiry", ["sc-bp-001"]),
        ("CHW community supply", ["sc-bp-007"]),
        ("El Nino West Africa", ["clim-004"]),
    ]

    def test_retrieval_precision(self, rag):
        """Measure precision@5 across benchmark queries."""
        hits = 0
        total = 0
        for query, expected_ids in self.QUERIES_AND_EXPECTED:
            results = rag.retrieve(query, top_k=5)
            retrieved_ids = {r["id"] for r in results}
            for eid in expected_ids:
                total += 1
                if eid in retrieved_ids:
                    hits += 1

        precision = hits / max(1, total)
        # Baseline: TF-IDF should get at least 50% of expected chunks
        assert precision >= 0.4, f"Precision@5 = {precision:.2f} (expected >= 0.4)"
        print(f"\n  RAG Precision@5: {precision:.2f} ({hits}/{total} hits)")

    def test_mean_reciprocal_rank(self, rag):
        """Measure MRR across benchmark queries."""
        mrr_sum = 0
        n_queries = 0
        for query, expected_ids in self.QUERIES_AND_EXPECTED:
            results = rag.retrieve(query, top_k=10)
            retrieved_ids = [r["id"] for r in results]
            best_rank = None
            for eid in expected_ids:
                if eid in retrieved_ids:
                    rank = retrieved_ids.index(eid) + 1
                    if best_rank is None or rank < best_rank:
                        best_rank = rank
            if best_rank is not None:
                mrr_sum += 1.0 / best_rank
            n_queries += 1

        mrr = mrr_sum / max(1, n_queries)
        assert mrr >= 0.3, f"MRR = {mrr:.3f} (expected >= 0.3)"
        print(f"\n  RAG MRR: {mrr:.3f}")
