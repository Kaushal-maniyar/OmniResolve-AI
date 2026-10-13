import re
from c360.config import settings
from c360.knowledge.vector_store import LocalVectorStore

PRODUCT_KEYWORD_MAP = {
    "P005": ["wifi", "wi-fi", "wi fi", "wireless", "802.1x", "ssid", "campus wifi"],
    "P001": ["broadband", "broad band", "business broadband", "business broad band", "ont", "modem", "los light"],
    "P002": ["leased line", "leased", "ill", "packet loss", "circuit"],
    "P003": ["sip trunk", "sip", "voip", "one-way audio", "one way audio", "codec", "call drops"],
    "P004": ["sbc", "oracle sbc", "oracle", "border controller", "registration failure"]
}

class GraphRAGRetriever:
    def __init__(self):
        self.vector_store = LocalVectorStore()

    @staticmethod
    def infer_product_id(query: str) -> str:
        """Automatically detect Product ID from query keywords if product_id is not explicitly passed."""
        q_lower = query.lower()
        # Normalize broad band -> broadband
        q_norm = re.sub(r"\bbroad\s+band\b", "broadband", q_lower)
        q_norm = re.sub(r"\bwi\s+fi\b", "wifi", q_norm)

        for pid, keywords in PRODUCT_KEYWORD_MAP.items():
            for kw in keywords:
                if kw in q_norm or re.search(r"\b" + re.escape(kw) + r"\b", q_norm):
                    return pid
        return None

    def get_product_context_from_graph(self, product_id: str) -> dict:
        """Fetch product details and ownership context from Neo4j Graph Database."""
        if not product_id:
            return {}
        driver = settings.get_driver()
        try:
            with driver.session(database=settings.database) as session:
                result = session.run(
                    "MATCH (p:Product {id: $pid}) RETURN p.id AS id, p.name AS name",
                    pid=product_id
                ).single()
                if result:
                    return {"product_id": result["id"], "product_name": result["name"]}
                return {"product_id": product_id, "product_name": "Detected Product"}
        except Exception as e:
            return {"product_id": product_id, "product_name": "Product"}
        finally:
            driver.close()

    def retrieve(self, query: str, product_id: str = None, category: str = None, top_k: int = 15) -> dict:
        # Auto-detect product_id if empty
        if not product_id:
            product_id = self.infer_product_id(query)

        filters = {}
        graph_product = {}
        if product_id:
            filters["product"] = product_id
            graph_product = self.get_product_context_from_graph(product_id)
        if category:
            filters["category"] = category

        chunks = self.vector_store.search(query, filters=filters, top_k=top_k)

        # Check for low similarity / missing knowledge
        escalation_recommended = False
        if not chunks or (chunks and chunks[0]["score"] < 0.15):
            escalation_recommended = True

        return {
            "query": query,
            "product_context": graph_product,
            "applied_filters": filters,
            "escalation_recommended": escalation_recommended,
            "results_count": len(chunks),
            "chunks": chunks
        }

retriever = GraphRAGRetriever()

if __name__ == "__main__":
    res = retriever.retrieve("My Business Broad band is not working")
    print(f"Query: {res['query']}")
    print(f"Detected Product: {res['product_context']}")
    print(f"Top Result: {res['chunks'][0]['metadata']['source_file']}")
