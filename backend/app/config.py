from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "password"

    ollama_base_url: str = "http://localhost:11434"
    coordinator_model: str = "gemma4:12b"
    intake_model: str = "deepseek-r1:70b"
    validator_model: str = "gemma4:12b"
    analyst_model: str = "llama4:latest"
    cypher_model: str = "qwen3-coder:30b"
    embedding_model: str = "nomic-embed-text"

    backend_port: int = 8000
    frontend_port: int = 3000

    model_config = {"env_file": str(Path(__file__).resolve().parents[2] / ".env")}


settings = Settings()
