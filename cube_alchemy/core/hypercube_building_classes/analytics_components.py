from typing import List, Dict, Any, Optional, Union, Callable, Tuple
from ..metric import Metric, ComputedMetric, extract_columns
import re
import warnings

class AnalyticsComponents:
    
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
        fillna: Optional[any] = None,
        nested: Optional[Dict[str, Any]] = None):

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

        # define metric column indexes. To be used on queries to traverse the tree (for the metrics we want to bring not the distinct values but all the rows involving its columns)

        metric_tables = set()
        metric_columns_indexes = set()                

        for column in new_metric.columns:
            table_name = self.column_to_table.get(column)
            if table_name:
                metric_tables.add(table_name)
            else:
                warnings.warn(f"Column {column} not found in any table.")

            
        metric_tables_dict = {table_name: self.tables[table_name] for table_name in metric_tables if table_name is not None}

        trajectory_tables = self._find_complete_trajectory(metric_tables_dict)
        
        for table_name in trajectory_tables:
            if table_name not in self.link_tables:
                metric_columns_indexes.add(f"_index_{table_name}")

        # add metric_columns_indexes to the new metric object 
        new_metric.columns_indexes = list(metric_columns_indexes)
        self.metrics[new_metric.name] = new_metric

        new_metric.query_relevant_columns = list(set(new_metric.nested_dimensions + new_metric.columns + new_metric.columns_indexes))

        # Auto-refresh only queries that declared this name as missing
        self._refresh_queries_declaring_missing_metrics(name, is_computed_metric=False)
    
    def define_computed_metric(self, name: str, expression: str, fillna: Optional[Any] = None) -> None:
        """Persist a post-aggregation computed metric as a ComputedMetric instance.

        These metrics are evaluated after base metrics aggregation in queries.
        Use [Column] syntax to reference aggregated columns or dimensions.
        """
        if not isinstance(name, str) or not name:
            raise ValueError("Computed metric requires a non-empty string name.")
        if not isinstance(expression, str) or not expression:
            raise ValueError("Computed metric requires a non-empty string expression.")

        self.computed_metrics[name] = ComputedMetric(name=name, expression=expression, fillna=fillna)

        # Auto-refresh only queries that declared this name as missing
        self._refresh_queries_declaring_missing_metrics(name, is_computed_metric=True)

    def _refresh_queries_declaring_missing_metrics(self, name: str, is_computed_metric: bool) -> None:
        # Auto-refresh only queries that declared this name as missing
        try:
            index = getattr(self, "_queries_missing_by_name", None)
            if index is not None and name in index and index[name]:
                affected = list(index.pop(name))
                for qname in affected:
                    q = self.queries.get(qname)
                    if not q:
                        continue
                    metric_type = 'computed' if is_computed_metric else 'base'
                    print(f"Query '{qname}' auto-refreshed due to newly defined {metric_type} metric '{name}'.")
                    self.define_query(
                        name=qname,
                        dimensions=q.get("dimensions", []),
                        metrics=q.get("metrics", []),
                        computed_metrics=q.get("computed_metrics", []),
                        having=q.get("having"),
                        sort=q.get("sort", []),
                        drop_null_dimensions=q.get("drop_null_dimensions", False),
                        drop_null_metric_results=q.get("drop_null_metric_results", False),
                    )
        except Exception as e:
            if len(self.queries)>0:
                print(f"Warning: failed to auto-refresh queries for metric '{name}': {e}")

    def define_query(
        self,
        name: str,
        dimensions: set[str] = {},
        metrics: List[str] = [],
        computed_metrics: List[str] = [],
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
                print(f"Metric '{metric_name}' is not defined. Define it with define_metric().")

        for computed_metrics_name in computed_metrics:
            if computed_metrics_name not in self.computed_metrics:
                print(f"Computed metric '{computed_metrics_name}' is not defined. Define it with define_computed_metric().")
        
        having_columns: List[str] = extract_columns(having) if having else []

        # --- Precompute hidden (internal) base metrics required ---
        hidden_metrics: List[str] = []
        # From computed metrics' expressions
        for cm_name in computed_metrics:
            if cm_name in self.computed_metrics:
                for col in self.computed_metrics[cm_name].columns:
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

        # --- Precompute hidden computed metrics and dependency order ---
        # Any computed metric referenced by requested computed metrics, HAVING, or SORT
        hidden_computed_metrics: List[str] = []
        referenced_computed: set[str] = set()
        for cm_name in computed_metrics:
            if cm_name in self.computed_metrics:
                for col in self.computed_metrics[cm_name].columns:
                    if col in self.computed_metrics and col not in computed_metrics and col not in hidden_computed_metrics:
                        hidden_computed_metrics.append(col)
                        referenced_computed.add(col)
        for col in having_columns:
            if col in self.computed_metrics and col not in computed_metrics and col not in hidden_computed_metrics:
                hidden_computed_metrics.append(col)
                referenced_computed.add(col)
        for sort_col, _dir in sort:
            if sort_col in self.computed_metrics and sort_col not in computed_metrics and sort_col not in hidden_computed_metrics:
                hidden_computed_metrics.append(sort_col)
                referenced_computed.add(sort_col)

        # Build dependency graph for all computed metrics involved in this query (we need to execute them in order to work)
        def build_cm_dependencies(names: List[str]) -> Dict[str, List[str]]:
            deps: Dict[str, List[str]] = {}
            for n in names:
                if n not in self.computed_metrics:
                    continue
                cm = self.computed_metrics[n]
                # dependencies are other computed metric names referenced in expression
                deps[n] = [c for c in cm.columns if c in self.computed_metrics]
            return deps

        # the set of computed metrics that might need evaluation
        all_cm_names: List[str] = []
        for n in computed_metrics + hidden_computed_metrics:
            if n not in all_cm_names:
                all_cm_names.append(n)
        cm_deps = build_cm_dependencies(all_cm_names)

        # Topologically sort computed metrics to a safe evaluation order
        computed_metrics_ordered: List[str] = []
        temp_mark: set[str] = set()
        perm_mark: set[str] = set()

        def visit(node: str):
            if node in perm_mark:
                return
            if node in temp_mark:
                raise ValueError(f"Cycle detected in computed metrics dependencies involving '{node}'.")
            temp_mark.add(node)
            for d in cm_deps.get(node, []):
                visit(d)
            temp_mark.remove(node)
            perm_mark.add(node)
            if node not in computed_metrics_ordered:
                computed_metrics_ordered.append(node)

        for node in all_cm_names:
            visit(node)

        # Build the set of referenced names to track missing items for fast auto-refresh.
        # Only consider tokens that are NOT dimensions and are plausible metric/computed metric names.
        all_used_columns = set(metrics) | set(computed_metrics)
        # From computed metrics expressions (only those that exist at the moment)
        for cm_name in computed_metrics:
            cm_obj = self.computed_metrics.get(cm_name)
            if cm_obj:
                for col in cm_obj.columns:
                    all_used_columns.add(col)
        # From HAVING and SORT
        for col in having_columns:
            all_used_columns.add(col)
        for sc, _ in sort:
            all_used_columns.add(sc)

        # Names that are not yet defined as metrics/computed metrics
        missing_column_names = sorted([n for n in all_used_columns if n not in self.metrics and n not in self.computed_metrics and n not in self.get_dimensions()])

        # Maintain a reverse index: name -> set(query_names) for O(1) refresh on new definitions
        if not hasattr(self, "_queries_missing_by_name"):
            self._queries_missing_by_name = {}
        # If redefining, remove previous memberships for this query to avoid stale links
        prev_q = self.queries.get(name)
        if prev_q is not None:
            for n in prev_q.get("missing_column_names", []):
                s = self._queries_missing_by_name.get(n)
                if s is not None:
                    s.discard(name)
                    if not s:
                        self._queries_missing_by_name.pop(n, None)
        # Add current memberships
        for n in missing_column_names:
            self._queries_missing_by_name.setdefault(n, set()).add(name)

        self.queries[name] = {
            "dimensions": dimensions,
            "metrics": metrics,
            "computed_metrics": computed_metrics,
            "having": having,
            "having_columns": having_columns,
            "sort": sort,

            # Precomputed internal helpers to avoid recomputation at runtime
            "hidden_metrics": hidden_metrics,
            "hidden_computed_metrics": hidden_computed_metrics,

            # Full ordered list to evaluate (requested + hidden, in dependency order)
            "computed_metrics_ordered": computed_metrics_ordered,

            "drop_null_dimensions": drop_null_dimensions,
            "drop_null_metric_results": drop_null_metric_results,
            # Tracking for fast re-definition when missing items get defined later
            "missing_column_names": missing_column_names,
        }

        # if there exists a plot configured with this query, we might need to update it
        q_state = getattr(self, 'plotting_components', {}).get(name)
        if q_state and q_state.get('plots'):
            print(f"Plots configuration for query '{name}' will be updated due to query re-definition.")
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
                "computed_metrics": q.get('computed_metrics', []),
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

    def get_computed_metrics(self) -> Dict[str, Any]:
        computed_metrics_formatted = {}
        for metric_name, metric in self.computed_metrics.items():
            computed_metrics_formatted[metric_name] = metric.get_computed_metric_details()
        return computed_metrics_formatted
    
    def get_metric(self, metric:str) -> Dict[str, Any]:
        return self.metrics[metric].get_metric_details()
    
    def get_computed_metric(self, computed_metric:str) -> Dict[str, Any]:
        return self.computed_metrics[computed_metric].get_computed_metric_details()

    def get_query(self, query:str) -> Dict[str, Any]:
        query = self.queries[query]
        query_formatted = {
            "dimensions": query.get('dimensions', []),
            "metrics": query.get('metrics', []),
            "drop_null_dimensions": query.get('drop_null_dimensions', False),
            "drop_null_metric_results": query.get('drop_null_metric_results', False),
            "computed_metrics": query.get('computed_metrics', []),
            "having": query.get('having'),
            "sort": query.get('sort'),
        }
        return query_formatted