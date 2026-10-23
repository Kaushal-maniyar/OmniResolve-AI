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
        self.vllm_base_url = os.getenv(
            "VLLM_BASE_URL", "http://192.168.100.10:8000/v1")
        self.vllm_api_key = os.getenv(
            "VLLM_API_KEY", "llm-engineer-dev-key-change-in-prod")
        self.vllm_model = os.getenv("VLLM_MODEL", "qwen3.8-27b")

        # LLM provider configuration
        self.llm_provider = os.getenv("LLM_PROVIDER", "dgx").lower()
        self.llm_fallback_provider = os.getenv(
            "LLM_FALLBACK_PROVIDER", "groq"
        ).lower()

        # Groq configuration
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_base_url = os.getenv(
            "GROQ_BASE_URL",
            "https://api.groq.com/openai/v1"
        )
        self.groq_model = os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile"
        )

        if not self.password or self.password == "CHANGE_ME":
            raise ValueError(
                "NEO4J_PASSWORD is not configured in .env file! Please set a valid password."
            )

    def get_driver(self) -> Driver:
        return GraphDatabase.driver(self.uri, auth=(self.username, self.password))


settings = Settings()
