from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, narratives, quicklog, search, dashboard, clients, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.lib.db_operations import is_db_available
    from app.lib.model_manager import model_manager
    if is_db_available():
        print(f"Neo4j connected: {settings.neo4j_uri}")
    else:
        print(f"WARNING: Neo4j not available at {settings.neo4j_uri}")
    await model_manager.initialize()
    yield
    from app.lib.db_operations import close_driver
    close_driver()


app = FastAPI(
    title="oyagami-local",
    description="親亡き後支援データベース（ローカルLLM版）",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{settings.frontend_port}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(narratives.router)
app.include_router(quicklog.router)
app.include_router(chat.router)
app.include_router(search.router)
app.include_router(dashboard.router)
app.include_router(clients.router)
app.include_router(system.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
