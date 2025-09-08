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

    def __init__(self, path: str | Path, prefer_nested_plots: bool = True, prefer_nested_enrichers: bool = True) -> None:
        super().__init__(path)
        self.prefer_nested_plots = prefer_nested_plots
        self.prefer_nested_enrichers = prefer_nested_enrichers

    # postprocess after base normalization (kinds -> name -> spec with kind/name filled)
    def _postprocess_loaded(self, normalized: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        if "queries" not in normalized:
            return normalized
        # Lift nested plots
        plots_bucket: Dict[str, Any] = dict(normalized.get("plots", {}))
        # Lift nested enrichers
        enrichers_bucket: Dict[str, Any] = dict(normalized.get("enrichers", {}))

        for qname, qspec in list(normalized["queries"].items()):
            if not isinstance(qspec, dict):
                continue
            # Nested plots -> top level
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
            # Nested enrichers -> top level
            q_enrichers = qspec.pop("enrichers", None)
            if isinstance(q_enrichers, dict):
                for ename, espec in q_enrichers.items():
                    if not isinstance(espec, dict):
                        continue
                    # Flatten: use the key (transformer) and keep only params; drop redundant 'transformer'/'params'
                    params = (
                        espec.get("params")
                        if isinstance(espec.get("params"), dict)
                        else {k: v for k, v in espec.items() if k not in ("kind", "name", "transformer")}
                    )
                    out = {**params, "kind": "enrichers", "name": str(ename), "query": qname}
                    enrichers_bucket[str(ename)] = out

        if plots_bucket:
            normalized["plots"] = plots_bucket
        if enrichers_bucket:
            # Also flatten any pre-existing top-level enricher specs that still use 'transformer'/'params'
            flat_bucket: Dict[str, Any] = {}
            for ename, espec in enrichers_bucket.items():
                if not isinstance(espec, dict):
                    flat_bucket[ename] = espec
                    continue
                params = (
                    espec.get("params")
                    if isinstance(espec.get("params"), dict)
                    else {k: v for k, v in espec.items() if k not in ("kind", "name", "transformer")}
                )
                # preserve query if provided
                qref = espec.get("query")
                out = {**params}
                if qref is not None:
                    out["query"] = qref
                out.setdefault("kind", "enrichers")
                out.setdefault("name", str(ename))
                flat_bucket[ename] = out
            normalized["enrichers"] = flat_bucket
        return normalized

    # preprocess before saving (drop meta and optionally re-nest plots)
    def _preprocess_to_save(self, data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        # first do the generic cleanup (remove kind/name, drop None)
        clean = super()._preprocess_to_save(data)

        # Optionally re-nest plots
        plots = (data or {}).get("plots", {}) or {}
        if plots and self.prefer_nested_plots and "queries" in clean:
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

        # Optionally re-nest enrichers
        enrichers = (data or {}).get("enrichers", {}) or {}
        if getattr(self, 'prefer_nested_enrichers', True) and "queries" in clean:
            # First, canonicalize any already nested enrichers to {transformer: params}
            for qname, qspec in list(clean.get("queries", {}).items()):
                if not isinstance(qspec, dict):
                    continue
                q_enr = qspec.get("enrichers")
                if not isinstance(q_enr, dict):
                    continue
                norm: Dict[str, Any] = {}
                for ename, espec in q_enr.items():
                    if not isinstance(espec, dict):
                        norm[str(ename)] = espec
                        continue
                    tkey = espec.get("transformer", str(ename))
                    params = (
                        espec.get("params")
                        if isinstance(espec.get("params"), dict)
                        else {k: v for k, v in espec.items() if k not in ("transformer",)}
                    )
                    norm[str(tkey)] = params
                qspec["enrichers"] = norm

            # Then, re-nest any top-level enrichers into their queries using the same canonical form
            remaining_top_level_enrichers: Dict[str, Any] = {}
            for ename, espec in (enrichers or {}).items():
                if not isinstance(espec, dict):
                    continue
                qname = espec.get("query")
                target = clean["queries"].get(qname) if qname else None
                tkey = espec.get("transformer", str(ename))
                params = (
                    espec.get("params")
                    if isinstance(espec.get("params"), dict)
                    else {k: v for k, v in espec.items() if k not in ("kind", "name", "query", "transformer")}
                )
                if target:
                    q_enr = target.setdefault("enrichers", {})
                    q_enr[str(tkey)] = params
                else:
                    # keep as top-level but drop redundant keys; retain query to keep reference
                    flat = dict(params)
                    if qname is not None:
                        flat["query"] = qname
                    remaining_top_level_enrichers[str(tkey)] = flat

            # Replace/clear top-level enrichers depending on if any remain
            if remaining_top_level_enrichers:
                clean["enrichers"] = remaining_top_level_enrichers
            else:
                clean.pop("enrichers", None)

        # Reorder keys within each query spec to a preferred order
        if "queries" in clean and isinstance(clean["queries"], dict):
            desired = [
                "dimensions",
                "metrics",
                "derived_metrics",
                "enrichers",
                "having",
                "sort",
                "plots",
            ]
            for qname, qspec in list(clean["queries"].items()):
                if not isinstance(qspec, dict):
                    continue
                ordered: Dict[str, Any] = {}
                # place desired keys first if present
                for key in desired:
                    if key in qspec:
                        ordered[key] = qspec[key]
                # append any remaining keys preserving existing order
                for key, val in qspec.items():
                    if key not in ordered:
                        ordered[key] = val
                clean["queries"][qname] = ordered

        return clean
