from enum import Enum

from pydantic import BaseModel


class IntentCategory(str, Enum):
    EMERGENCY = "emergency"
    DATA_REGISTRATION = "data_registration"
    QUERY = "query"
    ANALYSIS = "analysis"
    GENERAL = "general"


class RoutingDecision(BaseModel):
    intent: IntentCategory
    target_agent: str
    reason: str
    requires_model_switch: bool = False
    target_model: str | None = None


class ChatMessage(BaseModel):
    type: str
    content: str | None = None
    agent: str | None = None
    session_id: str | None = None


class ChatRequest(BaseModel):
    content: str
    session_id: str


class ModelStatusResponse(BaseModel):
    ollama_available: bool
    neo4j_available: bool
    loaded_models: list[str] = []
    current_exclusive: str | None = None
    memory_usage_gb: float | None = None
