from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Any
from .abc import Source, Repository, Spec, Key
import warnings

class Catalog:
    """Facade to load and query model definitions from one or more sources."""

    def __init__(self, sources: Iterable[Source], repository: Repository) -> None:
        self.sources = list(sources)
        self.repo = repository
        if len(sources) > 1:
            warnings.warn("Catalog: Multiple sources attached; reads will merge and saves will broadcast repo to all sources.")

    def refresh(self, kinds: Optional[Iterable[str]] = None, clear_repo: bool = False, reload_sources: bool = False) -> None:
        target_kinds = set(kinds) if kinds else None

        # Optionally reload sources (if they implement .reload())
        if reload_sources:
            for source in self.sources:
                reload_fn = getattr(source, "reload", None)
                if callable(reload_fn):
                    reload_fn()

        # Optionally clear repo so YAML fully replaces previous state
        if clear_repo:
            for k, n in list(self.repo.list()):
                if (target_kinds is None) or (k in target_kinds):
                    self.repo.delete(k, n)

        # Load from sources
        for source in self.sources:
            for (kind, name), spec in source.iter_definitions():
                if target_kinds and kind not in target_kinds:
                    continue
                self.repo.put(kind, name, spec)

    def get(self, kind: str, name: str) -> Optional[Spec]:
        return self.repo.get(kind, name)

    def list_kinds(self) -> List[str]:
        return sorted({k for k, _ in self.repo.list()})

    def list(self, kind: Optional[str] = None) -> List[str]:
        return sorted({name for k, name in self.repo.list(kind=kind)})
    
    def add(self, kind: str, name: str, spec: Spec) -> None:
        """Add a new definition."""
        spec = dict(spec)  # Make a copy to avoid modifying the original
        spec.setdefault("kind", kind)
        spec.setdefault("name", name)
        self.repo.put(kind, name, spec)

    def update(self, kind: str, name: str, spec: Spec) -> None:
        """Update an existing definition."""
        spec = dict(spec)  # Make a copy to avoid modifying the original
        spec.setdefault("kind", kind)
        spec.setdefault("name", name)
        self.repo.update(kind, name, spec)

    def delete(self, kind: str, name: str) -> bool:
        """Delete a definition."""
        return self.repo.delete(kind, name)

    def add_kind(self, kind: str) -> None:
        """Add a new kind (section)."""
        self.repo.add_kind(kind)
