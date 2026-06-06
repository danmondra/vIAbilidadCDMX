import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db.database import init_db
from api.routes import giros, tramites, viabilidad, webhook, zonas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ViableCDMX API",
    version="1.0.0",
    description=(
        "Backend para ViableCDMX — asesor de viabilidad y trámites para "
        "negocios en la Ciudad de México."
    ),
)

# ---------------------------------------------------------------------------
# CORS (open for demo/hackathon)
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(giros.router, prefix="/api", tags=["Giros"])
app.include_router(tramites.router, prefix="/api", tags=["Trámites"])
app.include_router(zonas.router, prefix="/api", tags=["Zonas"])
app.include_router(viabilidad.router, prefix="/api", tags=["Viabilidad"])
app.include_router(webhook.router, prefix="/api", tags=["Bot"])

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
def health():
    """Quick liveness probe."""
    return {"status": "ok", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Startup events
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    logger.info("Initialising database …")
    init_db()
    logger.info("Database ready.")


# ---------------------------------------------------------------------------
# Static files (serve index.html and assets from project root)
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent.parent  # project root

# Only mount static files if index.html exists (avoids error during tests)
if (_ROOT / "index.html").exists():
    app.mount(
        "/",
        StaticFiles(directory=str(_ROOT), html=True),
        name="static",
    )

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT", "development") == "development",
    )
