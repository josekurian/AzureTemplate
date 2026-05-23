from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="Guest or staff message")
    guest_id: Optional[str] = None
    language: str = "en"
    channel: str = "web"
    response_language: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    safety_decision: str = "allow"
    detected_intent: Optional[str] = None
    sentiment: Optional[str] = None
    translated_from: Optional[str] = None
    translated_to: Optional[str] = None
    key_phrases: List[str] = Field(default_factory=list)


class ReservationRequest(BaseModel):
    guest_name: str
    date: str
    time: str
    party_size: int
    dietary_notes: Optional[str] = None
    occasion: Optional[str] = None
    language: str = "en"


class ReservationResponse(BaseModel):
    status: str
    guest_name: str
    requested_time: str
    party_size: int
    human_review_required: bool
    notes: str


class TranslationRequest(BaseModel):
    text: str
    to_language: str = "en"


class TextToSpeechRequest(BaseModel):
    text: str
    voice: str = "en-US-JennyNeural"


class TextToSpeechResponse(BaseModel):
    audio_base64: str
    format: str = "wav"
    voice: str


class BotHandoffRequest(BaseModel):
    conversation_id: str
    guest_name: Optional[str] = None
    issue_summary: str
    priority: str = "normal"


class FeatureStatus(BaseModel):
    available: bool
    mode: str
    notes: str


class DetailedHealthResponse(BaseModel):
    status: str
    mock_mode: bool
    features: dict[str, FeatureStatus]


class AgentChatRequest(ChatRequest):
    session_id: Optional[str] = None
    actor_role: Literal["guest", "staff", "manager"] = "guest"


class AgentStepResponse(BaseModel):
    agent: str
    action: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class ToolInvocationResponse(BaseModel):
    tool_name: str
    status: str
    actor_role: str
    result: dict[str, Any] = Field(default_factory=dict)


class AgentChatResponse(BaseModel):
    trace_id: str
    selected_agent: str
    answer: str
    safety_decision: str
    tool_calls: List[ToolInvocationResponse] = Field(default_factory=list)
    steps: List[AgentStepResponse] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    approvals_requested: List[str] = Field(default_factory=list)
    memory_snapshot: dict[str, Any] = Field(default_factory=dict)


class TraceResponse(BaseModel):
    trace_id: str
    events: List[dict[str, Any]] = Field(default_factory=list)


class ApprovalRecordResponse(BaseModel):
    approval_id: str
    workflow_type: str
    status: str
    required_role: str
    created_by: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalActionRequest(BaseModel):
    actor: str
    decision: Literal["approved", "rejected"]
    notes: Optional[str] = None


class WorkflowRequest(BaseModel):
    session_id: Optional[str] = None
    guest_name: str
    message: str
    language: str = "en"
    guest_id: Optional[str] = None


class WorkflowResponse(BaseModel):
    workflow_type: str
    trace_id: str
    status: str
    selected_agents: List[str] = Field(default_factory=list)
    approvals_requested: List[str] = Field(default_factory=list)
    final_answer: str
    summary: dict[str, Any] = Field(default_factory=dict)


class EvaluationSummaryResponse(BaseModel):
    scenario_count: int
    pass_count: int
    fail_count: int
    pass_rate: float
    tool_calls: int
    blocked_count: int
    results: List[dict[str, Any]] = Field(default_factory=list)
