"""Compatibility shim for c360.knowledge.ingest."""
from c360.knowledge.ingest import *  # noqa: F401, F403
from c360.knowledge.ingest import ingest_knowledge_base, chunk_markdown, parse_frontmatter

if __name__ == "__main__":
    ingest_knowledge_base()
