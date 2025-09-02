from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple
import yaml
from ..abc import DefinitionSource, Spec, Key


class YAMLDefinitionSource(DefinitionSource):
    """
    Loads definitions from a single YAML file with top-level sections per kind:

    model.yaml structure example:

    metrics:
      sales:
        expr: sum(revenue)
        ...
    computed_metrics:
      gm_pct:
        expr: gm / sales
    queries:
      daily_sales:
        dimensions: [date]
        metrics: [sales]
    plots:
      sales_by_day:
        query: daily_sales
        type: line
    
    Each section is a mapping of name -> spec.
    """

    def __init__(self, path: str | Path, prefer_nested_plots: bool = True) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"YAML model file not found: {self.path}")
        self._cache: Optional[Dict[str, Dict[str, Any]]] = None
        # When saving, prefer to nest plots inside their queries (queries.<q>.plots)
        self.prefer_nested_plots = prefer_nested_plots

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if self._cache is None:
            with self.path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise ValueError("Root of YAML must be a mapping of kind -> definitions")
            # Normalize: ensure kinds map to dicts of name->spec
            normalized: Dict[str, Dict[str, Any]] = {}
            for kind, items in data.items():
                if items is None:
                    normalized[kind] = {}
                    continue
                if not isinstance(items, dict):
                    raise ValueError(f"Section '{kind}' must be a mapping of name -> spec")
                normalized[kind] = {}
                for name, spec in items.items():
                    if not isinstance(spec, dict):
                        raise ValueError(f"Spec for {kind}.{name} must be a mapping")
                    spec_copy = dict(spec)  # shallow copy
                    spec_copy.setdefault("kind", kind)
                    spec_copy.setdefault("name", str(name))
                    normalized[kind][str(name)] = spec_copy

            # Special handling: plots nested under queries -> lift into top-level 'plots'
            if "queries" in normalized:
                plots_bucket: Dict[str, Any] = dict(normalized.get("plots", {}))
                for qname, qspec in list(normalized["queries"].items()):
                    q_plots = qspec.pop("plots", None)
                    if isinstance(q_plots, dict):
                        for pname, pspec in q_plots.items():
                            if not isinstance(pspec, dict):
                                raise ValueError(f"Plot spec for queries.{qname}.plots.{pname} must be a mapping")
                            out = dict(pspec)
                            out.setdefault("kind", "plots")
                            out.setdefault("name", str(pname))
                            out.setdefault("query", qname)
                            plots_bucket[str(pname)] = out
                if plots_bucket:
                    normalized["plots"] = plots_bucket
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
        
    def save_to_file(self, data: Dict[str, Dict[str, Spec]], filepath: Optional[os.PathLike[str] | str] = None) -> None:
        """
        Save the current data structure back to the YAML file.
        
        Args:
            data: The data structure to save
            filepath: Optional custom filepath, defaults to the source's filepath
        """
        target_path = Path(filepath) if filepath else self.path
        
        # Prepare the data structure for saving
        # We need to clean internal attributes like 'kind' and 'name' that were added during normalization
        clean_data: Dict[str, Dict[str, Any]] = {}

        # Start by copying clean sections for everything except plots
        for kind, items in (data or {}).items():
            if kind == "plots":
                continue
            clean_section: Dict[str, Any] = {}
            for name, spec in (items or {}).items():
                if spec is None:
                    clean_section[name] = {}
                    continue
                clean_spec = {k: v for k, v in spec.items() if k not in ("kind", "name") and v is not None}
                clean_section[name] = clean_spec
            clean_data[kind] = clean_section

        # Handle plots: either nest under queries or keep top-level
        remaining_top_level_plots: Dict[str, Any] = {}
        plots = (data or {}).get("plots", {}) or {}
        if self.prefer_nested_plots and "queries" in clean_data:
            # Ensure 'plots' per-query bucket
            for pname, pspec in plots.items():
                if not isinstance(pspec, dict):
                    continue
                qname = pspec.get("query")
                if not qname or qname not in clean_data["queries"]:
                    # Unknown query; keep at top level
                    remaining_top_level_plots[pname] = {k: v for k, v in pspec.items() if k not in ("kind", "name")}
                    continue
                q_section = clean_data["queries"].setdefault(qname, {})
                q_plots = q_section.setdefault("plots", {})
                q_plots[pname] = {k: v for k, v in pspec.items() if k not in ("kind", "name", "query")}
        else:
            for pname, pspec in plots.items():
                remaining_top_level_plots[pname] = {k: v for k, v in pspec.items() if k not in ("kind", "name")}

        if remaining_top_level_plots:
            clean_data["plots"] = remaining_top_level_plots
        
        # Create parent directories if they don't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to the file with proper YAML formatting
        with open(target_path, 'w', encoding='utf-8') as f:
            yaml.dump(clean_data, f, default_flow_style=False, sort_keys=False, indent=2)
            
        # Update the internal cache
        self._cache = None  # Force reload on next access
