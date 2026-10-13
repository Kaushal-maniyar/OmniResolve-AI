import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from c360.knowledge.ingest import ingest_knowledge_base
from c360.knowledge.retriever import retriever
from c360.knowledge.vector_store import LocalVectorStore

def test_kb_ingestion_and_idempotency():
    """Verify KB documents can be ingested without creating duplicates on re-ingestion."""
    ingest_knowledge_base()
    store = LocalVectorStore()
    initial_count = store.count()
    assert initial_count > 0, "Vector store must contain ingested chunks"

    # Re-ingest and verify exact same chunk count
    ingest_knowledge_base()
    assert store.count() == initial_count, "Re-ingestion must be idempotent with 0 duplicates"

def test_product_isolation_filtering():
    """Verify querying Product P001 (Business Broadband) does NOT return Product P002 (ILL) chunks."""
    res_p001 = retriever.retrieve("packet loss drop ping", product_id="P001")
    for chunk in res_p001["chunks"]:
        assert chunk["metadata"]["product"] == "P001", "Product P001 search must strictly isolate P001 chunks"

    res_p002 = retriever.retrieve("packet loss drop ping", product_id="P002")
    for chunk in res_p002["chunks"]:
        assert chunk["metadata"]["product"] == "P002", "Product P002 search must strictly isolate P002 chunks"

def test_semantic_retrieval_relevance():
    """Verify relevant query returns matching troubleshooting section with high similarity score."""
    res = retriever.retrieve("red optical LOS light on modem", product_id="P001")
    assert res["results_count"] > 0
    top_chunk = res["chunks"][0]
    assert "BB-001" in top_chunk["metadata"]["issue_id"] or "RED" in top_chunk["text_content"].upper()
    assert top_chunk["score"] > 0.2
