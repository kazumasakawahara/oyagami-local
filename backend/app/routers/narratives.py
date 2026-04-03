from io import BytesIO

from fastapi import APIRouter, File, UploadFile

from app.agents.intake import extract_from_text
from app.agents.validator import check_safety_compliance, validate_schema
from app.lib.db_operations import register_to_database
from app.lib.file_readers import read_file
from app.schemas.narrative import (
    ExtractionRequest,
    ExtractedGraph,
    RegistrationResult,
    SafetyCheckResult,
    ValidationResult,
)

router = APIRouter(prefix="/api/narratives", tags=["narratives"])


@router.post("/extract")
async def extract(request: ExtractionRequest):
    result = await extract_from_text(request.text, request.client_name)
    if result:
        return ExtractedGraph(**result)
    return None


@router.post("/validate", response_model=ValidationResult)
async def validate(graph: ExtractedGraph):
    return validate_schema(graph.model_dump())


@router.post("/register", response_model=RegistrationResult)
async def register(graph: ExtractedGraph):
    result = register_to_database(graph.model_dump())
    return RegistrationResult(**result)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    text = read_file(BytesIO(content), file.filename)
    return {"filename": file.filename, "text": text}


@router.post("/safety-check", response_model=SafetyCheckResult)
async def safety_check(request: ExtractionRequest):
    return await check_safety_compliance(request.text, request.client_name)
