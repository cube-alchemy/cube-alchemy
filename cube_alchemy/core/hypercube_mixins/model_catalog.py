from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from cube_alchemy.catalogs import Catalog, Source, YAMLSource, ModelYAMLSource, Repository, InMemoryRepository


class ModelCatalog:
    """Hypercube component to sync model analytics (metrics, derived metrics, queries) and plotting (plot configs) components with a Catalog.

    Usage on a Hypercube instance:
    - cube.set_yaml_model_catalog(p*)    # set the YAML file path of model catalog source and then attach it to the hypercube
    - cube.load_from_model_catalog()     # load from source -> catalog repo -> define_* into cube
    - cube.save_to_model_catalog(path?)  # save current cube -> catalog repo -> catalog source
    """

    # Currently YAML-first for convenience. Generic hooks (set_model_catalog) allow plugging any other DefinitionSource/Repository.
    
    def __init__(self) -> None:
        self.model_catalog: Optional[Catalog] = None
        # YAML file path bound to this cube for model catalog
        self._model_yaml_path: Optional[Path] = None

    # ---------- YAMLsource wiring ----------
    def set_yaml_model_catalog(self, path: Optional[str] = None, use_current_directory: bool = True, create_if_missing: bool = True, 
                         default_yaml_name: Optional[str] = None, prefer_nested_plots: bool = True, prefer_nested_transformers: bool = True) -> Path:
        """Set the YAML file path to use for model definitions, and attach it to this cube.
        
        Args:
            path: Path to the YAML file, relative or absolute
            use_current_directory: If True and path is relative, use current working directory as base
            create_if_missing: If True, create the file with empty sections if it doesn't exist
            default_yaml_name: Default filename to use if path is None
            prefer_nested_plots: If True, plots will be nested under their parent queries in YAML
            prefer_nested_transformers: If True, transformers will be nested under parent queries in YAML
        """
        if default_yaml_name is None:
            default_yaml_name = "model_catalog.yaml"
        if path is None:
            path = default_yaml_name
        p = (Path.cwd() / path) if use_current_directory else Path(path)
        if not p.exists() and create_if_missing:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                "metrics: \nderived_metrics: \nqueries:",
                encoding="utf-8",
            )
        self._model_yaml_path = p.resolve()
        # Use the model-aware YAML source here; generic YAMLSource stays domain-agnostic
        source = ModelYAMLSource(p, prefer_nested_plots=prefer_nested_plots, prefer_nested_transformers=prefer_nested_transformers)
        self.set_model_catalog([source])
        self.log().info("Attached YAML definitions from %s to the model catalog.", self._model_yaml_path)
        return self._model_yaml_path

    def get_yaml_path_model_catalog(self) -> Optional[Path]:
        """Return the remembered YAML path (if attached)."""
        return self._model_yaml_path
    
    # ---------- generic source wiring ---------
    def set_model_catalog(self, sources: Iterable[Source], repo: Optional[Repository] = None) -> None:
        """Attach multiple DefinitionSources (merged by Catalog)."""
        src_list = list(sources)
        repo = repo or InMemoryRepository()
        catalog = Catalog(src_list, repo)
        self.model_catalog = catalog

    # ---------- high-level operations ----------
    def load_from_model_catalog(self, kinds: Optional[Iterable[str]] = None, reset_specs: bool = False, clear_repo: bool = False, reload_sources: bool = True) -> None:
        """Load from the active source into the Catalog, then apply to this cube.
        Order: metrics -> derived_metrics -> queries -> plots.
        clear_repo: If True, clear the existing repo before refreshing from source.
        reload_sources: If True, reload the sources before refreshing. This disables the cache and ensures that any changes in the source definitions are reflected in the Catalog.
        """
        catalog = self._require_model_catalog_()
        catalog.refresh(kinds=kinds, reload_sources=reload_sources, clear_repo=clear_repo)
        if reset_specs:
            self.reset_specs()
        self._apply_catalog_to_hypercube(catalog, kinds=kinds)

    def _model_catalog_pull_from_cube(self) -> None:
        """Extract current cube definitions into the Catalog repository (does not save)."""
        catalog = self._require_model_catalog_()
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

    def save_to_model_catalog(self, prefer_nested_plots: bool = True, prefer_nested_transformers: bool = True) -> Optional[Path]:
        """Save the cube's current state to the model catalog.
        
        Args:
            prefer_nested_plots: If True, plots will be nested under their parent queries in YAML
            prefer_nested_transformers: If True, transformers will be nested under parent queries in YAML
            
        Returns:
            Path to the saved YAML file if available, otherwise None
        """
        # Ensure repo reflects current cube state
        self._model_catalog_pull_from_cube()
        catalog = self._require_model_catalog_()
        # Build data structure from repo
        data: Dict[str, Dict[str, Any]] = {}
        for kind, name in catalog.repo.list():
            data.setdefault(kind, {})
            spec = catalog.get(kind, name)
            if spec is not None:
                data[kind][name] = spec
        # Save through all sources
        if not getattr(catalog, 'sources', None):
            raise RuntimeError("No sources attached to Catalog; cannot save.")
            
        # Update preferences for ModelYAMLSource instances before saving
        for source in catalog.sources:
            if isinstance(source, ModelYAMLSource):
                source.prefer_nested_plots = prefer_nested_plots
                source.prefer_nested_transformers = prefer_nested_transformers
            source.save(data)
            
        self.log().info(
            "Saved model definitions via %s source(s). %s",
            len(catalog.sources),
            ('YAML file -> ' + str(self._model_yaml_path)) if self._model_yaml_path else ''
        )
        
        return self._model_yaml_path

    # ---------- Catalog -> cube ----------
    def _apply_catalog_to_hypercube(self, catalog: Catalog, kinds: Optional[Iterable[str]] = None) -> None:
        kinds_set = set(kinds) if kinds else None

        def _do(k: str) -> bool:
            return (kinds_set is None) or (k in kinds_set)

        if _do("metrics"):
            for name in catalog.list("metrics"):
                spec = catalog.get("metrics", name) or {}
                self._apply_metric_to_hypercube(name, spec)

        if _do("derived_metrics"):
            for name in catalog.list("derived_metrics"):
                spec = catalog.get("derived_metrics", name) or {}
                self._apply_derived_metric_to_hypercube(name, spec)

        if _do("queries"):
            for name in catalog.list("queries"):
                spec = catalog.get("queries", name) or {}
                self._apply_query_to_hypercube(name, spec)

        if _do("plots"):
            for name in catalog.list("plots"):
                spec = catalog.get("plots", name) or {}
                self._apply_plot_to_hypercube(name, spec)

        if _do("transformers"):
            for name in catalog.list("transformers"):
                spec = catalog.get("transformers", name) or {}
                self._apply_transformer_to_hypercube(name, spec)

    def _apply_metric_to_hypercube(self, name: str, spec: Dict[str, Any]) -> None:
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
            nested=spec.get("nested"),
        )

    def _apply_derived_metric_to_hypercube(self, name: str, spec: Dict[str, Any]) -> None:
        self.define_derived_metric(
            name=name,
            expression=str(spec.get("expression", "")),
            fillna=spec.get("fillna"),
        )

    def _parse_sort_to_hypercube(self, sort_val: Any) -> List[Tuple[str, str]]:
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

    def _apply_query_to_hypercube(self, name: str, spec: Dict[str, Any]) -> None:
        self.define_query(
            name=name,
            dimensions=spec.get("dimensions", []) or [],
            metrics=spec.get("metrics", []) or [],
            derived_metrics=spec.get("derived_metrics", []) or [],
            having=spec.get("having"),
            sort=self._parse_sort_to_hypercube(spec.get("sort")),
            drop_null_dimensions=spec.get("drop_null_dimensions", False),
            drop_null_metric_results=spec.get("drop_null_metric_results", False),
        )

    def _apply_plot_to_hypercube(self, plot_name: str, spec: Dict[str, Any]) -> None:
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
            sort_by=spec.get("sort_by"),
            pivot=spec.get("pivot"),
            limit=spec.get("limit"),
            formatter=spec.get("formatter"),
            annotations=spec.get("annotations"),
            custom_options=spec.get("custom_options"),
            set_as_default=set_default,
        )

    def _apply_transformer_to_hypercube(self, transformer_name: str, spec: Dict[str, Any]) -> None:
        """Apply a saved transformer config to the cube for a given query (single-step model)."""
        query_name = spec.get("query")
        if not query_name:
            raise ValueError(f"Transformer '{transformer_name}' missing 'query' reference")

        transformer = spec.get("transformer") or transformer_name
        params = spec.get("params") or {}
        if not transformer:
            raise ValueError(f"Transformer '{transformer_name}' missing 'transformer'")
        self.define_transformation(
            query_name=query_name,
            transformer=transformer,
            params=params,
        )
        # Strict keys
        allowed_keys = {"query", "transformer", "params", "kind", "name"}
        unexpected = set(spec.keys()) - allowed_keys
        if unexpected:
            raise ValueError(f"Unsupported keys in transformer spec for '{transformer_name}': {sorted(unexpected)}")

    # ---------- mapping: cube -> specs ----------
    def _extract_cube_to_specs_(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        data: Dict[str, Dict[str, Dict[str, Any]]] = {
            "metrics": {},
            "derived_metrics": {},
            "queries": {},
            "plots": {},
            "transformers": {},
        }

        # Metrics
        metrics = getattr(self, "metrics", {})
        for name, metric_obj in (metrics or {}).items():
            try:
                details = metric_obj.get_metric_details()  # Expected in Metric class
            except Exception:
                details = {}
            data["metrics"][name] = details

        # Derived metrics
        derived_metrics = getattr(self, "derived_metrics", {})
        for name, cm_obj in (derived_metrics or {}).items():
            try:
                details = cm_obj.get_derived_metric_details()  # Expected in DerivedMetric class
            except Exception:
                details = {}
            data["derived_metrics"][name] = details

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

        # Transformers: per-query mapping transformer->params; flatten
        transformation_state = getattr(self, "transformation_components", {})
        if isinstance(transformation_state, dict):
            for query_name, estate in transformation_state.items():
                for transformer, params in (estate or {}).items():
                    out = {"transformer": transformer, "params": dict(params or {}), "query": query_name}
                    data["transformers"][transformer] = out

        return data

    # ---------- guards ----------
    def _require_model_catalog_(self) -> Catalog:
        if not self.model_catalog:
            raise RuntimeError("No definitions source attached. Call set_yaml_model_catalog(...) or model_catalog_attach_source(...) first.")
        return self.model_catalog

    def _require_repo_(self) -> Repository:
        if not self.model_catalog.repo:
            raise RuntimeError("Catalog repository not initialized.")
        return self.model_catalog.repo