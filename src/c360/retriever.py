"""Compatibility shim for c360.knowledge.retriever."""
from c360.knowledge.retriever import *  # noqa: F401, F403
from c360.knowledge.retriever import GraphRAGRetriever, retriever, PRODUCT_KEYWORD_MAP

if __name__ == "__main__":
    res = retriever.retrieve("My Business Broad band is not working")
    print(f"Query: {res['query']}")
    print(f"Detected Product: {res['product_context']}")
    print(f"Top Result: {res['chunks'][0]['metadata']['source_file']}")
