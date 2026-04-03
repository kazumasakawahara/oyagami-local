import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.team import process_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            user_text = msg.get("content", "")
            session_id = msg.get("session_id", session_id)
            result = await process_message(user_text, session_id)
            # Send routing info
            await websocket.send_json({
                "type": "routing",
                "agent": result["routing"].target_agent,
                "decision": result["routing"].intent.value,
                "reason": result["routing"].reason,
            })
            # Send response as stream chunks
            response_text = result["response"]
            for i in range(0, len(response_text), 20):
                chunk = response_text[i:i + 20]
                await websocket.send_json({
                    "type": "stream",
                    "content": chunk,
                    "agent": result["routing"].target_agent,
                })
            # Send metadata
            await websocket.send_json({
                "type": "metadata",
                "agents_used": result["metadata"]["agents_used"],
                "model_switches": result["metadata"]["model_switches"],
            })
            # Send done
            await websocket.send_json({"type": "done", "session_id": session_id})
    except WebSocketDisconnect:
        logger.info(f"Chat session {session_id} disconnected")
