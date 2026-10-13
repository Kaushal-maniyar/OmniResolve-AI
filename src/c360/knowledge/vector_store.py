import json
import math
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "vector_store" / "kb_vectors.db"

STOPWORDS = {
    "my", "is", "not", "working", "the", "a", "an", "and", "or", "in", "on", "at", "to",
    "for", "with", "from", "by", "of", "it", "this", "that", "how", "what", "where", "why",
    "can", "do", "does", "i", "you", "we", "me", "have", "has", "had", "are", "was", "were"
}

class LocalVectorStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS kb_chunks (
                chunk_id TEXT PRIMARY KEY,
                product TEXT,
                category TEXT,
                issue_id TEXT,
                title TEXT,
                audience TEXT,
                version TEXT,
                source_file TEXT,
                text_content TEXT,
                embedding_json TEXT
            )
            """)

    @staticmethod
    def get_embedding(text: str, dim: int = 128) -> list[float]:
        """Generate a TF-IDF weighted semantic vector filtering out stopwords."""
        words = [w for w in re.findall(r"\w+", text.lower()) if w not in STOPWORDS]
        vec = [0.0] * dim
        if not words:
            # Fallback if text contains only stopwords
            words = re.findall(r"\w+", text.lower())
            if not words:
                return vec

        for i, word in enumerate(words):
            # Give higher weight to rare/distinct terms
            weight = 2.0 if len(word) > 3 else 1.0
            h = hash(word) % dim
            vec[h] += weight
            # Bigram hash
            if i > 0:
                h2 = hash(f"{words[i-1]}_{word}") % dim
                vec[h2] += 1.5

        # L2 Normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    @staticmethod
    def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        dot = sum(a * b for a, b in zip(vec1, vec2))
        return float(dot)

    def upsert_chunk(self, chunk_id: str, text_content: str, metadata: dict):
        embedding = self.get_embedding(text_content)
        embedding_json = json.dumps(embedding)
        with self._get_conn() as conn:
            conn.execute("""
            INSERT INTO kb_chunks (
                chunk_id, product, category, issue_id, title, audience, version, source_file, text_content, embedding_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                product = excluded.product,
                category = excluded.category,
                issue_id = excluded.issue_id,
                title = excluded.title,
                audience = excluded.audience,
                version = excluded.version,
                source_file = excluded.source_file,
                text_content = excluded.text_content,
                embedding_json = excluded.embedding_json
            """, (
                chunk_id,
                metadata.get("product"),
                metadata.get("category"),
                metadata.get("issue_id"),
                metadata.get("title"),
                metadata.get("audience"),
                metadata.get("version"),
                metadata.get("source_file"),
                text_content,
                embedding_json
            ))

    def delete_by_source(self, source_file: str):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM kb_chunks WHERE source_file = ?", (source_file,))

    def search(self, query: str, filters: dict = None, top_k: int = 3) -> list[dict]:
        query_vec = self.get_embedding(query)
        filters = filters or {}
        
        sql = "SELECT chunk_id, product, category, issue_id, title, audience, version, source_file, text_content, embedding_json FROM kb_chunks"
        conditions = []
        params = []

        if filters.get("product"):
            conditions.append("product = ?")
            params.append(filters["product"])
        if filters.get("category"):
            conditions.append("category = ?")
            params.append(filters["category"])
        if filters.get("issue_id"):
            conditions.append("issue_id = ?")
            params.append(filters["issue_id"])

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        with self._get_conn() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(sql, params).fetchall()

        results = []
        for row in rows:
            chunk_id, product, category, issue_id, title, audience, version, source_file, text_content, embedding_json = row
            chunk_vec = json.loads(embedding_json)
            score = self.cosine_similarity(query_vec, chunk_vec)
            results.append({
                "chunk_id": chunk_id,
                "score": round(score, 4),
                "metadata": {
                    "product": product,
                    "category": category,
                    "issue_id": issue_id,
                    "title": title,
                    "audience": audience,
                    "version": version,
                    "source_file": source_file,
                },
                "text_content": text_content
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def count(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT count(*) FROM kb_chunks").fetchone()[0]
