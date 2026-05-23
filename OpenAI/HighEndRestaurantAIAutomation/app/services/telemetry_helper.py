from uuid import uuid4


def safe_telemetry(
    *,
    feature: str,
    detected_language: str | None = None,
    target_language: str | None = None,
    confidence: float | None = None,
    redaction_count: int = 0,
    fallback_reason: str | None = None,
    audio_duration_ms: int | None = None,
) -> dict:
    return {
        "feature": feature,
        "correlation_id": str(uuid4()),
        "latency_ms": 0,
        "detected_language": detected_language,
        "target_language": target_language,
        "confidence": confidence,
        "redaction_count": redaction_count,
        "fallback_reason": fallback_reason,
        "audio_duration_ms": audio_duration_ms,
    }
