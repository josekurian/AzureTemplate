"""
telemetry.py — Phase 9: Monitoring and Observability
=====================================================
AI-102 Skills:
  - Application Insights: SDK telemetry for end-to-end latency tracking
  - Custom events and metrics: token usage, safety decisions, search quality
  - OpenTelemetry tracing: spans for each pipeline stage
  - KQL query examples for Log Analytics dashboards

Restaurant Monitoring Use Cases:
  - Track average response latency per query type (voice vs text)
  - Alert when token spend exceeds daily budget threshold
  - Monitor content safety block rate (spike = potential attack)
  - Track search recall quality (no results returned = index issue)
"""

import logging
import os
from typing import Optional
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

try:
    from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
    from applicationinsights import TelemetryClient
    _appinsights_available = True
except ImportError:
    _appinsights_available = False

logger = logging.getLogger(__name__)

# ── Global telemetry setup ────────────────────────────────────────────────────
_tracer_provider: Optional[TracerProvider] = None
_telemetry_client: Optional[object] = None  # TelemetryClient


def setup_telemetry(connection_string: str) -> None:
    """
    Initialise Application Insights telemetry.
    Call once at application startup.

    AI-102: connectionString is preferred over instrumentationKey (deprecated).
    """
    global _tracer_provider, _telemetry_client

    if not connection_string or not _appinsights_available:
        logger.warning("Application Insights not configured — telemetry disabled.")
        return

    # OpenTelemetry trace exporter to Azure Monitor
    exporter = AzureMonitorTraceExporter(connection_string=connection_string)
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracer_provider = provider

    # Classic Application Insights client for custom events/metrics
    _telemetry_client = TelemetryClient()
    _telemetry_client.context.instrumentation_key = _extract_ikey(connection_string)

    logger.info("Application Insights telemetry initialised.")


def get_tracer(name: str) -> trace.Tracer:
    """Return a tracer for the given module name."""
    return trace.get_tracer(name)


def record_token_usage(
    prompt_tokens: int,
    completion_tokens: int,
    deployment: str,
    session_id: str = "",
) -> None:
    """
    Track token usage as a custom metric in Application Insights.

    AI-102: Token cost = primary cost driver for Azure OpenAI.
    Monitoring this enables budget alerts before the bill arrives.

    KQL to query token usage:
      customMetrics
      | where name == "openai_total_tokens"
      | summarize sum(value) by bin(timestamp, 1h), tostring(customDimensions.deployment)
      | render timechart
    """
    if _telemetry_client:
        _telemetry_client.track_metric(
            "openai_prompt_tokens",
            prompt_tokens,
            properties={"deployment": deployment, "session_id": session_id},
        )
        _telemetry_client.track_metric(
            "openai_completion_tokens",
            completion_tokens,
            properties={"deployment": deployment, "session_id": session_id},
        )
        _telemetry_client.track_metric(
            "openai_total_tokens",
            prompt_tokens + completion_tokens,
            properties={"deployment": deployment, "session_id": session_id},
        )
        _telemetry_client.flush()


def record_safety_decision(
    is_safe: bool,
    blocked_categories: list[str],
    context: str,
    jailbreak: bool = False,
    document_attack: bool = False,
) -> None:
    """
    Track content safety decisions as custom events.

    AI-102: Monitoring the block rate per category is part of Responsible AI governance.
    A sudden spike in HATE or JAILBREAK events indicates an active attack.

    KQL dashboard query:
      customEvents
      | where name == "content_safety_decision"
      | where tobool(customDimensions.jailbreak_detected) == true
      | summarize count() by bin(timestamp, 15m)
      | render timechart
    """
    if _telemetry_client:
        _telemetry_client.track_event(
            "content_safety_decision",
            properties={
                "is_safe": str(is_safe),
                "blocked_categories": ",".join(blocked_categories),
                "context": context,
                "jailbreak_detected": str(jailbreak),
                "document_attack_detected": str(document_attack),
            },
            measurements={"block_count": 0 if is_safe else 1},
        )
        _telemetry_client.flush()


def record_search_metrics(
    query: str,
    results_count: int,
    used_semantic_ranker: bool,
    latency_ms: float,
) -> None:
    """
    Track search quality and cost indicators.

    AI-102: results_count == 0 indicates an index gap (content not ingested).
    use_semantic_ranker == True adds per-query cost — track usage rate.
    """
    if _telemetry_client:
        _telemetry_client.track_metric(
            "search_results_count",
            results_count,
            properties={
                "used_semantic_ranker": str(used_semantic_ranker),
                "query_length": str(len(query)),
            },
        )
        _telemetry_client.track_metric(
            "search_latency_ms",
            latency_ms,
            properties={"used_semantic_ranker": str(used_semantic_ranker)},
        )
        if results_count == 0:
            _telemetry_client.track_event(
                "search_zero_results",
                properties={"query_preview": query[:100]},
            )
        _telemetry_client.flush()


# ── KQL Reference Queries (for Log Analytics dashboards) ──────────────────────
KQL_QUERIES = {
    "token_spend_hourly": """
        // Total token spend per hour by deployment
        customMetrics
        | where name == "openai_total_tokens"
        | summarize TotalTokens=sum(value) by bin(timestamp, 1h), Deployment=tostring(customDimensions.deployment)
        | render timechart
    """,
    "safety_block_rate": """
        // Content safety block rate over time
        customEvents
        | where name == "content_safety_decision"
        | summarize
            Total=count(),
            Blocked=countif(tobool(customDimensions.is_safe) == false)
            by bin(timestamp, 15m)
        | extend BlockRate = round(todouble(Blocked) / Total * 100, 1)
        | render timechart
    """,
    "jailbreak_attempts": """
        // Jailbreak attempts — security alert
        customEvents
        | where name == "content_safety_decision"
        | where tobool(customDimensions.jailbreak_detected) == true
        | summarize count() by bin(timestamp, 5m)
        | render timechart
    """,
    "openai_throttle_alerts": """
        // Azure OpenAI 429 throttle events
        AzureDiagnostics
        | where ResourceType == "OPENAI"
        | where statusCode_d == 429
        | summarize ThrottledRequests=count() by bin(TimeGenerated, 5m)
        | where ThrottledRequests > 5
    """,
    "e2e_latency": """
        // End-to-end chat response latency (P95)
        dependencies
        | where name == "restaurant_chat"
        | summarize
            P50=percentile(duration, 50),
            P95=percentile(duration, 95),
            P99=percentile(duration, 99)
            by bin(timestamp, 1h)
        | render timechart
    """,
}


def _extract_ikey(connection_string: str) -> str:
    """Extract InstrumentationKey from a connection string."""
    for part in connection_string.split(";"):
        if part.startswith("InstrumentationKey="):
            return part.split("=", 1)[1]
    return ""
