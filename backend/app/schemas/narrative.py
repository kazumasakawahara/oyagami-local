from pydantic import BaseModel


class GraphNode(BaseModel):
    temp_id: str
    label: str
    properties: dict


class GraphRelationship(BaseModel):
    source_temp_id: str
    target_temp_id: str
    type: str
    properties: dict = {}


class ExtractedGraph(BaseModel):
    nodes: list[GraphNode] = []
    relationships: list[GraphRelationship] = []


class ExtractionRequest(BaseModel):
    text: str
    client_name: str | None = None


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    corrected_graph: ExtractedGraph | None = None


class SafetyCheckResult(BaseModel):
    is_violation: bool
    warning: str | None = None
    risk_level: str = "None"


class RegistrationResult(BaseModel):
    status: str
    client_name: str | None = None
    registered_count: int = 0
    registered_types: list[str] = []
    message: str | None = None


class QuickLogRequest(BaseModel):
    client_name: str
    note: str
    situation: str | None = None
    supporter_name: str = "system"
