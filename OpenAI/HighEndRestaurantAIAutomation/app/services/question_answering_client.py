from pathlib import Path
from uuid import uuid4

from app.core.config import settings


class QuestionAnsweringClient:
    def __init__(self) -> None:
        self._faq_source = self._load_faq_source()

    def _load_faq_source(self) -> dict[str, tuple[str, str]]:
        path = Path(__file__).resolve().parents[2] / "data" / "nlp" / "faq_source.md"
        if not path.exists():
            return {}
        lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
        faq: dict[str, tuple[str, str]] = {}
        for line in lines:
            if "|" not in line or line.startswith("#"):
                continue
            question_key, answer, source_id = [part.strip() for part in line.split("|", 2)]
            faq[question_key.lower()] = (answer, source_id)
        return faq

    async def answer_question(self, question: str, language: str = "en") -> dict:
        correlation_id = str(uuid4())
        lowered = question.lower()
        best_answer = None
        best_source = "faq:none"
        confidence = 0.35
        for key, (answer, source_id) in self._faq_source.items():
            if key in lowered or any(token in lowered for token in key.split()):
                best_answer = answer
                best_source = source_id
                confidence = 0.88
                break
        if not best_answer:
            best_answer = "I do not have an approved FAQ answer for that question. Please let me connect you with the team or use grounded retrieval."
        return {
            "answer": best_answer,
            "source_id": best_source,
            "confidence": confidence,
            "escalation_required": confidence < 0.6,
            "correlation_id": correlation_id,
        }
