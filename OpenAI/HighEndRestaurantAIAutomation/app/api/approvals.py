from fastapi import APIRouter, HTTPException

from app.agent_runtime.approval_queue import approval_queue
from app.schemas import ApprovalActionRequest, ApprovalRecordResponse

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalRecordResponse])
async def list_approvals():
    return [ApprovalRecordResponse(**item) for item in approval_queue.list()]


@router.post("/{approval_id}", response_model=ApprovalRecordResponse)
async def decide_approval(approval_id: str, request: ApprovalActionRequest):
    item = approval_queue.get(approval_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    updated = approval_queue.decide(approval_id, actor=request.actor, decision=request.decision, notes=request.notes)
    return ApprovalRecordResponse(**updated)
