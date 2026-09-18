from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.database.database import init_db
from backend.app.api.routes import router as api_router
from backend.app.api.websocket import ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite tables
    print(f"Starting {settings.APP_NAME}...")
    await init_db()
    yield
    # Shutdown
    print(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous AI Agent backend monitoring smart home thermodynamic dynamics, tariffs, and appliances.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as necessary for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "status": "active",
        "docs_url": "/docs",
        "ws_url": "/ws/simulation"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
