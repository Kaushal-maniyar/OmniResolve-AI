import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

# Locate repository root (.env location)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

class Settings:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")
        self.home = os.getenv("NEO4J_HOME")
        self.service_name = os.getenv("NEO4J_SERVICE_NAME", "neo4j")

        # vLLM Configuration
        self.vllm_base_url = os.getenv("VLLM_BASE_URL", "http://192.168.100.10:8000/v1")
        self.vllm_api_key = os.getenv("VLLM_API_KEY", "llm-engineer-dev-key-change-in-prod")
        self.vllm_model = os.getenv("VLLM_MODEL", "qwen3.8-27b")

        if not self.password or self.password == "CHANGE_ME":
            raise ValueError(
                "NEO4J_PASSWORD is not configured in .env file! Please set a valid password."
            )

    def get_driver(self) -> Driver:
        return GraphDatabase.driver(self.uri, auth=(self.username, self.password))

settings = Settings()
