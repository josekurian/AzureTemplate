from collections import defaultdict, deque
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.agent_runtime.runtime import AgentRuntime
from app.agents.sample_agent import SampleAgent
from app.core.config import settings
from app.extraction.extractor import Extractor
from app.ingestion.orchestrator import IngestionOrchestrator
from app.nlp.intent import detect_intent
from app.review.human_review_queue import HumanReviewQueue
from app.services.azure_openai_adapter import AzureOpenAIAdapter
from app.services.cognitive_search_adapter import CognitiveSearchAdapter
from app.services.document_intelligence_adapter import DocumentIntelligenceAdapter
from app.speech.synthesize import synthesize
from app.speech.transcribe import transcribe

app = FastAPI(title="High-End Restaurant AI - Azure")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

request_metrics: dict[str, dict[str, Any]] = defaultdict(
    lambda: {"count": 0, "total_ms": 0.0, "max_ms": 0.0, "last_status": None}
)
request_history: deque[dict[str, Any]] = deque(maxlen=100)
scenario_history: deque[dict[str, Any]] = deque(maxlen=100)
review_queue = HumanReviewQueue()

EPISODES = [
    {
        "id": "episode-1",
        "title": "Platform Health",
        "description": "Verify service readiness, mock mode, and baseline configuration.",
        "workflow": "health_and_readiness",
        "agent": "System Monitor",
        "sample_input": {"check": "health"},
    },
    {
        "id": "episode-2",
        "title": "Invoice Extraction",
        "description": "Run the document intelligence extractor against a sample invoice path.",
        "workflow": "document_extraction",
        "agent": "Document Extraction Agent",
        "sample_input": {"file_path": "/tmp/sample-invoice.pdf"},
    },
    {
        "id": "episode-3",
        "title": "Knowledge Ingestion",
        "description": "Embed and index sample restaurant content for retrieval testing.",
        "workflow": "knowledge_ingestion",
        "agent": "Knowledge Ingestion Agent",
        "sample_input": {
            "docs": [
                {
                    "id": "menu-1",
                    "text": "Chef tasting menu with truffle risotto and seasonal wine pairing.",
                }
            ]
        },
    },
    {
        "id": "episode-4",
        "title": "Intent Detection",
        "description": "Classify guest messages into reservation or fallback intents.",
        "workflow": "guest_intelligence",
        "agent": "Intent Classification Agent",
        "sample_input": {"text": "I need a reservation for four guests at 8 PM."},
    },
    {
        "id": "episode-5",
        "title": "Human Review Queue",
        "description": "Escalate uncertain items into a review queue for operators.",
        "workflow": "human_review",
        "agent": "Review Escalation Agent",
        "sample_input": {"item": {"source": "reservation", "confidence": 0.62}},
    },
    {
        "id": "episode-6",
        "title": "Speech and Agent Runtime",
        "description": "Exercise transcription, synthesis, and the sample agent tool invocation flow.",
        "workflow": "speech_and_agent_runtime",
        "agent": "Concierge Agent",
        "sample_input": {"audio_path": "/tmp/sample-audio.wav", "query": "Find chef specials"},
    },
]

WORKFLOWS = [
    {
        "id": "health_and_readiness",
        "name": "Health and Readiness",
        "steps": ["Health probe", "Ready probe", "Mock mode verification"],
        "modules": ["app.main"],
    },
    {
        "id": "document_extraction",
        "name": "Document Extraction",
        "steps": ["Upload path", "Document analysis", "Structured field output"],
        "modules": ["app.extraction.extractor", "app.services.document_intelligence_adapter"],
    },
    {
        "id": "knowledge_ingestion",
        "name": "Knowledge Ingestion",
        "steps": ["Text chunk collection", "Embedding", "Search indexing"],
        "modules": ["app.ingestion.orchestrator", "app.services.azure_openai_adapter", "app.services.cognitive_search_adapter"],
    },
    {
        "id": "guest_intelligence",
        "name": "Guest Intelligence",
        "steps": ["Input message", "Intent classification", "Confidence reporting"],
        "modules": ["app.nlp.intent"],
    },
    {
        "id": "human_review",
        "name": "Human Review",
        "steps": ["Create escalation item", "Queue item", "List queue status"],
        "modules": ["app.review.human_review_queue"],
    },
    {
        "id": "speech_and_agent_runtime",
        "name": "Speech and Agent Runtime",
        "steps": ["Transcription", "Text-to-speech", "Tool call through runtime"],
        "modules": ["app.speech.transcribe", "app.speech.synthesize", "app.agent_runtime.runtime", "app.agents.sample_agent"],
    },
]

AGENTS = [
    {
        "id": "system-monitor",
        "name": "System Monitor",
        "type": "Operational Agent",
        "workflows": ["health_and_readiness"],
        "capabilities": ["Health checks", "Environment visibility", "Request monitoring"],
    },
    {
        "id": "document-extraction-agent",
        "name": "Document Extraction Agent",
        "type": "Processing Agent",
        "workflows": ["document_extraction"],
        "capabilities": ["Invoice extraction", "Structured field mapping"],
    },
    {
        "id": "knowledge-ingestion-agent",
        "name": "Knowledge Ingestion Agent",
        "type": "Data Agent",
        "workflows": ["knowledge_ingestion"],
        "capabilities": ["Embeddings", "Search indexing", "Content ingestion"],
    },
    {
        "id": "intent-classification-agent",
        "name": "Intent Classification Agent",
        "type": "NLP Agent",
        "workflows": ["guest_intelligence"],
        "capabilities": ["Intent detection", "Confidence scoring"],
    },
    {
        "id": "review-escalation-agent",
        "name": "Review Escalation Agent",
        "type": "Governance Agent",
        "workflows": ["human_review"],
        "capabilities": ["Queue routing", "Escalation tracking"],
    },
    {
        "id": "concierge-agent",
        "name": "Concierge Agent",
        "type": "Runtime Agent",
        "workflows": ["speech_and_agent_runtime"],
        "capabilities": ["Speech input", "Speech output", "Tool invocation"],
    },
    {
        "id": "sample-agent",
        "name": "SampleAgent",
        "type": "Reference Agent",
        "workflows": ["speech_and_agent_runtime"],
        "capabilities": ["Search tool calls through AgentRuntime"],
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def metrics_snapshot() -> list[dict[str, Any]]:
    rows = []
    for path, data in request_metrics.items():
        avg_ms = data["total_ms"] / data["count"] if data["count"] else 0.0
        rows.append(
            {
                "path": path,
                "count": data["count"],
                "average_ms": round(avg_ms, 2),
                "max_ms": round(data["max_ms"], 2),
                "last_status": data["last_status"],
            }
        )
    return sorted(rows, key=lambda row: (-row["count"], row["path"]))


async def execute_episode(episode_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}

    if episode_id == "episode-1":
        return {
            "health": {"status": "ok", "mock_mode": settings.MOCK_MODE},
            "ready": {"status": "ready"},
        }

    if episode_id == "episode-2":
        file_path = payload.get("file_path", "/tmp/sample-invoice.pdf")
        extractor = Extractor(DocumentIntelligenceAdapter(mock_mode=settings.MOCK_MODE))
        return await extractor.extract(file_path)

    if episode_id == "episode-3":
        docs = payload.get("docs") or EPISODES[2]["sample_input"]["docs"]
        orchestrator = IngestionOrchestrator(
            embedder=AzureOpenAIAdapter(mock_mode=settings.MOCK_MODE),
            indexer=CognitiveSearchAdapter(mock_mode=settings.MOCK_MODE),
        )
        return await orchestrator.ingest(docs)

    if episode_id == "episode-4":
        text = payload.get("text", EPISODES[3]["sample_input"]["text"])
        return await detect_intent(text)

    if episode_id == "episode-5":
        item = payload.get("item", EPISODES[4]["sample_input"]["item"])
        enqueue_result = await review_queue.enqueue(item)
        queue_items = await review_queue.list()
        return {"enqueue_result": enqueue_result, "queue_items": queue_items}

    if episode_id == "episode-6":
        audio_path = payload.get("audio_path", EPISODES[5]["sample_input"]["audio_path"])
        query = payload.get("query", EPISODES[5]["sample_input"]["query"])
        runtime = AgentRuntime()

        async def fake_search(search_query: str) -> dict[str, Any]:
            return {"hits": [{"id": "special-1", "text": f"Result for {search_query}"}]}

        runtime.register_tool("search", fake_search)
        agent = SampleAgent(runtime)
        transcript = await transcribe(audio_path)
        speech = await synthesize(query)
        agent_result = await agent.do_work(query)
        return {"transcript": transcript, "speech": speech, "agent_result": agent_result}

    raise HTTPException(status_code=404, detail=f"Unknown episode '{episode_id}'")


@app.middleware("http")
async def track_requests(request, call_next):
    started_at = perf_counter()
    response = await call_next(request)
    elapsed_ms = (perf_counter() - started_at) * 1000
    path = request.url.path

    bucket = request_metrics[path]
    bucket["count"] += 1
    bucket["total_ms"] += elapsed_ms
    bucket["max_ms"] = max(bucket["max_ms"], elapsed_ms)
    bucket["last_status"] = response.status_code

    request_history.appendleft(
        {
            "timestamp": now_iso(),
            "method": request.method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": round(elapsed_ms, 2),
        }
    )
    return response


@app.get("/health")
async def health():
    return {"status": "ok", "mock_mode": settings.MOCK_MODE}


@app.get("/ready")
async def ready():
    return {"status": "ready"}


@app.get("/api/dashboard/summary")
async def dashboard_summary():
    return {
        "service": app.title,
        "mock_mode": settings.MOCK_MODE,
        "episodes": len(EPISODES),
        "agents": len(AGENTS),
        "workflows": len(WORKFLOWS),
        "recent_requests": len(request_history),
        "recent_scenarios": len(scenario_history),
    }


@app.get("/api/dashboard/catalog")
async def dashboard_catalog():
    return {"episodes": EPISODES, "agents": AGENTS, "workflows": WORKFLOWS}


@app.get("/api/dashboard/episodes")
async def list_episodes():
    return EPISODES


@app.post("/api/dashboard/run/{episode_id}")
async def run_episode(episode_id: str, payload: dict[str, Any] | None = None):
    started_at = perf_counter()
    response = await execute_episode(episode_id, payload)
    elapsed_ms = (perf_counter() - started_at) * 1000
    event = {
        "timestamp": now_iso(),
        "episode_id": episode_id,
        "request": payload or {},
        "response": response,
        "duration_ms": round(elapsed_ms, 2),
    }
    scenario_history.appendleft(event)
    return event


@app.get("/api/dashboard/agents")
async def list_agents():
    return AGENTS


@app.get("/api/dashboard/workflows")
async def list_workflows():
    return WORKFLOWS


@app.get("/api/dashboard/metrics")
async def list_metrics():
    return {
        "generated_at": now_iso(),
        "http_metrics": metrics_snapshot(),
        "scenario_runs": list(scenario_history)[:20],
    }


@app.get("/api/dashboard/requests")
async def list_requests(limit: int = Query(default=25, ge=1, le=100)):
    return {
        "http_requests": list(request_history)[:limit],
        "scenario_requests": list(scenario_history)[:limit],
    }
