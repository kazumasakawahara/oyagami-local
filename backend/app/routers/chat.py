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
            try:
                msg = json.loads(data)
                user_text = msg.get("content", "")
                session_id = msg.get("session_id", session_id)

                if not user_text:
                    await websocket.send_json({"type": "done", "session_id": session_id})
                    continue

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
            except json.JSONDecodeError:
                await websocket.send_json({"type": "stream", "content": "無効なメッセージ形式です。", "agent": "system"})
                await websocket.send_json({"type": "done", "session_id": session_id})
            except Exception as e:
                logger.error(f"Chat processing error: {e}", exc_info=True)
                await websocket.send_json({"type": "stream", "content": "エラーが発生しました。もう一度お試しください。", "agent": "system"})
                await websocket.send_json({"type": "done", "session_id": session_id})
    except WebSocketDisconnect:
        logger.info(f"Chat session {session_id} disconnected")
