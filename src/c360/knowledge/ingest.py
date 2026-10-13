import hashlib
import re
from pathlib import Path
import yaml
from c360.config import settings
from c360.knowledge.vector_store import LocalVectorStore

KB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "knowledge_base"

def parse_frontmatter(content: str) -> tuple[dict, str]:
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return {}, content
    yaml_text = match.group(1)
    body = content[match.end():]
    metadata = yaml.safe_load(yaml_text) or {}
    return metadata, body

def chunk_markdown(body: str, min_chunk_len: int = 60) -> list[tuple[str, str]]:
    """Split markdown into header-anchored logical sections, merging empty/short header lines into the next section."""
    raw_sections = re.split(r"\n(?=#{1,4}\s+)", body)
    chunks = []
    pending_header = ""

    for sec in raw_sections:
        sec_str = sec.strip()
        if not sec_str:
            continue

        if pending_header:
            sec_str = f"{pending_header}\n\n{sec_str}"
            pending_header = ""

        lines = sec_str.splitlines()
        content_lines = [l for l in lines if not l.strip().startswith("#") and l.strip()]
        
        # If section is very short or has no content lines below headers, merge with next section
        if len(sec_str) < min_chunk_len or not content_lines:
            pending_header = sec_str
            continue

        header = lines[0].strip() if lines[0].startswith("#") else "General Section"
        chunks.append((header, sec_str))

    if pending_header:
        if chunks:
            h, prev_text = chunks[-1]
            chunks[-1] = (h, f"{prev_text}\n\n{pending_header}")
        else:
            chunks.append(("General Section", pending_header))

    return chunks

def ingest_knowledge_base():
    print("=== STARTING KNOWLEDGE BASE INGESTION PIPELINE ===")
    store = LocalVectorStore()
    md_files = list(KB_DIR.glob("**/*.md"))
    print(f"Found {len(md_files)} markdown documents in {KB_DIR}")

    total_chunks = 0
    doc_products = set()

    for filepath in md_files:
        rel_path = str(filepath.relative_to(KB_DIR.parent))
        with open(filepath, "r", encoding="utf-8") as f:
            raw_content = f.read()

        metadata, body = parse_frontmatter(raw_content)
        metadata["source_file"] = rel_path
        
        product_id = metadata.get("product")
        if product_id:
            doc_products.add(product_id)

        # Purge stale chunks for this source file before re-ingestion
        store.delete_by_source(rel_path)

        chunks = chunk_markdown(body)
        print(f"Processing {filepath.name}: Extracted {len(chunks)} chunk(s) [Product: {product_id}]")

        for idx, (header, text_content) in enumerate(chunks):
            # Generate deterministic chunk ID
            hash_input = f"{rel_path}_{header}_{idx}"
            chunk_id = "CHK_" + hashlib.md5(hash_input.encode("utf-8")).hexdigest()[:12]
            
            chunk_metadata = dict(metadata)
            chunk_metadata["section_header"] = header

            store.upsert_chunk(chunk_id, text_content, chunk_metadata)
            total_chunks += 1

    print(f"\nVector Store Ingestion Complete: {total_chunks} chunks stored in LocalVectorStore ({store.count()} total).")

    # --- Neo4j Graph Sync (GraphRAG Linkage) ---
    print("\n--- Syncing Knowledge Base Metadata to Neo4j Graph ---")
    try:
        driver = settings.get_driver()
        with driver.session(database=settings.database) as session:
            for pid in doc_products:
                cypher = """
                MATCH (p:Product {id: $pid})
                MERGE (kb:KnowledgeDoc {product_id: $pid})
                SET kb.updated_at = datetime(), kb.chunk_count = $chunk_count
                MERGE (p)-[:HAS_KNOWLEDGE_DOC]->(kb)
                """
                session.run(cypher, pid=pid, chunk_count=total_chunks)
                print(f"  Neo4j Graph Linkage: Product({pid}) -[:HAS_KNOWLEDGE_DOC]-> KnowledgeDoc({pid})")
        driver.close()
    except Exception as e:
        print(f"Notice: Neo4j graph sync skipped or database unavailable ({e}). Chunks ingested into Vector Store successfully.")

    print("=== INGESTION & GRAPH SYNC COMPLETE ===")

if __name__ == "__main__":
    ingest_knowledge_base()
