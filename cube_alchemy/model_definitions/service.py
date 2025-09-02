from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Any
from .abc import DefinitionSource, DefinitionRepository, Spec, Key


class Catalog:
    """Facade to load and query model definitions from one or more sources."""

    def __init__(self, sources: Iterable[DefinitionSource], repository: DefinitionRepository) -> None:
        self.sources = list(sources)
        self.repo = repository

    def refresh(self, kinds: Optional[Iterable[str]] = None) -> None:
        target_kinds = set(kinds) if kinds else None
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

    # Convenience helpers (extend as needed)
    def get_metric(self, name: str) -> Optional[Spec]:
        return self.get("metrics", name)

    def list_metrics(self) -> List[str]:
        return self.list("metrics")
    
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
    
    def save(self, filepath: Optional[os.PathLike[str] | str] = None) -> None:
        """
        Save the current state of the repository back to a YAML file.
        
        Args:
            filepath: Optional custom filepath. If not provided, it will use 
                    the filepath from the first YAMLDefinitionSource in sources.
        """
        from .sources.yaml_single_file import YAMLDefinitionSource
        
        # Find the first YAML source to use its save_to_file method
        yaml_source = None
        for source in self.sources:
            if isinstance(source, YAMLDefinitionSource):
                yaml_source = source
                break
        
        if not yaml_source:
            raise ValueError("No YAMLDefinitionSource found in sources")
        
        # Convert repository contents to the expected data structure
        data: Dict[str, Dict[str, Spec]] = {}
        
        # Get all kinds and items from the repository
        for kind, name in self.repo.list():
            if kind not in data:
                data[kind] = {}
            
            spec = self.get(kind, name)
            if spec:
                data[kind][name] = spec
        
        # Save using the YAML source
        yaml_source.save_to_file(data, filepath)
