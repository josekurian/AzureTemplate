from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title="High-End Restaurant AI - Azure")

@app.get("/health")
async def health():
    return {"status":"ok","mock_mode": settings.MOCK_MODE}

@app.get("/ready")
async def ready():
    return {"status":"ready"}
