"""Popularity score for suggestions collected across many expansion queries.

Autocomplete returns no numbers, only an order. A phrase that surfaces for many different
prefixes, and near the top of each list, is searched more often. Score = sum of position weights
over every appearance, where position 0 weighs 1.0 and each lower slot weighs less.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field


def position_weight(position: int) -> float:
    return 1.0 / (1.0 + 0.25 * position)


def normalize(phrase: str) -> str:
    return " ".join(phrase.lower().split())


@dataclass
class ScoredPhrase:
    phrase: str
    score: float = 0.0
    occurrences: int = 0
    best_position: int = 10**6
    sources: set[str] = field(default_factory=set)


def score_suggestions(lists: Iterable[tuple[str, list[str]]]) -> list[ScoredPhrase]:
    """lists: (source, ordered suggestions) per expansion query. Returns phrases, best first."""
    acc: dict[str, ScoredPhrase] = {}
    for source, suggestions in lists:
        seen: set[str] = set()
        for pos, raw in enumerate(suggestions):
            norm = normalize(raw)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            item = acc.setdefault(norm, ScoredPhrase(phrase=norm))
            item.score += position_weight(pos)
            item.occurrences += 1
            item.best_position = min(item.best_position, pos)
            item.sources.add(source)
    return sorted(acc.values(), key=lambda p: (-p.score, p.best_position, p.phrase))
