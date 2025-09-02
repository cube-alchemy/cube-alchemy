from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from cube_alchemy.model_definitions import Catalog, YAMLDefinitionSource, DefinitionRepository, InMemoryRepository


class ModelDefinitions:
    """Hypercube component to sync model definitions (metrics, queries, plots) with a Catalog.

    Usage on a Hypercube instance (mixed in via multiple inheritance):
      - cube.definitions_set_yaml(p)            # set the YAML file path and then attach it to the hypercube
        - cube._definitions_attach_yaml(p)       # attach a YAML file to the hypercube as the source
      - cube.definitions_refresh_into_cube()    # load from YAML -> catalog -> define_* into cube
      - cube.definitions_pull_from_cube()       # extract cube -> catalog repo
      - cube.definitions_save(path?)            # save current repo -> YAML
      - cube.definitions_list(kind)             # helper to inspect loaded items
    """

    # I am making this implementation tight to yaml definition source, but it could be generalized to any type of source, just need to re-write the yaml specific methods.
    # ---------- lifecycle ----------
    def __init__(self) -> None:
        # Late-bound wiring: call definitions_set_yaml when ready
        self._definitions_repo: Optional[DefinitionRepository] = None
        self._definitions_source: Optional[YAMLDefinitionSource] = None
        self._definitions_catalog: Optional[Catalog] = None
        # Remember the YAML file path bound to this cube (if any)
        self._definitions_yaml_path = None

    # ---------- source wiring ----------
    def definitions_get_yaml_path(self) -> Optional[Path]:
        """Return the remembered YAML path (if attached)."""
        return self._definitions_yaml_path

    def definitions_set_yaml(self, path: Optional[str], use_current_directory: bool = True, create_if_missing: bool = True) -> Path:
        """Set the YAML file path to use for model definitions, and attach it to this cube."""
        default_yaml_name = "model_definitions.yaml"
        if path is None:
            path = default_yaml_name
        p = (Path.cwd() / path) if use_current_directory else Path(path)
        if not p.exists() and create_if_missing:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                "metrics: {}\ncomputed_metrics: {}\nqueries: {}\nplots: {}\n",
                encoding="utf-8",
            )
        self._definitions_yaml_path = p.resolve()
        self._definitions_attach_yaml()
        print(f'Attached YAML definitions from {self._definitions_yaml_path}')
        return self._definitions_yaml_path

    def _definitions_attach_yaml(self) -> None:

        p = self._definitions_yaml_path

        source = YAMLDefinitionSource(p)
        repo = InMemoryRepository()
        catalog = Catalog([source], repo)

        self._definitions_source = source
        self._definitions_repo = repo
        self._definitions_catalog = catalog

    # ---------- high-level operations ----------
    def definitions_refresh_into_cube(self, kinds: Optional[Iterable[str]] = None) -> None:
        """Load from the active source into the Catalog, then apply to this cube.
        Order: metrics -> computed_metrics -> queries -> plots.
        """
        catalog = self._require_catalog_()
        catalog.refresh(kinds=kinds)
        self._apply_catalog_to_cube_(catalog, kinds=kinds)

    def definitions_pull_from_cube(self) -> None:
        """Extract current cube definitions into the Catalog repository (does not save)."""
        catalog = self._require_catalog_()
        repo = self._require_repo_()

        # Clear repo by deleting existing entries
        existing = list(repo.list())
        for k, n in existing:
            repo.delete(k, n)

        data = self._extract_cube_to_specs_()
        for kind, items in data.items():
            repo.add_kind(kind)
            for name, spec in items.items():
                spec.setdefault("kind", kind)
                spec.setdefault("name", name)
                repo.put(kind, name, spec)

    def definitions_save_to_yaml(self, filepath: Optional[str | Path] = None) -> None:
        """Persist current Catalog repository to YAML (via YAMLDefinitionSource)."""
        self.definitions_pull_from_cube()
        catalog = self._require_catalog_()
        # If no explicit filepath provided, prefer stored YAML path when available
        target = Path(filepath) if filepath is not None else (self._definitions_yaml_path or None)
        catalog.save(target)
        print(f'Saved model definitions to {target}')

    def definitions_list(self, kind: Optional[str] = None) -> List[str]:
        catalog = self._require_catalog_()
        return catalog.list(kind)

    # ---------- mapping: Catalog -> cube ----------
    def _apply_catalog_to_cube_(self, catalog: Catalog, kinds: Optional[Iterable[str]] = None) -> None:
        kinds_set = set(kinds) if kinds else None

        def _do(k: str) -> bool:
            return (kinds_set is None) or (k in kinds_set)

        if _do("metrics"):
            for name in catalog.list("metrics"):
                spec = catalog.get("metrics", name) or {}
                self._apply_metric_(name, spec)

        if _do("computed_metrics"):
            for name in catalog.list("computed_metrics"):
                spec = catalog.get("computed_metrics", name) or {}
                self._apply_computed_metric_(name, spec)

        if _do("queries"):
            for name in catalog.list("queries"):
                spec = catalog.get("queries", name) or {}
                self._apply_query_(name, spec)

        if _do("plots"):
            for name in catalog.list("plots"):
                spec = catalog.get("plots", name) or {}
                self._apply_plot_(name, spec)

    def _apply_metric_(self, name: str, spec: Dict[str, Any]) -> None:
        self.define_metric(
            name=name,
            expression=spec.get("expression"),
            aggregation=spec.get("aggregation"),
            metric_filters=spec.get("metric_filters"),
            row_condition_expression=spec.get("row_condition_expression"),
            context_state_name=spec.get("context_state_name", "Default"),
            ignore_dimensions=spec.get("ignore_dimensions", False),
            ignore_context_filters=spec.get("ignore_context_filters", False),
            fillna=spec.get("fillna"),
        )

    def _apply_computed_metric_(self, name: str, spec: Dict[str, Any]) -> None:
        self.define_computed_metric(
            name=name,
            expression=str(spec.get("expression", "")),
            fillna=spec.get("fillna"),
        )

    def _parse_sort_(self, sort_val: Any) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        if not sort_val:
            return out
        if isinstance(sort_val, list):
            for item in sort_val:
                if isinstance(item, dict) and "column" in item:
                    out.append((str(item["column"]), str(item.get("direction", "asc")).lower()))
                elif isinstance(item, (list, tuple)) and len(item) >= 1:
                    col = str(item[0])
                    direction = str(item[1]).lower() if len(item) > 1 else "asc"
                    out.append((col, direction))
                elif isinstance(item, str):
                    parts = item.split()
                    col = parts[0]
                    direction = parts[1].lower() if len(parts) > 1 else "asc"
                    out.append((col, direction))
        return out

    def _apply_query_(self, name: str, spec: Dict[str, Any]) -> None:
        self.define_query(
            name=name,
            dimensions=spec.get("dimensions", []) or [],
            metrics=spec.get("metrics", []) or [],
            computed_metrics=spec.get("computed_metrics", []) or [],
            having=spec.get("having"),
            sort=self._parse_sort_(spec.get("sort")),
            drop_null_dimensions=spec.get("drop_null_dimensions", False),
            drop_null_metric_results=spec.get("drop_null_metric_results", False),
        )

    def _apply_plot_(self, plot_name: str, spec: Dict[str, Any]) -> None:
        query_name = spec.get("query")
        if not query_name:
            raise ValueError(f"Plot '{plot_name}' missing 'query' reference")
        figsize_val = spec.get("figsize")
        figsize = tuple(figsize_val) if isinstance(figsize_val, (list, tuple)) else figsize_val
        # Decide default: if not specified in spec, make the first plot per query the default
        qstate = getattr(self, 'plotting_components', {}).get(query_name) if hasattr(self, 'plotting_components') else None
        default_exists = bool(qstate and qstate.get('default')) if isinstance(qstate, dict) else False
        set_default = spec.get("set_as_default") if "set_as_default" in spec else (not default_exists)

        self.define_plot(
            query_name=query_name,
            plot_name=plot_name,
            plot_type=spec.get("plot_type"),
            dimensions=spec.get("dimensions"),
            metrics=spec.get("metrics"),
            color_by=spec.get("color_by"),
            title=spec.get("title"),
            stacked=spec.get("stacked", False),
            figsize=figsize,
            orientation=spec.get("orientation", "vertical"),
            palette=spec.get("palette"),
            sort_values=spec.get("sort_values", False),
            sort_ascending=spec.get("sort_ascending", True),
            limit=spec.get("limit"),
            formatter=spec.get("formatter"),
            annotations=spec.get("annotations"),
            custom_options=spec.get("custom_options"),
            set_as_default=set_default,
        )

    # ---------- mapping: cube -> specs ----------
    def _extract_cube_to_specs_(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        data: Dict[str, Dict[str, Dict[str, Any]]] = {
            "metrics": {},
            "computed_metrics": {},
            "queries": {},
            "plots": {},
        }

        # Metrics
        metrics = getattr(self, "metrics", {})
        for name, metric_obj in (metrics or {}).items():
            try:
                details = metric_obj.get_metric_details()  # Expected in Metric class
            except Exception:
                details = {}
            data["metrics"][name] = details

        # Computed metrics
        computed_metrics = getattr(self, "computed_metrics", {})
        for name, cm_obj in (computed_metrics or {}).items():
            try:
                details = cm_obj.get_computed_metric_details()  # Expected in ComputedMetric class
            except Exception:
                details = {}
            data["computed_metrics"][name] = details

        # Queries
        queries = getattr(self, "queries", {})
        for name in (queries or {}).keys():
            try:
                qspec = self.get_query(name)
            except Exception:
                qspec = queries.get(name, {})
            # Normalize sort to list[{'column','direction'}] for readability
            sort = qspec.get("sort") or []
            norm_sort: List[Dict[str, str]] = []
            if isinstance(sort, list):
                for item in sort:
                    if isinstance(item, (list, tuple)) and len(item) >= 1:
                        norm_sort.append({"column": item[0], "direction": (item[1] if len(item) > 1 else "asc")})
                    elif isinstance(item, dict) and "column" in item:
                        norm_sort.append({"column": item["column"], "direction": item.get("direction", "asc")})
                    elif isinstance(item, str):
                        parts = item.split()
                        norm_sort.append({"column": parts[0], "direction": (parts[1] if len(parts) > 1 else "asc")})
            qcopy = dict(qspec)
            qcopy["sort"] = norm_sort
            data["queries"][name] = qcopy

        # Plots: stored per-query inside plotting_components; flatten
        plotting_state = getattr(self, "plotting_components", {})
        if isinstance(plotting_state, dict):
            for query_name, qstate in plotting_state.items():
                plots = (qstate or {}).get("plots", {})
                for plot_name, pspec in (plots or {}).items():
                    out = dict(pspec)
                    out["query"] = query_name
                    out.pop("_input_dimensions", None)
                    out.pop("_input_metrics", None)
                    data["plots"][plot_name] = out

        return data

    # ---------- guards ----------
    def _require_catalog_(self) -> Catalog:
        if not self._definitions_catalog:
            raise RuntimeError("No definitions source attached. Call definitions_set_yaml_path() first.")
        return self._definitions_catalog

    def _require_repo_(self) -> DefinitionRepository:
        if not self._definitions_repo:
            raise RuntimeError("Catalog repository not initialized.")
        return self._definitions_repo

    
