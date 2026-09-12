from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1.api import api_router


from app.services.vision.manager import stream_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Create all database tables registered on Base metadata
    Base.metadata.create_all(bind=engine)
    print(f"[*] {settings.PROJECT_NAME} initialized in [{settings.NODE_TYPE}] mode.")
    yield
    # Gracefully release any active video streams on shutdown
    stream_manager.stop_all()
    print(f"[*] {settings.PROJECT_NAME} shutting down.")


# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Set up CORS middleware for dashboard frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve local media snapshots and clips securely
app.mount("/storage", StaticFiles(directory=settings.STORAGE_DIR), name="storage")

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", summary="Root Status")
def root():
    """Root endpoint providing quick navigation links."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "node_type": settings.NODE_TYPE,
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
    }
