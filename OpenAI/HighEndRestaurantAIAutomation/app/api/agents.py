from fastapi import APIRouter

from app.agent_runtime.runtime import agent_runtime
from app.agent_runtime.trace_context import get_trace
from app.schemas import AgentChatRequest, AgentChatResponse, TraceResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest):
    return await agent_runtime.run_agent_chat(request.model_dump())


@router.get("/trace/{trace_id}", response_model=TraceResponse)
async def agent_trace(trace_id: str):
    return TraceResponse(trace_id=trace_id, events=get_trace(trace_id))
