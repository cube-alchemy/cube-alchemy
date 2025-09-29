from __future__ import annotations
from pathlib import Path
from typing import Any, Dict

from .yaml_single_file import YAMLSource


class ModelYAMLSource(YAMLSource):
    """YAML source with model-aware mapping for queries, plots, and transformers.

        What this does (high level):
        - Load (YAML -> in-memory):
            - Lifts any nested sections under queries.<name>.{plots|transformers} to top-level buckets
                and adds a 'query' field so each item knows where it belongs.
            - Normalizes transformer specs to a canonical in-memory shape:
                {'transformer': <name>, 'params': {...}, 'query': <q>} (plus 'kind' and 'name' from the base normalizer).
            - Removes the nested sections from the queries (so there's a single source of truth in memory).
        - Save (in-memory -> YAML):
            - If prefer_nested_{plots|transformers} is True and an item references a known query,
                re-nests it back under queries.<name>.{plots|transformers}.
            - When nested, transformers are saved as params-only under queries.<name>.transformers[<name>].
            - Items with unknown/missing query remain top-level; top-level sections are removed when empty.

        Why this class matters:
        - It is the bridge between concise authoring in YAML and the strict shapes the cube expects.
            The cube's application layer (ModelCatalog) consumes transformers as
            {'transformer': name, 'params': {...}, 'query': q}. This class guarantees that normalized
            shape on load, while keeping the saved YAML compact and readable.

        Note: 
        Transformers and plots reference a query but are stored separately from queries in the hypercube. It was designed this way so we can re-define a query without needing to re-define its associated plots or transformations.

        Minimal example
        ---------------
                YAML (authoring-time, block-style):
                        queries:
                            q1:
                                dimensions:
                                    - Country
                                metrics:
                                    - Revenue
                                transformers:
                                    zscore:
                                        'on': Revenue
                                plots:
                                    bar_chart:
                                        plot_type: bar
                                        metrics:
                                            - Revenue

        After load (in-memory normalized view):
            transformers:
                zscore:
                    kind: transformers
                    name: zscore
                    transformer: zscore
                        params:
                            'on': Revenue
                    query: q1
            plots:
                bar_chart:
                    kind: plots
                    name: bar_chart
                    plot_type: bar
                    metrics:
                        - Revenue
                    query: q1
            queries:
                q1:
                    kind: queries
                    name: q1
                    dimensions:
                       - Country
                    metrics:
                       - Revenue
                    # no nested 'transformers' or 'plots' here (they were lifted)

        Round-trip (YAML -> memory -> YAML):
        - Starting from nested YAML and saving without edits emits the same structure
            (items with known queries remain nested; no inline maps are introduced).

    """

    def __init__(self, path: str | Path, prefer_nested_plots: bool = True, prefer_nested_transformers: bool = True) -> None:
        super().__init__(path)
        self.prefer_nested_plots = prefer_nested_plots
        self.prefer_nested_transformers = prefer_nested_transformers

    # Helper: lift nested section (plots/transformers) from queries to top-level with query metadata
    def _lift_nested_section(self, normalized: Dict[str, Dict[str, Any]], section: str) -> None:
        if "queries" not in normalized:
            return
        bucket: Dict[str, Any] = dict(normalized.get(section, {}))
        for qname, qspec in list(normalized.get("queries", {}).items()):
            if not isinstance(qspec, dict):
                continue
            q_items = qspec.pop(section, None)
            if not isinstance(q_items, dict):
                continue
            for iname, ispec in q_items.items():
                if not isinstance(ispec, dict):
                    continue
                # For transformers, create canonical spec with transformer/name & params
                if section == "transformers":
                    params = (
                        ispec.get("params") if isinstance(ispec.get("params"), dict)
                        else {k: v for k, v in ispec.items() if k not in ("kind", "name", "transformer")}
                    )
                    out = {"transformer": str(iname), "params": params, "kind": section, "name": str(iname), "query": qname}
                else:
                    out = dict(ispec)
                    out.setdefault("kind", section)
                    out.setdefault("name", str(iname))
                    out.setdefault("query", qname)
                
                # Use composite key for plots to avoid name collisions across queries
                if section == "plots":
                    bucket_key = f"{qname}:{str(iname)}"
                else:
                    bucket_key = str(iname)
                bucket[bucket_key] = out
        if bucket:
            # Ensure kind/name defaults also for pre-existing top-level entries
            flat: Dict[str, Any] = {}
            for iname, ispec in bucket.items():
                if not isinstance(ispec, dict):
                    flat[iname] = ispec
                    continue
                normalized_spec = dict(ispec)
                # Ensure canonical form for transformers: {'transformer': name, 'params': {...}, 'query'?: q}
                if section == "transformers":
                    params = (
                        normalized_spec.get("params") if isinstance(normalized_spec.get("params"), dict)
                        else {k: v for k, v in normalized_spec.items() if k not in ("kind", "name", "transformer", "query")}
                    )
                    # keep query annotation if present during normalized view
                    qref = normalized_spec.get("query")
                    
                    # Extract the original transformer name if it's a composite key
                    item_name = iname
                    if section == "transformers" and "query" in normalized_spec and ":" in iname:
                        _, item_name = iname.split(":", 1)
                    
                    normalized_spec = {"transformer": str(item_name), "params": params}
                    if qref is not None:
                        normalized_spec["query"] = qref
                
                # Extract the original item name for plots if it's a composite key
                item_name = iname
                if ":" in iname:
                    _, item_name = iname.split(":", 1)
                
                normalized_spec.setdefault("kind", section)
                normalized_spec.setdefault("name", str(item_name))
                flat[iname] = normalized_spec
            normalized[section] = flat

    # postprocess after base normalization (kinds -> name -> spec with kind/name filled)
    def _postprocess_loaded(self, normalized: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        # DRY: lift both sections the same way
        self._lift_nested_section(normalized, "plots")
        self._lift_nested_section(normalized, "transformers")
        return normalized

    # preprocess before saving (drop meta and optionally re-nest plots)
    def _preprocess_to_save(self, data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        # Work on a shallow copy first, then run the generic cleanup (avoids losing hints like 'query')
        work: Dict[str, Dict[str, Any]] = {
            kind: {name: (dict(spec) if isinstance(spec, dict) else spec) for name, spec in (items or {}).items()}
            for kind, items in (data or {}).items()
        }

        # Helper: DRY re-nesting logic for plots and transformers on the working copy
        def _renest_section(section: str, prefer_flag: bool) -> None:
            bucket = (work or {}).get(section, {}) or {}
            if not (prefer_flag and bucket and "queries" in work):
                return
            remaining: Dict[str, Any] = {}
            for iname, ispec in bucket.items():
                if not isinstance(ispec, dict):
                    continue
                
                # Extract original item name from composite key
                item_name = iname
                if ":" in iname:
                    qname_from_key, item_name = iname.split(":", 1)
                
                qname = ispec.get("query")
                target = work["queries"].get(qname) if qname else None
                if target:
                    q_items = target.setdefault(section, {})
                    if section == "transformers":
                        # canonical params-only
                        params = (
                            ispec.get("params") if isinstance(ispec.get("params"), dict)
                            else {k: v for k, v in ispec.items() if k not in ("kind", "name", "query", "transformer")}
                        )
                        q_items[str(item_name)] = params
                    else:
                        q_items[str(item_name)] = {k: v for k, v in ispec.items() if k not in ("kind", "name", "query")}
                else:
                    # Extract original item name from composite key for top-level items
                    item_name = iname
                    if ":" in iname:
                        _, item_name = iname.split(":", 1)
                        
                    # keep top-level; drop only kind/name; for transformers keep params-only at save-time
                    if section == "transformers":
                        params = (
                            ispec.get("params") if isinstance(ispec.get("params"), dict)
                            else {k: v for k, v in ispec.items() if k not in ("kind", "name", "transformer", "query")}
                        )
                        remaining[str(item_name)] = params
                    else:
                        remaining[str(item_name)] = {k: v for k, v in ispec.items() if k not in ("kind", "name")}
            if remaining:
                work[section] = remaining
            else:
                work.pop(section, None)

        # Optionally re-nest plots and transformers using the same logic
        _renest_section("plots", getattr(self, "prefer_nested_plots", True))
        _renest_section("transformers", getattr(self, "prefer_nested_transformers", True))

        # now do the generic cleanup (remove kind/name, drop None)
        clean = super()._preprocess_to_save(work)

        # Reorder keys within each query spec to a preferred order
        if "queries" in clean and isinstance(clean["queries"], dict):
            desired = [
                "dimensions",
                "metrics",
                "derived_metrics",
                "transformers",
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
