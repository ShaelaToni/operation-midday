"""The SourceAdapter interface and the source registry (the one import door)."""
from __future__ import annotations

import abc

# Canonical source identifiers (match IngestRun.source / SpendRow.source values).
SPEND_SOURCES = ("google", "meta", "taboola", "tiktok")
REVENUE_SOURCES = ("affiliate",)
ALL_SOURCES = SPEND_SOURCES + REVENUE_SOURCES


class SourceAdapter(abc.ABC):
    """Parse one source's raw rows into normalized ORM-row kwargs.

    Implementations handle that source's real-shape quirks (Google micros,
    Meta nested actions/action_values, Taboola 'spent' + timezone, TikTok
    dimensions/metrics split read by NAME, affiliate sub_id + status).
    Adapters do NO database I/O - they return plain dicts; the caller persists.
    """

    source: str  # one of ALL_SOURCES; set by each subclass

    @abc.abstractmethod
    def parse_row(self, raw: dict) -> dict:
        """Map ONE raw source row (as the platform returns/exports it) to a dict of
        kwargs for the target ORM model (SpendRow for spend sources, ConversionRow
        for revenue sources). The raw dict is preserved by the caller into the row's
        'raw' JSON field for lineage."""
        raise NotImplementedError

    def parse_rows(self, raw_rows: list[dict]) -> list[dict]:
        """Parse a batch. Default maps parse_row over the list; override if a source
        needs batch context (e.g. TikTok's dimensions/metrics split)."""
        return [self.parse_row(r) for r in raw_rows]


# Registry: source name -> adapter instance. Populated in 2B as each adapter lands.
# The one import door: callers look up by source string, never import a concrete adapter.
_REGISTRY: dict[str, SourceAdapter] = {}


def register(adapter: SourceAdapter) -> None:
    _REGISTRY[adapter.source] = adapter


def get_adapter(source: str) -> SourceAdapter:
    if source not in _REGISTRY:
        raise KeyError(f"No adapter registered for source '{source}'. Known: {sorted(_REGISTRY)}")
    return _REGISTRY[source]


def registered_sources() -> list[str]:
    return sorted(_REGISTRY)
