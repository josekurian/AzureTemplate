from fastapi import APIRouter
from app.review.human_review_queue import HumanReviewQueue
from app.core.config import settings

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

# Use shared queue instance if desired; here create per-request for demo
queue = HumanReviewQueue()

@router.post("/enqueue")
async def enqueue(item: dict):
    return await queue.enqueue(item)

@router.get("/list")
async def list_queue():
    return await queue.list()
