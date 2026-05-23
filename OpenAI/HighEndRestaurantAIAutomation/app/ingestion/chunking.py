import hashlib
import re
from typing import Any


def approximate_token_count(text: str) -> int:
    return max(1, len(text.split()))


def _split_sections(markdown: str) -> list[tuple[str | None, str]]:
    sections: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    for line in markdown.splitlines():
        if line.strip().startswith("#"):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
                current_lines = []
            current_heading = re.sub(r"^#+\s*", "", line).strip() or None
            continue
        current_lines.append(line)
    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))
    return [section for section in sections if section[1]]


def chunk_markdown(
    markdown: str,
    *,
    source_id: str,
    metadata: dict[str, Any],
    max_tokens: int = 180,
    overlap_tokens: int = 30,
) -> list[dict[str, Any]]:
    sections = _split_sections(markdown) or [(metadata.get("title"), markdown.strip())]
    chunks: list[dict[str, Any]] = []
    for section_index, (heading, content) in enumerate(sections, start=1):
        words = content.split()
        start = 0
        while start < len(words):
            end = min(len(words), start + max_tokens)
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words).strip()
            if not chunk_text:
                break
            digest = hashlib.sha1(f"{source_id}:{section_index}:{start}:{chunk_text}".encode("utf-8")).hexdigest()[:12]
            chunk_id = f"{source_id}-s{section_index}-t{start}-{digest}"
            chunks.append(
                {
                    "id": chunk_id,
                    "chunk_id": chunk_id,
                    "section": heading or metadata.get("section"),
                    "page": metadata.get("page"),
                    "content": chunk_text,
                    "token_count": approximate_token_count(chunk_text),
                    "metadata": dict(metadata),
                }
            )
            if end >= len(words):
                break
            start = max(0, end - overlap_tokens)
    return chunks
