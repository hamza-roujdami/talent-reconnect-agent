"""FastAPI server for Talent Reconnect Agent.

Usage:
    python main.py
    
    # Or with uvicorn directly:
    uvicorn main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import router, get_factory
from config import config
from observability import setup_telemetry, enable_foundry_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Validate config
    missing = config.validate()
    if missing:
        print("⚠️  Missing environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nSome features may not work. Copy .env.example to .env and configure.")
    
    # Setup observability (App Insights + OpenTelemetry)
    if setup_telemetry():
        print("✓ Telemetry enabled (Azure Monitor)")
        enable_foundry_tracing()
    
    # Initialize factory on startup
    print("🚀 Starting Talent Reconnect Agent...")
    try:
        await get_factory()
        print("✓ Agents initialized")
    except Exception as e:
        print(f"⚠️  Agent initialization failed: {e}")
        print("   API will start but chat may not work.")
    
    yield
    
    # Cleanup on shutdown
    print("Shutting down...")


app = FastAPI(
    title="Talent Reconnect Agent",
    description="AI-powered recruiting assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# Include API routes
app.include_router(router)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Serve the main UI."""
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    print(f"\n🎯 Talent Reconnect Agent")
    print(f"   http://{config.host}:{config.port}\n")
    
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=True,
    )
