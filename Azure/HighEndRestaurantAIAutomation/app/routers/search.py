from fastapi import APIRouter, Query, HTTPException
from app.services.cognitive_search_adapter import CognitiveSearchAdapter
from app.core.config import settings

router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("")
async def search(q: str = Query(...), top_k: int = 5):
    cs = CognitiveSearchAdapter(mock_mode=settings.MOCK_MODE)
    try:
        res = await cs.search(q, top_k=top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"query": q, "results": res}
