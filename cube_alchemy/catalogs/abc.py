from __future__ import annotations
from abc import ABC, abstractmethod
import os
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple

Spec = Dict[str, Any]
Key = Tuple[str, str]  # (kind, name)


class Source(ABC):
    """Read-only provider of model definition specs from any backend (yaml, db, web, etc)."""

    @abstractmethod
    def kinds(self) -> Iterable[str]:
        """Return the kinds of objects available (e.g., metrics, queries, plots)."""
        raise NotImplementedError

    @abstractmethod
    def iter_definitions(self, kind: Optional[str] = None) -> Iterator[Tuple[Key, Spec]]:
        """Yield ((kind, name), spec) items."""
        raise NotImplementedError

    @abstractmethod
    def get(self, kind: str, name: str) -> Optional[Spec]:
        """Return the spec for (kind, name) if present."""
        raise NotImplementedError
    
    @abstractmethod
    def save(self, data: Dict[str, Dict[str, Spec]], filepath: Optional[os.PathLike[str] | str] = None) -> None:
        """Persist the provided definitions to this source.

        Implementations may use an internal default location when filepath is None.
        """
        raise NotImplementedError

class Repository(ABC):
    """Mutable storage for normalized specs."""

    @abstractmethod
    def put(self, kind: str, name: str, spec: Spec) -> None:
        """Store a definition by kind and name."""
        raise NotImplementedError

    @abstractmethod
    def get(self, kind: str, name: str) -> Optional[Spec]:
        """Get a definition by kind and name."""
        raise NotImplementedError

    @abstractmethod
    def list(self, kind: Optional[str] = None) -> Iterable[Key]:
        """List keys (kind, name) for definitions, optionally filtered by kind."""
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, kind: str, name: str) -> bool:
        """Delete a definition by kind and name."""
        raise NotImplementedError

    @abstractmethod
    def update(self, kind: str, name: str, spec: Spec) -> None:
        """Update an existing definition."""
        raise NotImplementedError
    
    @abstractmethod
    def add_kind(self, kind: str) -> None:
        """Add a new kind (section) if it doesn't exist."""
        raise NotImplementedError
    
    @abstractmethod
    def get_all(self) -> Dict[str, Dict[str, Spec]]:
        """Get the entire data structure."""
        raise NotImplementedError
