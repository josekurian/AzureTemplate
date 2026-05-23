from fastapi import APIRouter

from app.agent_runtime.runtime import agent_runtime
from app.agent_runtime.workflow_engine import WorkflowEngine
from app.schemas import WorkflowRequest, WorkflowResponse

router = APIRouter(prefix="/workflows", tags=["workflows"])
workflow_engine = WorkflowEngine(agent_runtime)


@router.post("/private-dining", response_model=WorkflowResponse)
async def private_dining_workflow(request: WorkflowRequest):
    result = await workflow_engine.run_private_dining(request.model_dump())
    return WorkflowResponse(**result)
