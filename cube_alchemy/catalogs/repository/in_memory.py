from __future__ import annotations
from typing import Dict, Iterable, Optional, List
from ..abc import Repository, Spec, Key


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Spec]] = {}

    def put(self, kind: str, name: str, spec: Spec) -> None:
        self._data.setdefault(kind, {})[name] = spec

    def get(self, kind: str, name: str) -> Optional[Spec]:
        return self._data.get(kind, {}).get(name)

    def list(self, kind: Optional[str] = None) -> Iterable[Key]:
        if kind:
            for name in self._data.get(kind, {}):
                yield (kind, name)
            return
        for k, items in self._data.items():
            for n in items:
                yield (k, n)
    
    def delete(self, kind: str, name: str) -> bool:
        """Delete a definition by kind and name."""
        if kind not in self._data or name not in self._data[kind]:
            return False
        del self._data[kind][name]
        # Remove empty kind dictionaries
        if not self._data[kind]:
            del self._data[kind]
        return True
    
    def update(self, kind: str, name: str, spec: Spec) -> None:
        """Update an existing definition."""
        self.put(kind, name, spec)
    
    def add_kind(self, kind: str) -> None:
        """Add a new kind (section) if it doesn't exist."""
        if kind not in self._data:
            self._data[kind] = {}
    
    def get_all(self) -> Dict[str, Dict[str, Spec]]:
        """Get the entire data structure."""
        return self._data
