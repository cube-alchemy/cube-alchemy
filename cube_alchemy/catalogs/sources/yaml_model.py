from __future__ import annotations
from pathlib import Path
from typing import Any, Dict

from .yaml_single_file import YAMLSource


class ModelYAMLSource(YAMLSource):
    """YAML source with model-specific conveniences (queries<->plots nesting).

    - On load: lifts nested queries.<name>.plots into top-level 'plots' with a 'query' field.
    - On save: if both 'queries' and 'plots' exist, nests plots back under their query unless
      the plot references an unknown query (then it stays top-level under 'plots').
    """

    def __init__(self, path: str | Path, prefer_nested_plots: bool = True) -> None:
        super().__init__(path)
        self.prefer_nested_plots = prefer_nested_plots

    # postprocess after base normalization (kinds -> name -> spec with kind/name filled)
    def _postprocess_loaded(self, normalized: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        if "queries" not in normalized:
            return normalized
        plots_bucket: Dict[str, Any] = dict(normalized.get("plots", {}))
        for qname, qspec in list(normalized["queries"].items()):
            if not isinstance(qspec, dict):
                continue
            q_plots = qspec.pop("plots", None)
            if isinstance(q_plots, dict):
                for pname, pspec in q_plots.items():
                    if not isinstance(pspec, dict):
                        continue
                    out = dict(pspec)
                    out.setdefault("kind", "plots")
                    out.setdefault("name", str(pname))
                    out.setdefault("query", qname)
                    plots_bucket[str(pname)] = out
        if plots_bucket:
            normalized["plots"] = plots_bucket
        return normalized

    # preprocess before saving (drop meta and optionally re-nest plots)
    def _preprocess_to_save(self, data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        # first do the generic cleanup (remove kind/name, drop None)
        clean = super()._preprocess_to_save(data)
        plots = (data or {}).get("plots", {}) or {}
        if not plots:
            return clean
        if not self.prefer_nested_plots:
            return clean  # leave plots at top-level as they came
        if "queries" not in clean:
            return clean
        # nest plots under queries when possible
        remaining_top_level_plots: Dict[str, Any] = {}
        for pname, pspec in plots.items():
            if not isinstance(pspec, dict):
                continue
            qname = pspec.get("query")
            target = clean["queries"].get(qname) if qname else None
            if not target:
                # unknown query or missing reference: keep top-level
                remaining_top_level_plots[pname] = {k: v for k, v in pspec.items() if k not in ("kind", "name")}
                continue
            q_plots = target.setdefault("plots", {})
            q_plots[pname] = {k: v for k, v in pspec.items() if k not in ("kind", "name", "query")}
        if remaining_top_level_plots:
            clean.setdefault("plots", {}).update(remaining_top_level_plots)
        return clean
