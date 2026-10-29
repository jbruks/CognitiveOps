"""Small attributed passage retriever for MF-DoD.

Caller supplies extracted passages; this module does not claim to have parsed
PDFs or verified their pagination. Source text is untrusted reference content.
"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DoctrinePassage:
    source: str
    text: str
    locator: str | None = None
    verified: bool = False

    def __post_init__(self):
        if not self.source.strip() or not self.text.strip():
            raise ValueError("Source and text must be non-empty")


@dataclass(frozen=True)
class DoctrineHit:
    passage: DoctrinePassage
    score: int


class DoctrineService:
    def __init__(self, passages=()):
        self.passages = tuple(passages)
        if any(not isinstance(p, DoctrinePassage) for p in self.passages):
            raise TypeError("Passages must be DoctrinePassage instances")

    @staticmethod
    def _terms(text):
        return set(re.findall(r"[a-zA-ZÀ-ÿ0-9]{3,}", text.casefold()))

    def retrieve(self, question, limit=3):
        if not isinstance(question, str) or not question.strip():
            raise ValueError("A nonempty doctrine question is required")
        if limit < 1:
            raise ValueError("limit must be positive")
        terms = self._terms(question)
        hits = [
            DoctrineHit(p, len(terms & self._terms(p.text)))
            for p in self.passages
        ]
        return sorted((h for h in hits if h.score > 0),
                      key=lambda h: (-h.score, h.passage.source,
                                     h.passage.locator or ""))[:limit]

    @staticmethod
    def provenance(hit):
        p = hit.passage
        return {"source": p.source, "locator": p.locator,
                "locator_verified": p.verified, "excerpt": p.text,
                "overlap_score": hit.score}
