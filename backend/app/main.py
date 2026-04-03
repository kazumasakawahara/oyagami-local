from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, narratives, quicklog, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


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


@app.get("/api/health")
async def health():
    return {"status": "ok"}
