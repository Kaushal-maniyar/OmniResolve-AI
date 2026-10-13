"""
c360: Customer 360 AI GraphRAG Framework
----------------------------------------
Sub-packages:
- c360.graph: Graph Database Management (Neo4j schema, seeding, verification, reset)
- c360.knowledge: Knowledge Base & Vector Store Engine (RAG ingestion, search, GraphRAG retriever)
- c360.agent: LangGraph Customer Support Agent (vLLM qwen3.8-27b, 4 Tools, Graph Persistence)
- c360.core: Core utilities & dataset validation
"""

import importlib

__all__ = [
    # Graph Domain
    "seed_database",
    "purge_database",
    "verify_database",
    "reset_demo_data",
    # Knowledge & Vector Store Domain
    "LocalVectorStore",
    "ingest_knowledge_base",
    "GraphRAGRetriever",
    "retriever",
    # Agent Domain
    "run_agent_graph",
    "CustomerSupportGraph",
    "VLLMClient",
    # Core Domain
    "validate_datasets",
    "read_csv",
]

_ATTR_MAP = {
    "seed_database": ("c360.graph.seed", "seed_database"),
    "purge_database": ("c360.graph.seed", "purge_database"),
    "verify_database": ("c360.graph.verify", "verify_database"),
    "reset_demo_data": ("c360.graph.reset", "reset_demo_data"),
    "LocalVectorStore": ("c360.knowledge.vector_store", "LocalVectorStore"),
    "ingest_knowledge_base": ("c360.knowledge.ingest", "ingest_knowledge_base"),
    "GraphRAGRetriever": ("c360.knowledge.retriever", "GraphRAGRetriever"),
    "retriever": ("c360.knowledge.retriever", "retriever"),
    "run_agent_graph": ("c360.agent.workflow", "run_agent_graph"),
    "CustomerSupportGraph": ("c360.agent.workflow", "CustomerSupportGraph"),
    "VLLMClient": ("c360.agent.client", "VLLMClient"),
    "validate_datasets": ("c360.core.data", "validate_datasets"),
    "read_csv": ("c360.core.data", "read_csv"),
}

def __getattr__(name: str):
    if name in _ATTR_MAP:
        mod_name, attr_name = _ATTR_MAP[name]
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr_name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
