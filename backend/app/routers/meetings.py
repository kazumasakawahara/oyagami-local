import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.lib.db_operations import register_to_database, run_query
from app.lib.embedding import embed_text
from app.lib.transcription import is_supported_format, transcribe_audio
from app.schemas.meeting import MeetingRecord, MeetingUploadResponse

router = APIRouter(prefix="/api/meetings", tags=["meetings"])
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "meetings"


@router.post("/upload", response_model=MeetingUploadResponse)
async def upload_meeting(
    file: UploadFile = File(...),
    client_name: str = Form(...),
    title: str = Form(""),
    note: str = Form(""),
):
    if not is_supported_format(file.filename):
        return MeetingUploadResponse(
            status="error", message=f"Unsupported format: {file.filename}"
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4().hex[:8]
    safe_filename = Path(file.filename).name.replace("..", "").replace("/", "").replace("\\", "")
    file_path = UPLOAD_DIR / f"{file_id}_{safe_filename}"
    content = await file.read()
    file_path.write_bytes(content)

    transcript = await transcribe_audio(str(file_path))

    graph = {
        "nodes": [
            {"temp_id": "c1", "label": "Client", "properties": {"name": client_name}},
            {
                "temp_id": "mr1",
                "label": "MeetingRecord",
                "properties": {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "title": title or file.filename,
                    "filePath": str(file_path),
                    "transcript": transcript or "",
                    "note": note,
                },
            },
        ],
        "relationships": [
            {
                "source_temp_id": "mr1",
                "target_temp_id": "c1",
                "type": "ABOUT",
                "properties": {},
            },
        ],
    }
    register_to_database(graph)

    if transcript:
        embedding = await embed_text(transcript)
        if embedding:
            run_query(
                "MATCH (mr:MeetingRecord {filePath: $path}) SET mr.textEmbedding = $embedding",
                {"path": str(file_path), "embedding": embedding},
            )

    return MeetingUploadResponse(
        status="success", transcript=transcript, meeting_id=file_id
    )


@router.get("/{client_name}", response_model=list[MeetingRecord])
async def list_meetings(client_name: str):
    records = run_query(
        """
        MATCH (mr:MeetingRecord)-[:ABOUT]->(c:Client {name: $name})
        RETURN mr.date AS date, mr.title AS title, mr.duration AS duration,
               mr.transcript AS transcript, mr.note AS note,
               mr.filePath AS file_path, c.name AS client_name
        ORDER BY mr.date DESC
        """,
        {"name": client_name},
    )
    return [MeetingRecord(**r) for r in records]
