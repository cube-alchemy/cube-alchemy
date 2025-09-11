from typing import List, Dict, Any, Optional, Union, Callable, Tuple
from ..metric import Metric, DerivedMetric, extract_columns
import re
import warnings

class AnalyticsSpecs:
    
    def define_metric(
        self,
        name: Optional[str] = None,
        expression: Optional[str] = None,
        aggregation: Optional[Union[str, Callable[[Any], Any]]] = None,
        metric_filters: Optional[Dict[str, Any]] = None,
        row_condition_expression: Optional[str] = None,
        context_state_name: str = 'Default',
        ignore_dimensions: bool = False,
        ignore_context_filters: bool = False,
        fillna: Optional[Any] = None,
        nested: Optional[Dict[str, Any]] = None,
    ) -> None:
        new_metric = Metric(
            name,
            expression,
            aggregation,
            metric_filters,
            row_condition_expression,
            context_state_name,
            ignore_dimensions,
            ignore_context_filters,
            fillna,
            nested,
        )

        # define metric column indexes. To be used on queries to traverse the tree
        metric_tables: set[str] = set()
        metric_columns_indexes: set[str] = set()

        for column in new_metric.columns:
            table_name = self.column_to_table.get(column)
            if table_name:
                metric_tables.add(table_name)
            else:
                warnings.warn(f"Column {column} not found in any table.")

        metric_tables_dict = {tname: self.tables[tname] for tname in metric_tables if tname is not None}
        trajectory_tables = self._find_complete_trajectory(metric_tables_dict)

        for tname in trajectory_tables:
            if tname not in self.link_tables:
                metric_columns_indexes.add(f"_index_{tname}")

        # add metric_columns_indexes to the new metric object
        new_metric.columns_indexes = list(metric_columns_indexes)
        self.metrics[new_metric.name] = new_metric

        new_metric.query_relevant_columns = list(set(new_metric.nested_dimensions + new_metric.columns + new_metric.columns_indexes))

        # Register and refresh dependents (queries referencing this metric, even if previously missing)
        self._refresh_queries_dependent_on(new_metric.name, is_derived_metric=False)
        # Targeted refresh handled by dependency index
    
    def define_derived_metric(self, name: str, expression: str, fillna: Optional[Any] = None) -> None:
        """Persist a post-aggregation derived metric as a DerivedMetric instance.

        These metrics are evaluated after base metrics aggregation in queries.
        Use [Column] syntax to reference aggregated columns or dimensions.
        """
        if not isinstance(name, str) or not name:
            raise ValueError("Derived metric requires a non-empty string name.")
        if not isinstance(expression, str) or not expression:
            raise ValueError("Derived metric requires a non-empty string expression.")

        self.derived_metrics[name] = DerivedMetric(name=name, expression=expression, fillna=fillna)

        # Register and refresh dependents (queries referencing this derived metric, even if previously missing)
        self._refresh_queries_dependent_on(name, is_derived_metric=True)
        # Targeted refresh handled by dependency index

    def define_query(
        self,
        name: str,
        dimensions: set[str] = {},
        metrics: List[str] = [],
        derived_metrics: List[str] = [],
        having: Optional[str] = None,
        sort: List[Tuple[str, str]] = [],        
        drop_null_dimensions: bool = False,
        drop_null_metric_results: bool = False,
    ):
        # Normalize dimensions to list but preserve provided order if it's already a list
        dimensions = list(dimensions)

        # Validate metric names exist now, but store only names to keep linkage live
        for metric_name in metrics:
            if metric_name not in self.metrics:
                self.log().warning(f"Metric '{metric_name}' is not defined when defining query '{name}'. Define it with define_metric().")

        for derived_metrics_name in derived_metrics:
            if derived_metrics_name not in self.derived_metrics:
                self.log().warning(
                    f"Derived metric '{derived_metrics_name}' is not defined when defining query '{name}'. Define it with define_derived_metric()."
                )
        
        having_columns: List[str] = extract_columns(having) if having else []

        # --- Precompute hidden (internal) base metrics required ---
        hidden_metrics: List[str] = []
        # From derived metrics' expressions
        for cm_name in derived_metrics:
            if cm_name in self.derived_metrics:
                for col in self.derived_metrics[cm_name].columns:
                    if col in self.metrics and col not in metrics and col not in hidden_metrics:
                        hidden_metrics.append(col)
        # From HAVING expression referenced columns
        for col in having_columns:
            if col in self.metrics and col not in metrics and col not in hidden_metrics:
                hidden_metrics.append(col)
        # From SORT columns
        for sort_col, _dir in sort:
            if sort_col in self.metrics and sort_col not in metrics and sort_col not in hidden_metrics:
                hidden_metrics.append(sort_col)

        # --- Precompute hidden derived metrics and dependency order ---
        # Any derived metric referenced by requested derived metrics, HAVING, or SORT
        hidden_derived_metrics: List[str] = []
        referenced_computed: set[str] = set()
        for cm_name in derived_metrics:
            if cm_name in self.derived_metrics:
                for col in self.derived_metrics[cm_name].columns:
                    if col in self.derived_metrics and col not in derived_metrics and col not in hidden_derived_metrics:
                        hidden_derived_metrics.append(col)
                        referenced_computed.add(col)
        for col in having_columns:
            if col in self.derived_metrics and col not in derived_metrics and col not in hidden_derived_metrics:
                hidden_derived_metrics.append(col)
                referenced_computed.add(col)
        for sort_col, _dir in sort:
            if sort_col in self.derived_metrics and sort_col not in derived_metrics and sort_col not in hidden_derived_metrics:
                hidden_derived_metrics.append(sort_col)
                referenced_computed.add(sort_col)

        # Build dependency graph for all derived metrics involved in this query (we need to execute them in order to work)
        def build_cm_dependencies(names: List[str]) -> Dict[str, List[str]]:
            deps: Dict[str, List[str]] = {}
            for n in names:
                if n not in self.derived_metrics:
                    continue
                cm = self.derived_metrics[n]
                # dependencies are other derived metric names referenced in expression
                deps[n] = [c for c in cm.columns if c in self.derived_metrics]
            return deps

        # the set of derived metrics that might need evaluation
        all_cm_names: List[str] = []
        for n in derived_metrics + hidden_derived_metrics:
            if n not in all_cm_names:
                all_cm_names.append(n)
        cm_deps = build_cm_dependencies(all_cm_names)

        # Topologically sort derived metrics to a safe evaluation order
        derived_metrics_ordered: List[str] = []
        temp_mark: set[str] = set()
        perm_mark: set[str] = set()

        def visit(node: str):
            if node in perm_mark:
                return
            if node in temp_mark:
                raise ValueError(f"Cycle detected in derived metrics dependencies involving '{node}'.")
            temp_mark.add(node)
            for d in cm_deps.get(node, []):
                visit(d)
            temp_mark.remove(node)
            perm_mark.add(node)
            if node not in derived_metrics_ordered:
                derived_metrics_ordered.append(node)

        for node in all_cm_names:
            visit(node)

        # Build the set of referenced names to track missing items for fast auto-refresh.
        all_used_columns = set(metrics) | set(derived_metrics)
        # From derived metrics expressions (only those that exist at the moment)
        for cm_name in derived_metrics:
            cm_obj = self.derived_metrics.get(cm_name)
            if cm_obj:
                for col in cm_obj.columns:
                    all_used_columns.add(col)
        # From HAVING and SORT
        for col in having_columns:
            all_used_columns.add(col)
        for sc, _ in sort:
            all_used_columns.add(sc)

        # Only consider tokens that are NOT dimensions and are plausible metric/derived metric names.
        missing_column_names = sorted([n for n in all_used_columns if n not in self.metrics and n not in self.derived_metrics and n not in self.get_dimensions()])

        # Register dependency edges for targeted refreshes
        try:
            if hasattr(self, '_dep_index') and self._dep_index is not None:
                # Remove old edges pointing to this query to avoid accumulation
                self._dep_index.remove_query(name)
                # Sources:
                # - explicit + hidden base metrics
                # - explicit + hidden derived metrics
                dep_sources = set(metrics) | set(hidden_metrics) | set(derived_metrics) | set(hidden_derived_metrics)

                # Include HAVING/SORT tokens only if they resolve to existing metric/derived metric names.
                # Missing HAVING/SORT tokens will be captured via missing_column_names below.
                for col in having_columns:
                    if col in self.metrics or col in self.derived_metrics:
                        dep_sources.add(col)
                for sort_col, _ in sort:
                    if sort_col in self.metrics or sort_col in self.derived_metrics:
                        dep_sources.add(sort_col)

                # Add unresolved tokens (not metrics, not derived metrics, not dimensions)
                dep_sources |= set(missing_column_names)
                for src in dep_sources:
                    self._dep_index.add(src, 'query', name)
        except Exception as _:
            # Non-fatal if dependency registration fails
            pass

        self.queries[name] = {
            "dimensions": dimensions,
            "metrics": metrics,
            "derived_metrics": derived_metrics,
            "having": having,
            "having_columns": having_columns,
            "sort": sort,

            # Precomputed internal helpers to avoid recomputation at runtime
            "hidden_metrics": hidden_metrics,
            "hidden_derived_metrics": hidden_derived_metrics,

            # Full ordered list to evaluate (requested + hidden, in dependency order)
            "derived_metrics_ordered": derived_metrics_ordered,

            "drop_null_dimensions": drop_null_dimensions,
            "drop_null_metric_results": drop_null_metric_results,
            # Tracking for fast re-definition when missing items get defined later
            "missing_column_names": missing_column_names,
        }

        # if there exists a plot configured with this query, we might need to update it
        q_state = getattr(self, 'plotting_components', {}).get(name)
        if q_state and q_state.get('plots'):
            self.log().info("Plots configuration for query '%s' will be updated due to query re-definition.", name)
            # Remove existing edges query->plot to avoid stale duplicates
            try:
                if hasattr(self, '_dep_index') and self._dep_index is not None:
                    for plot_name in list(q_state['plots'].keys()):
                        self._dep_index.remove_plot(plot_name)
            except Exception:
                pass
            for plot_name, plot_config in q_state['plots'].items():
                new_plot = plot_config
                new_plot['dimensions'] = plot_config.get('_input_dimensions', [])
                new_plot['metrics'] = plot_config.get('_input_metrics', [])
                new_plot.pop('_input_dimensions', None)
                new_plot.pop('_input_metrics', None)

                # if the query has more (or less) dimensions/metrics, we need to update the plot config too
                self.define_plot(
                    query_name=name,
                    plot_name=plot_name,
                    **new_plot
                )

    def _refresh_queries_dependent_on(self, metric_name: str, is_derived_metric: bool) -> None:
        """Refresh queries that depend on the given metric/derived metric using the dependency index."""
        try:
            index = getattr(self, '_dep_index', None)
            if not index:
                return
            dependents = list(index.get(metric_name))
            if not dependents:
                return
            for kind, qname in dependents:
                if kind != 'query':
                    continue
                q = self.queries.get(qname)
                if not q:
                    continue
                metric_type = 'computed' if is_derived_metric else 'base'
                self.log().info(
                    "Query '%s' auto-refreshed due to newly defined %s metric '%s'.",
                    qname, metric_type, metric_name
                )
                self.define_query(
                    name=qname,
                    dimensions=q.get("dimensions", []),
                    metrics=q.get("metrics", []),
                    derived_metrics=q.get("derived_metrics", []),
                    having=q.get("having"),
                    sort=q.get("sort", []),
                    drop_null_dimensions=q.get("drop_null_dimensions", False),
                    drop_null_metric_results=q.get("drop_null_metric_results", False),
                )
        except Exception as e:
            if len(getattr(self, 'queries', {})) > 0:
                self.log().warning("Failed to auto-refresh dependents for '%s': %s", metric_name, e)

    def get_dimensions(self) -> List[str]:
        dimensions = set()
        for table_name, table in self.tables.items():
            dimensions.update(
                col for col in table.columns 
                if not (
                    col.startswith('_index_') or 
                    col.startswith('_key_') or 
                    col.startswith('_composite_key_') or
                    #re.search(r'<_composite_', col)
                    re.search(r'<.*>', col)
                )
            )
        return sorted(list(dimensions))

    def get_queries(self) -> Dict[str, Any]:
        queries_formatted: Dict[str, Any] = {}
        for name, q in self.queries.items():
            queries_formatted[name] = {
                "dimensions": q.get('dimensions', []),
                "metrics": q.get('metrics', []),
                "derived_metrics": q.get('derived_metrics', []),
                "having": q.get('having'),
                "sort": q.get('sort'),                
                "drop_null_dimensions": q.get('drop_null_dimensions', False),
                "drop_null_metric_results": q.get('drop_null_metric_results', False),
            }
        return queries_formatted
    
    def get_metrics(self) -> Dict[str, Any]:
        metrics_formatted = {}
        for metric_name, metric in self.metrics.items():
            metrics_formatted[metric_name] = metric.get_metric_details()
        return metrics_formatted 

    def get_derived_metrics(self) -> Dict[str, Any]:
        derived_metrics_formatted = {}
        for metric_name, metric in self.derived_metrics.items():
            derived_metrics_formatted[metric_name] = metric.get_derived_metric_details()
        return derived_metrics_formatted
    
    def get_metric(self, metric:str) -> Dict[str, Any]:
        return self.metrics[metric].get_metric_details()
    
    def get_derived_metric(self, derived_metric:str) -> Dict[str, Any]:
        return self.derived_metrics[derived_metric].get_derived_metric_details()

    def get_query(self, query:str) -> Dict[str, Any]:
        query = self.queries[query]
        query_formatted = {
            "dimensions": query.get('dimensions', []),
            "metrics": query.get('metrics', []),
            "drop_null_dimensions": query.get('drop_null_dimensions', False),
            "drop_null_metric_results": query.get('drop_null_metric_results', False),
            "derived_metrics": query.get('derived_metrics', []),
            "having": query.get('having'),
            "sort": query.get('sort'),
        }
        return query_formatted

    # --- Deletion hooks and debug helpers ---
    def delete_query(self, name: str) -> None:
        """Remove a query definition and its dependency edges."""
        if name in self.queries:
            self.queries.pop(name, None)
    # No legacy reverse index to clean
        # Clean dependency edges
        try:
            if hasattr(self, '_dep_index') and self._dep_index is not None:
                self._dep_index.remove_query(name)
        except Exception:
            pass
        # Remove plotting configs tied to this query, and their edges
        try:
            qstate = getattr(self, 'plotting_components', {}).pop(name, None)
            if qstate and 'plots' in qstate:
                for plot_name in list(qstate['plots'].keys()):
                    if hasattr(self, '_dep_index') and self._dep_index is not None:
                        self._dep_index.remove_plot(plot_name)
        except Exception:
            pass

    def delete_metric(self, name: str) -> None:
        """Remove a base metric; dependent queries will still reference the name and be marked missing until redefined."""
        self.metrics.pop(name, None)
        # No reverse-refresh on deletion; edges remain from name->query for future redefinition

    def delete_derived_metric(self, name: str) -> None:
        """Remove a derived metric; dependent queries will still reference the name and be marked missing until redefined."""
        self.derived_metrics.pop(name, None)
        # No reverse-refresh on deletion

    def debug_dependencies(self) -> Dict[str, Any]:
        """Return a full snapshot of dependency edges (all sources -> dependents)."""
        try:
            if hasattr(self, '_dep_index') and self._dep_index is not None:
                snap = self._dep_index.snapshot()
                # Convert tuples to lists for easier serialization if needed
                return {src: [list(dep) for dep in deps] for src, deps in snap.items()}
        except Exception:
            pass
        return {}

    def debug_missing_dependencies(self) -> Dict[str, Any]:
        """Return only unresolved dependency edges.

        A source is considered unresolved if it is NOT one of:
        - a defined base metric name
        - a defined derived metric name
        - a known dimension
        - a defined query name (queries act as sources for plot dependents)
        """
        try:
            if hasattr(self, '_dep_index') and self._dep_index is not None:
                snap = self._dep_index.snapshot()
                dims = set(self.get_dimensions()) if hasattr(self, 'tables') else set()
                queries = set(self.queries.keys()) if hasattr(self, 'queries') else set()
                filtered = {}
                for src, deps in snap.items():
                    if (
                        src not in self.metrics
                        and src not in self.derived_metrics
                        and src not in dims
                        and src not in queries
                    ):
                        filtered[src] = [list(dep) for dep in deps]
                return filtered
        except Exception:
            pass
        return {}