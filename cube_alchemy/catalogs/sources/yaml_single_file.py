from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple
import yaml
from ..abc import Source, Spec, Key


class YAMLSource(Source):
    """Generic single-file YAML source.

    Expects a top-level mapping of kind -> { name -> spec }.
    No domain-specific behavior is applied. Subclasses may override the
    protected hooks to customize load/save transformations.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"YAML file not found: {self.path}")
        self._cache: Optional[Dict[str, Dict[str, Any]]] = None

    # ----- protected extension hooks -----
    def _postprocess_loaded(self, normalized: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Customize data right after normalization. Default: identity."""
        return normalized

    def _preprocess_to_save(self, data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Customize data just before saving. Default: drop meta keys and pass through."""
        clean: Dict[str, Dict[str, Any]] = {}
        for kind, items in (data or {}).items():
            section: Dict[str, Any] = {}
            for name, spec in (items or {}).items():
                if spec is None:
                    section[name] = {}
                    continue
                section[name] = {k: v for k, v in spec.items() if k not in ("kind", "name") and v is not None}
            clean[kind] = section
        return clean

    # ----- core implementation -----
    def _load(self) -> Dict[str, Dict[str, Any]]:
        if self._cache is None:
            with self.path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            if not isinstance(raw, dict):
                raise ValueError("Root of YAML must be a mapping of kind -> {name -> spec}")
            normalized: Dict[str, Dict[str, Any]] = {}
            for kind, items in raw.items():
                if items is None:
                    normalized[str(kind)] = {}
                    continue
                if not isinstance(items, dict):
                    raise ValueError(f"Section '{kind}' must be a mapping of name -> spec")
                bucket: Dict[str, Any] = {}
                for name, spec in items.items():
                    if not isinstance(spec, dict):
                        raise ValueError(f"Spec for {kind}.{name} must be a mapping")
                    spec_copy = dict(spec)
                    spec_copy.setdefault("kind", str(kind))
                    spec_copy.setdefault("name", str(name))
                    bucket[str(name)] = spec_copy
                normalized[str(kind)] = bucket
            normalized = self._postprocess_loaded(normalized)
            self._cache = normalized
        return self._cache

    def kinds(self) -> Iterable[str]:
        return sorted(self._load().keys())

    def iter_definitions(self, kind: Optional[str] = None) -> Iterator[Tuple[Key, Spec]]:
        data = self._load()
        if kind:
            for name, spec in data.get(kind, {}).items():
                yield ((kind, name), spec)
            return
        for k, items in data.items():
            for name, spec in items.items():
                yield ((k, name), spec)

    def get(self, kind: str, name: str) -> Optional[Spec]:
        return self._load().get(kind, {}).get(name)

    def save(self, data: Dict[str, Dict[str, Spec]], filepath: Optional[os.PathLike[str] | str] = None) -> None:
        target_path = Path(filepath) if filepath else self.path
        out = self._preprocess_to_save(data)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open('w', encoding='utf-8') as f:
            yaml.dump(out, f, default_flow_style=False, sort_keys=False, indent=2)
        self._cache = None  # Force reload on next access

    def reload(self) -> None:
        """Invalidate cache so next access re-reads from disk."""
        self._cache = None

