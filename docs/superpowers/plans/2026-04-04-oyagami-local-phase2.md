# oyagami-local Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add semantic search, ecomap visualization, meeting records with audio transcription, Japanese chunking, and E2E tests to complete the full feature set.

**Architecture:** Extends Phase 1 monorepo. Backend adds 3 routers + 2 library modules. Frontend adds 3 pages. Whisper for local audio transcription.

**Tech Stack:** Phase 1 stack + fugashi (Japanese chunking), openai-whisper (audio transcription), React Flow (ecomap visualization)

**Spec:** `docs/superpowers/specs/2026-04-04-oyagami-local-design.md` (Phase 2 section)

**Reference project:** `~/Dev-Work/neo4j-agno-agent/` (ecomap: `skills/ecomap_generator/drawio_engine.py`, audio: `lib/embedding.py`)

---

## File Map

### Backend — New/Modified Files

| File | Responsibility |
|------|---------------|
| `app/lib/chunking.py` | 日本語テキストのチャンク分割（fugashi + 文境界認識） |
| `app/lib/transcription.py` | 音声→テキスト文字起こし（openai-whisper） |
| `app/lib/ecomap.py` | エコマップデータ取得 + draw.io XML 生成 |
| `app/lib/embedding.py` | (修正) セマンティック検索エンドポイント用の高レベル関数追加 |
| `app/routers/search.py` | (修正) POST /api/search/semantic エンドポイント追加 |
| `app/routers/ecomap.py` | GET /api/ecomap/{name} エコマップ生成 |
| `app/routers/meetings.py` | POST /api/meetings/upload, GET /api/meetings/{name} |
| `app/schemas/ecomap.py` | エコマップ関連の Pydantic モデル |
| `app/schemas/meeting.py` | 面談記録関連の Pydantic モデル |
| `tests/lib/test_chunking.py` | チャンキングの単体テスト |
| `tests/lib/test_transcription.py` | 文字起こしのテスト |
| `tests/routers/test_ecomap.py` | エコマップ API テスト |
| `tests/routers/test_meetings.py` | 面談記録 API テスト |
| `tests/routers/test_search_semantic.py` | セマンティック検索 API テスト |

### Frontend — New Files

| File | Responsibility |
|------|---------------|
| `src/app/search/page.tsx` | セマンティック検索画面 |
| `src/app/ecomap/page.tsx` | エコマップ生成画面 |
| `src/app/meetings/page.tsx` | 面談記録管理画面 |
| `src/components/domain/EcomapViewer.tsx` | React Flow でエコマップを描画 |
| `src/components/domain/SearchResults.tsx` | 検索結果リスト（スコア付き） |
| `src/components/domain/AudioUploader.tsx` | 音声ファイルアップロード + 文字起こし状態表示 |

---

## Task 1: 日本語チャンキング（fugashi）

**Files:**
- Create: `backend/app/lib/chunking.py`
- Create: `backend/tests/lib/test_chunking.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/lib/test_chunking.py
from app.lib.chunking import split_into_chunks, split_at_sentence_boundaries


def test_short_text_no_split():
    """512トークン未満のテキストは分割しない"""
    text = "短いテスト文です。"
    chunks = split_into_chunks(text, max_tokens=512)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_long_text_splits():
    """512トークン超のテキストを文単位で分割"""
    sentences = ["これはテスト文です。"] * 200  # 十分長いテキスト
    text = "".join(sentences)
    chunks = split_into_chunks(text, max_tokens=512)
    assert len(chunks) > 1
    # 全チャンクを結合すると元のテキストに戻る（オーバーラップ除く）
    for chunk in chunks:
        assert len(chunk) > 0


def test_sentence_boundary_detection():
    """文境界で正しく分割される"""
    text = "今日は天気が良い。明日は雨かもしれない。来週は晴れるだろう。"
    sentences = split_at_sentence_boundaries(text)
    assert len(sentences) == 3
    assert sentences[0] == "今日は天気が良い。"
    assert sentences[1] == "明日は雨かもしれない。"
    assert sentences[2] == "来週は晴れるだろう。"


def test_chunk_overlap():
    """チャンク間にオーバーラップがある"""
    sentences = [f"これは文{i}です。" for i in range(100)]
    text = "".join(sentences)
    chunks = split_into_chunks(text, max_tokens=50, overlap_sentences=1)
    if len(chunks) > 1:
        # 2番目のチャンクの先頭が、1番目のチャンクの末尾と重複
        assert any(s in chunks[1] for s in chunks[0].split("。") if s)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/lib/test_chunking.py -v
```

- [ ] **Step 3: Implement chunking.py**

```python
# backend/app/lib/chunking.py
"""Japanese text chunking using fugashi for sentence boundary detection."""
import re
import logging

logger = logging.getLogger(__name__)

# Sentence-ending patterns for Japanese
SENTENCE_ENDINGS = re.compile(r"(?<=[。！？\n])")


def split_at_sentence_boundaries(text: str) -> list[str]:
    """Split text into sentences at Japanese sentence boundaries.

    Uses regex for 。！？ and newlines. Does not require fugashi
    for this step (morphological analysis is for token counting).
    """
    parts = SENTENCE_ENDINGS.split(text)
    sentences = [p.strip() for p in parts if p.strip()]
    return sentences


def count_tokens_approximate(text: str) -> int:
    """Approximate token count for Japanese text.

    Japanese characters are roughly 1-2 tokens each.
    This is a fast approximation; exact counting would require
    the model's tokenizer.
    """
    # Rough heuristic: each Japanese character ≈ 1.5 tokens,
    # ASCII words ≈ 1 token per word
    jp_chars = sum(1 for c in text if ord(c) > 0x3000)
    ascii_words = len(re.findall(r"[a-zA-Z0-9]+", text))
    return int(jp_chars * 1.5 + ascii_words)


def split_into_chunks(
    text: str,
    max_tokens: int = 512,
    overlap_sentences: int = 1,
) -> list[str]:
    """Split text into chunks at sentence boundaries.

    Args:
        text: Input text to chunk
        max_tokens: Maximum approximate tokens per chunk
        overlap_sentences: Number of sentences to overlap between chunks

    Returns:
        List of text chunks. Short texts (< max_tokens) return as single chunk.
    """
    if count_tokens_approximate(text) <= max_tokens:
        return [text]

    sentences = split_at_sentence_boundaries(text)
    if not sentences:
        return [text]

    chunks = []
    current_sentences: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = count_tokens_approximate(sentence)

        if current_tokens + sentence_tokens > max_tokens and current_sentences:
            # Save current chunk
            chunks.append("".join(current_sentences))

            # Start new chunk with overlap
            if overlap_sentences > 0 and len(current_sentences) >= overlap_sentences:
                current_sentences = current_sentences[-overlap_sentences:]
                current_tokens = sum(
                    count_tokens_approximate(s) for s in current_sentences
                )
            else:
                current_sentences = []
                current_tokens = 0

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    # Don't forget the last chunk
    if current_sentences:
        chunks.append("".join(current_sentences))

    return chunks if chunks else [text]
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/lib/test_chunking.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/lib/chunking.py backend/tests/lib/test_chunking.py
git commit -m "feat: add Japanese text chunking with sentence boundary detection"
```

---

## Task 2: セマンティック検索 API + 画面

**Files:**
- Modify: `backend/app/routers/search.py`
- Modify: `backend/app/lib/embedding.py`
- Create: `backend/app/schemas/search.py`
- Create: `backend/tests/routers/test_search_semantic.py`
- Create: `frontend/src/app/search/page.tsx`
- Create: `frontend/src/components/domain/SearchResults.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/components/domain/Sidebar.tsx`

- [ ] **Step 1: Create search schemas**

```python
# backend/app/schemas/search.py
from pydantic import BaseModel


class SemanticSearchRequest(BaseModel):
    query: str
    index_name: str = "support_log_embedding"
    top_k: int = 10
    client_name: str | None = None


class SemanticSearchResult(BaseModel):
    score: float
    node_label: str
    properties: dict
    client_name: str | None = None
```

- [ ] **Step 2: Add semantic search endpoint to search router**

Add to `backend/app/routers/search.py`:

```python
from app.lib.embedding import embed_text, semantic_search
from app.schemas.search import SemanticSearchRequest, SemanticSearchResult

@router.post("/semantic", response_model=list[SemanticSearchResult])
async def search_semantic(request: SemanticSearchRequest):
    """Semantic search using vector embeddings."""
    query_embedding = await embed_text(request.query)
    if not query_embedding:
        return []

    results = semantic_search(
        query_embedding=query_embedding,
        index_name=request.index_name,
        top_k=request.top_k,
    )

    return [
        SemanticSearchResult(
            score=r["score"],
            node_label=request.index_name.replace("_embedding", ""),
            properties=r["node"],
            client_name=r["node"].get("name"),
        )
        for r in results
    ]
```

- [ ] **Step 3: Write API test**

```python
# backend/tests/routers/test_search_semantic.py
def test_semantic_search_endpoint(client):
    resp = client.post("/api/search/semantic", json={
        "query": "パニック時の対応",
        "index_name": "support_log_embedding",
        "top_k": 5,
    })
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

- [ ] **Step 4: Create frontend search page**

Create `frontend/src/app/search/page.tsx` with:
- テキスト入力（検索クエリ）
- インデックス選択ドロップダウン（support_log, care_preference, ng_action, client_summary）
- 件数制限スライダー
- 検索結果をカード形式で表示（スコア付き）

Create `frontend/src/components/domain/SearchResults.tsx` — results list component.

- [ ] **Step 5: Update API client and sidebar**

Add `search.semantic()` to `frontend/src/lib/api.ts`.
Add `/search` to Sidebar navigation items.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add semantic search with vector embeddings (API + frontend)"
```

---

## Task 3: エコマップ — バックエンド

**Files:**
- Create: `backend/app/lib/ecomap.py`
- Create: `backend/app/schemas/ecomap.py`
- Create: `backend/app/routers/ecomap.py`
- Create: `backend/tests/routers/test_ecomap.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create ecomap schemas**

```python
# backend/app/schemas/ecomap.py
from pydantic import BaseModel


class EcomapNode(BaseModel):
    id: str
    label: str
    category: str
    properties: dict


class EcomapEdge(BaseModel):
    source: str
    target: str
    label: str


class EcomapData(BaseModel):
    client_name: str
    template: str
    nodes: list[EcomapNode]
    edges: list[EcomapEdge]


class EcomapTemplate(BaseModel):
    id: str
    name: str
    description: str
```

- [ ] **Step 2: Implement ecomap.py library**

Port logic from `~/Dev-Work/neo4j-agno-agent/skills/ecomap_generator/drawio_engine.py`.
Key adaptations:
- Remove draw.io XML generation (frontend will render with React Flow)
- Keep Neo4j query patterns for fetching related nodes
- Return structured data (EcomapData) instead of XML
- Support 4 templates: full_view, support_meeting, emergency, handover
- 9 categories with color codes: ngActions(red), carePreferences(green), keyPersons(blue), guardians(purple), hospitals(cyan), certificates(orange), conditions(yellow), supporters(teal), services(pink)

```python
# backend/app/lib/ecomap.py
"""Ecomap data generation from Neo4j graph data."""
import logging
from app.lib.db_operations import run_query
from app.schemas.ecomap import EcomapData, EcomapEdge, EcomapNode

logger = logging.getLogger(__name__)

TEMPLATES = {
    "full_view": {
        "name": "全体像",
        "description": "クライアントの全支援ネットワーク",
        "categories": [
            "conditions", "ngActions", "carePreferences", "keyPersons",
            "guardians", "hospitals", "certificates", "supporters", "services",
        ],
    },
    "support_meeting": {
        "name": "支援会議用",
        "description": "支援者・機関を中心に表示",
        "categories": ["keyPersons", "supporters", "services", "guardians"],
    },
    "emergency": {
        "name": "緊急時",
        "description": "禁忌事項・緊急連絡先を優先表示",
        "categories": ["ngActions", "carePreferences", "keyPersons", "hospitals", "guardians"],
    },
    "handover": {
        "name": "引き継ぎ用",
        "description": "ケア指示・医療情報を中心に表示",
        "categories": [
            "conditions", "ngActions", "carePreferences",
            "hospitals", "certificates", "keyPersons",
        ],
    },
}

CATEGORY_COLORS = {
    "ngActions": "#ef4444",
    "carePreferences": "#22c55e",
    "keyPersons": "#3b82f6",
    "guardians": "#8b5cf6",
    "hospitals": "#06b6d4",
    "certificates": "#f97316",
    "conditions": "#eab308",
    "supporters": "#14b8a6",
    "services": "#ec4899",
}

# Category → (Cypher pattern, node variable, relationship label)
CATEGORY_QUERIES = {
    "conditions": ("(c)-[:HAS_CONDITION]->(n:Condition)", "n", "HAS_CONDITION"),
    "ngActions": ("(c)-[:MUST_AVOID]->(n:NgAction)", "n", "MUST_AVOID"),
    "carePreferences": ("(c)-[:REQUIRES]->(n:CarePreference)", "n", "REQUIRES"),
    "keyPersons": ("(c)-[:HAS_KEY_PERSON]->(n:KeyPerson)", "n", "HAS_KEY_PERSON"),
    "guardians": ("(c)-[:HAS_LEGAL_REP]->(n:Guardian)", "n", "HAS_LEGAL_REP"),
    "hospitals": ("(c)-[:TREATED_AT]->(n:Hospital)", "n", "TREATED_AT"),
    "certificates": ("(c)-[:HAS_CERTIFICATE]->(n:Certificate)", "n", "HAS_CERTIFICATE"),
    "supporters": ("(s:Supporter)-[:LOGGED]->(:SupportLog)-[:ABOUT]->(c)", "s", "SUPPORTS"),
    "services": ("(c)-[:USES_SERVICE]->(n:ServiceProvider)", "n", "USES_SERVICE"),
}


def fetch_ecomap_data(client_name: str, template: str = "full_view") -> EcomapData:
    """Fetch ecomap graph data from Neo4j."""
    tmpl = TEMPLATES.get(template, TEMPLATES["full_view"])
    categories = tmpl["categories"]

    nodes = [EcomapNode(
        id="client",
        label=client_name,
        category="client",
        properties={},
    )]
    edges = []

    for cat in categories:
        if cat not in CATEGORY_QUERIES:
            continue
        pattern, var, rel_label = CATEGORY_QUERIES[cat]
        query = f"""
            MATCH {pattern}
            WHERE c.name = $name
            RETURN {var} AS node, elementId({var}) AS eid
        """
        records = run_query(query, {"name": client_name})
        for r in records:
            node_data = dict(r["node"])
            node_id = r["eid"]
            display = node_data.get("name") or node_data.get("action") or node_data.get("instruction") or node_data.get("type") or str(node_data)
            nodes.append(EcomapNode(
                id=node_id,
                label=str(display)[:40],
                category=cat,
                properties=node_data,
            ))
            edges.append(EcomapEdge(
                source="client",
                target=node_id,
                label=rel_label,
            ))

    return EcomapData(
        client_name=client_name,
        template=template,
        nodes=nodes,
        edges=edges,
    )
```

- [ ] **Step 3: Implement ecomap router**

```python
# backend/app/routers/ecomap.py
from fastapi import APIRouter, Query
from app.lib.ecomap import fetch_ecomap_data, TEMPLATES
from app.schemas.ecomap import EcomapData, EcomapTemplate

router = APIRouter(prefix="/api/ecomap", tags=["ecomap"])


@router.get("/templates", response_model=list[EcomapTemplate])
async def list_templates():
    return [
        EcomapTemplate(id=k, name=v["name"], description=v["description"])
        for k, v in TEMPLATES.items()
    ]


@router.get("/{client_name}", response_model=EcomapData)
async def get_ecomap(client_name: str, template: str = Query("full_view")):
    return fetch_ecomap_data(client_name, template)
```

- [ ] **Step 4: Register router in main.py**

```python
from app.routers import ecomap
app.include_router(ecomap.router)
```

- [ ] **Step 5: Write test**

```python
# backend/tests/routers/test_ecomap.py
def test_list_templates(client):
    resp = client.get("/api/ecomap/templates")
    assert resp.status_code == 200
    templates = resp.json()
    assert len(templates) == 4
    ids = [t["id"] for t in templates]
    assert "full_view" in ids
    assert "emergency" in ids

def test_get_ecomap(client):
    resp = client.get("/api/ecomap/テスト太郎?template=full_view")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert data["template"] == "full_view"
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add ecomap backend with Neo4j data fetch and 4 templates"
```

---

## Task 4: エコマップ — フロントエンド

**Files:**
- Create: `frontend/src/app/ecomap/page.tsx`
- Create: `frontend/src/components/domain/EcomapViewer.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/components/domain/Sidebar.tsx`

- [ ] **Step 1: Install React Flow**

```bash
cd ~/Dev-Work/oyagami-local/frontend
pnpm add @xyflow/react
```

- [ ] **Step 2: Add types and API client**

Add to `types.ts`:
```typescript
export interface EcomapNode {
  id: string;
  label: string;
  category: string;
  properties: Record<string, unknown>;
}
export interface EcomapEdge {
  source: string;
  target: string;
  label: string;
}
export interface EcomapData {
  client_name: string;
  template: string;
  nodes: EcomapNode[];
  edges: EcomapEdge[];
}
export interface EcomapTemplate {
  id: string;
  name: string;
  description: string;
}
```

Add to `api.ts`:
```typescript
ecomap: {
  templates: () => fetchApi<EcomapTemplate[]>("/api/ecomap/templates"),
  get: (name: string, template?: string) =>
    fetchApi<EcomapData>(`/api/ecomap/${encodeURIComponent(name)}?template=${template || "full_view"}`),
},
```

- [ ] **Step 3: Create EcomapViewer component**

`frontend/src/components/domain/EcomapViewer.tsx`:
- React Flow でノードとエッジを描画
- カテゴリ別の色分け（CATEGORY_COLORS に対応）
- クライアントノードを中心に放射状レイアウト
- ノードクリックで詳細表示（properties をポップオーバー）
- ズーム/パン対応

- [ ] **Step 4: Create ecomap page**

`frontend/src/app/ecomap/page.tsx`:
- クライアント選択ドロップダウン（api.clients.list()）
- テンプレート選択ラジオボタン（api.ecomap.templates()）
- EcomapViewer コンポーネント
- カテゴリ凡例（色付きバッジ）

- [ ] **Step 5: Update sidebar**

Add `/ecomap` to Sidebar navigation under 「活用」 section.

- [ ] **Step 6: Verify build and commit**

```bash
cd ~/Dev-Work/oyagami-local/frontend && pnpm build
git add -A
git commit -m "feat: add ecomap visualization with React Flow and category colors"
```

---

## Task 5: 音声文字起こし（Whisper）

**Files:**
- Create: `backend/app/lib/transcription.py`
- Create: `backend/tests/lib/test_transcription.py`
- Modify: `backend/pyproject.toml` (add openai-whisper)

- [ ] **Step 1: Install whisper**

```bash
cd ~/Dev-Work/oyagami-local/backend
uv add openai-whisper
```

Note: openai-whisper requires ffmpeg. Verify: `brew install ffmpeg`

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/lib/test_transcription.py
from app.lib.transcription import SUPPORTED_AUDIO_FORMATS


def test_supported_formats():
    assert ".mp3" in SUPPORTED_AUDIO_FORMATS
    assert ".wav" in SUPPORTED_AUDIO_FORMATS
    assert ".m4a" in SUPPORTED_AUDIO_FORMATS


def test_is_supported_format():
    from app.lib.transcription import is_supported_format
    assert is_supported_format("test.mp3")
    assert is_supported_format("meeting.wav")
    assert not is_supported_format("document.pdf")
```

- [ ] **Step 3: Implement transcription.py**

```python
# backend/app/lib/transcription.py
"""Audio transcription using OpenAI Whisper (local model)."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".webm"}
WHISPER_MODEL = "base"  # Options: tiny, base, small, medium, large


def is_supported_format(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_AUDIO_FORMATS


async def transcribe_audio(audio_path: str, language: str = "ja") -> str | None:
    """Transcribe audio file to text using Whisper.

    Args:
        audio_path: Path to audio file
        language: Language code (default: Japanese)

    Returns:
        Transcribed text or None on failure
    """
    try:
        import whisper

        model = whisper.load_model(WHISPER_MODEL)
        result = model.transcribe(audio_path, language=language)
        text = result.get("text", "")
        logger.info(f"Transcribed {audio_path}: {len(text)} chars")
        return text
    except ImportError:
        logger.error("openai-whisper is not installed. Run: uv add openai-whisper")
        return None
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return None
```

- [ ] **Step 4: Run tests and commit**

```bash
uv run pytest tests/lib/test_transcription.py -v
git add -A
git commit -m "feat: add local audio transcription with OpenAI Whisper"
```

---

## Task 6: 面談記録 — バックエンド

**Files:**
- Create: `backend/app/schemas/meeting.py`
- Create: `backend/app/routers/meetings.py`
- Create: `backend/tests/routers/test_meetings.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create meeting schemas**

```python
# backend/app/schemas/meeting.py
from pydantic import BaseModel


class MeetingRecord(BaseModel):
    date: str | None = None
    title: str | None = None
    duration: str | None = None
    transcript: str | None = None
    note: str | None = None
    client_name: str | None = None
    file_path: str | None = None


class MeetingUploadResponse(BaseModel):
    status: str
    transcript: str | None = None
    meeting_id: str | None = None
    message: str | None = None
```

- [ ] **Step 2: Implement meetings router**

```python
# backend/app/routers/meetings.py
import os
import uuid
from datetime import datetime
from io import BytesIO
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
    """Upload audio file, transcribe, embed, and register as MeetingRecord."""
    if not is_supported_format(file.filename):
        return MeetingUploadResponse(
            status="error",
            message=f"Unsupported format: {file.filename}",
        )

    # Save file
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4().hex[:8]
    file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    content = await file.read()
    file_path.write_bytes(content)

    # Transcribe
    transcript = await transcribe_audio(str(file_path))

    # Register to Neo4j
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
    result = register_to_database(graph)

    # Embed transcript if available
    if transcript:
        embedding = await embed_text(transcript)
        if embedding:
            run_query(
                """
                MATCH (mr:MeetingRecord {filePath: $path})
                SET mr.textEmbedding = $embedding
                """,
                {"path": str(file_path), "embedding": embedding},
            )

    return MeetingUploadResponse(
        status="success",
        transcript=transcript,
        meeting_id=file_id,
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
```

- [ ] **Step 3: Register router and write test**

Add to main.py:
```python
from app.routers import meetings
app.include_router(meetings.router)
```

```python
# backend/tests/routers/test_meetings.py
def test_list_meetings(client):
    resp = client.get("/api/meetings/テスト太郎")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

- [ ] **Step 4: Add uploads/ to .gitignore**

```
uploads/
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add meeting record API with audio upload and transcription"
```

---

## Task 7: 面談記録 — フロントエンド

**Files:**
- Create: `frontend/src/app/meetings/page.tsx`
- Create: `frontend/src/components/domain/AudioUploader.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/components/domain/Sidebar.tsx`

- [ ] **Step 1: Add types and API**

Add to `types.ts`:
```typescript
export interface MeetingRecord {
  date: string | null;
  title: string | null;
  duration: string | null;
  transcript: string | null;
  note: string | null;
  client_name: string | null;
  file_path: string | null;
}
```

Add to `api.ts`:
```typescript
meetings: {
  upload: async (file: File, clientName: string, title?: string, note?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("client_name", clientName);
    if (title) formData.append("title", title);
    if (note) formData.append("note", note);
    const res = await fetch(`${API_BASE}/api/meetings/upload`, {
      method: "POST", body: formData,
    });
    if (!res.ok) throw new Error(`Upload error: ${res.status}`);
    return res.json();
  },
  list: (clientName: string) =>
    fetchApi<MeetingRecord[]>(`/api/meetings/${encodeURIComponent(clientName)}`),
},
```

- [ ] **Step 2: Create AudioUploader component**

`frontend/src/components/domain/AudioUploader.tsx`:
- ファイル選択（対応形式: mp3, wav, m4a, ogg, flac, aac, webm）
- クライアント選択ドロップダウン
- タイトル入力（任意）
- メモ入力（任意）
- アップロードボタン + 進捗表示
- 文字起こし結果の表示

- [ ] **Step 3: Create meetings page**

`frontend/src/app/meetings/page.tsx`:
- 上部: AudioUploader（新規面談記録の追加）
- 下部: クライアント選択 → 面談記録一覧（日付順）
- 各記録の文字起こしテキストを折りたたみ表示

- [ ] **Step 4: Update sidebar**

Add `/meetings` to Sidebar navigation under 「記録」 section.

- [ ] **Step 5: Build and commit**

```bash
pnpm build
git add -A
git commit -m "feat: add meeting record page with audio upload and transcription display"
```

---

## Task 8: Embedding バックフィル + ベクトルインデックス初期化

**Files:**
- Create: `backend/scripts/backfill_embeddings.py`
- Modify: `backend/app/main.py` (add vector index initialization to lifespan)

- [ ] **Step 1: Add vector index initialization to lifespan**

In `backend/app/main.py` lifespan, add after `model_manager.initialize()`:

```python
from app.lib.embedding import ensure_vector_indexes
ensure_vector_indexes()
```

- [ ] **Step 2: Create backfill script**

```python
# backend/scripts/backfill_embeddings.py
"""Backfill embeddings for existing nodes that don't have them yet."""
import asyncio
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.lib.db_operations import run_query
from app.lib.embedding import embed_text

TARGETS = [
    ("SupportLog", "embedding", "note"),
    ("NgAction", "embedding", "action"),
    ("CarePreference", "embedding", "instruction"),
]

async def backfill():
    for label, prop, text_field in TARGETS:
        records = run_query(
            f"MATCH (n:{label}) WHERE n.{prop} IS NULL AND n.{text_field} IS NOT NULL "
            f"RETURN elementId(n) AS eid, n.{text_field} AS text LIMIT 100"
        )
        print(f"{label}: {len(records)} nodes to backfill")
        for r in records:
            embedding = await embed_text(r["text"])
            if embedding:
                run_query(
                    f"MATCH (n) WHERE elementId(n) = $eid SET n.{prop} = $emb",
                    {"eid": r["eid"], "emb": embedding},
                )
        print(f"{label}: done")

if __name__ == "__main__":
    asyncio.run(backfill())
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add embedding backfill script and vector index auto-initialization"
```

---

## Task 9: E2E テスト（Playwright）

**Files:**
- Create: `frontend/e2e/dashboard.spec.ts`
- Create: `frontend/e2e/narrative.spec.ts`
- Create: `frontend/playwright.config.ts`

- [ ] **Step 1: Install Playwright**

```bash
cd ~/Dev-Work/oyagami-local/frontend
pnpm add -D @playwright/test
npx playwright install chromium
```

- [ ] **Step 2: Create playwright.config.ts**

```typescript
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: "http://localhost:3000" },
  webServer: {
    command: "pnpm dev",
    port: 3000,
    reuseExistingServer: true,
  },
});
```

- [ ] **Step 3: Write E2E tests**

```typescript
// frontend/e2e/dashboard.spec.ts
import { test, expect } from "@playwright/test";

test("dashboard loads with stats cards", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h2")).toContainText("ダッシュボード");
  await expect(page.locator("text=利用者数")).toBeVisible();
});

test("navigation works", async ({ page }) => {
  await page.goto("/");
  await page.click("text=クライアント一覧");
  await expect(page).toHaveURL("/clients");
  await expect(page.locator("h2")).toContainText("クライアント一覧");
});
```

```typescript
// frontend/e2e/narrative.spec.ts
import { test, expect } from "@playwright/test";

test("narrative page shows wizard step 1", async ({ page }) => {
  await page.goto("/narrative");
  await expect(page.locator("h2")).toContainText("ナラティブ入力");
  await expect(page.locator("textarea")).toBeVisible();
  await expect(page.locator("text=ファイルを選択")).toBeVisible();
});
```

- [ ] **Step 4: Run E2E tests**

```bash
cd ~/Dev-Work/oyagami-local/frontend
npx playwright test
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "test: add Playwright E2E tests for dashboard and narrative pages"
```

---

## Task 10: ドキュメント更新 + 最終確認

- [ ] **Step 1: Update README.md**

Add Phase 2 features to README:
- セマンティック検索（ベクトル類似度検索）
- エコマップ（React Flow で支援ネットワーク可視化）
- 面談記録（音声アップロード → Whisper 文字起こし → Neo4j 登録）
- Update API endpoint table with new endpoints
- Update 画面一覧 table with 3 new pages
- Update project structure tree

- [ ] **Step 2: Update CLAUDE.md and SETUP_GUIDE.md**

Add new features, endpoints, and dependencies (openai-whisper, ffmpeg, @xyflow/react).

- [ ] **Step 3: Run all tests**

```bash
# Backend
cd ~/Dev-Work/oyagami-local/backend && uv run pytest tests/ -v

# Frontend build
cd ~/Dev-Work/oyagami-local/frontend && pnpm build

# E2E (requires backend + frontend running)
cd ~/Dev-Work/oyagami-local/frontend && npx playwright test
```

- [ ] **Step 4: Final commit and push**

```bash
cd ~/Dev-Work/oyagami-local
git add -A
git commit -m "docs: update documentation for Phase 2 features"
git push
```
