import logging
import re
import pandas as pd
from ..metric import Metric, MetricGroup
from typing import Dict, List, Any, Optional, Tuple
import copy
import uuid

def add_quotes_to_brackets(expression: str) -> str:
                    return re.sub(r'\[(.*?)\]', r"['\1']", expression)

def brackets_to_backticks(expression: str) -> str:
    """Convert column references in square brackets to pandas query backtick syntax.

    Example: "[country] == 'US' & [age] >= 18" -> "`country` == 'US' & `age` >= 18"
    """
    return re.sub(r'\[(.*?)\]', lambda m: f"`{m.group(1)}`", expression)

class Query:
    def dimension(self, dimension:str,
        context_state_name: str = 'Default',
        query_filters: Optional[Dict[str, Any]] = None) -> List[str]:
        df = self.dimensions([dimension], context_state_name=context_state_name, query_filters=query_filters)
        return df[dimension]

    def dimensions(
        self,
        columns_to_fetch: List[str],
        retrieve_keys: bool = False,
        context_state_name: str = 'Default',
        query_filters: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        if query_filters is None:
            query_filters = {}
        df = self.context_states[context_state_name].copy()
        df = self._fetch_and_merge_columns(columns_to_fetch, df)

        df = self._apply_filters_to_dataframe(df, query_filters)
        
        if retrieve_keys:
            return df.drop_duplicates()
        else:
            return df[columns_to_fetch].drop_duplicates()
    
    def register_function(self, **kwargs):
        """Register variables/functions available to DataFrame.query via @name."""
        self.registered_functions.update(kwargs)

    def query(
        self, 
        query_name: Optional[str] = None,
        # on the fly queries
        options: Optional[Dict[str, Any]] = None,
        _retrieve_query_name: Optional[str] = False # Internal use, to plot ad hoc queries
    ):

        if options is None:
            query = self.queries.get(query_name)
            if not query:
                raise ValueError(f"Query '{query_name}' not found.")
            new_query_name = None
        # Define an ad-hoc query with the provided parameters
        else:
            base = self.queries.get(query_name) or {}

            uuid_str = str(uuid.uuid4())[:8]
            new_query_name = f"**ad-hoc** ({uuid_str})" if not query_name else f"**ad-hoc** ({query_name}) ({uuid_str})"

            def pick(key: str, default):
                if key in options:
                    val = options.get(key)
                    if val is None:
                        return base.get(key, default)
                    return val
                return base.get(key, default)

            dims = pick("dimensions", [])
            mets = pick("metrics", [])
            cmets = pick("computed_metrics", [])
            having = pick("having", None)
            sort = pick("sort", [])
            drop_null_dimensions = pick("drop_null_dimensions", False)
            drop_null_metric_results = pick("drop_null_metric_results", False)

            # Always re-run define_query to recompute hidden/ordered deps
            self.define_query(
                name=new_query_name,
                dimensions=dims,
                metrics=mets,
                computed_metrics=cmets,
                having=having,
                sort=sort,
                drop_null_dimensions=drop_null_dimensions,
                drop_null_metric_results=drop_null_metric_results
            )
            query = self.queries.get(new_query_name)
            self.log().info("New query defined: %s", new_query_name)

        # Build full set of metrics to compute using precomputed hidden metrics
        all_metrics = query["metrics"] + query["hidden_metrics"]
        metric_objects: List[Metric] = []
        for name in all_metrics:
            try:
                metric_objects.append(self.metrics[name])
            except KeyError:
                raise ValueError(f"Metric '{name}' is not defined. Define it with define_metric().")
        # Execute the query up until aggregation
        query_result = self._multiple_state_and_filter_query(
            dimensions = query["dimensions"],
            metrics = metric_objects,
            drop_null_dimensions = query["drop_null_dimensions"],
            drop_null_metric_results = query["drop_null_metric_results"]
        )
        # Apply post-aggregation ops: evaluate computed metrics in stored order
        query_result = self._apply_computed_metrics_and_having(
            query_result,
            query["computed_metrics_ordered"],
            query["having"]
        )

        # Sort if requested (list of tuples: [(column, 'asc'|'desc'), ...])
        if query["sort"]:
            # Only sort by columns that exist in the result to avoid errors in ad-hoc/no-dimension cases
            by_dirs = [(c, d) for c, d in query["sort"] if c in query_result.columns]
            if by_dirs:
                by = [c for c, _ in by_dirs]
                ascending = [str(d).lower() == 'asc' for _, d in by_dirs]
                query_result = query_result.sort_values(by=by, ascending=ascending)
        
        final_result = query_result[query["dimensions"] + query["metrics"] + query["computed_metrics"]]

        if _retrieve_query_name:
            return new_query_name or query_name, final_result
        return final_result

        # I use this method to avoid calling and processing the indexes multiple times when there are multiple metrics with the same context_states and filters, which I assume is the most common case.
    
    def _single_state_and_filter_query(
        self,
        dimensions: List[str] = [],
        metrics: Optional[List[Metric]] = [],
        query_filters: Optional[Dict[str, Any]] = {},
        context_state_name: str = 'Default' ,
        drop_null_dimensions: bool = False,
        drop_null_metric_results: bool = False
    ) -> pd.DataFrame:
        metrics_list_len = len(metrics)

        # Preserve original dimensions and establish merge/group keys
        original_dimensions = list(dimensions)
        no_dimension = len(original_dimensions) == 0
        fake_dim_to_group_by = '<all>'
        dimensions = [fake_dim_to_group_by] if no_dimension else original_dimensions

        if metrics_list_len == 0:
            df = self.dimensions(original_dimensions, False, context_state_name, query_filters)
            return df
        else:
            results = []
            count = 0
            for metric in metrics:
                df = self.context_states[context_state_name].copy()  # copy state DataFrame to avoid modifying original
                df = self._apply_filters_to_dataframe(df, query_filters)

                # Compute per-metric effective dimensions once (used for nested and outer aggregation)
                if metric.ignore_dimensions is False:
                    metric_effective_dims = list(original_dimensions)
                    base_dimensions_changed = False
                elif metric.ignore_dimensions is True:
                    metric_effective_dims: List[str] = []
                    base_dimensions_changed = True
                elif isinstance(metric.ignore_dimensions, list):
                    ignore_set = set(metric.ignore_dimensions)
                    metric_effective_dims = [d for d in original_dimensions if d not in ignore_set]
                    if tuple(metric_effective_dims) != tuple(original_dimensions):
                        base_dimensions_changed = True
                else:
                    raise ValueError(f"Invalid value for ignore_dimensions: {metric.ignore_dimensions}")

                # Fetch only what this metric needs: effective dims + metric-relevant columns
                all_relevant_columns = list(set(metric_effective_dims + metric.query_relevant_columns))
                metric_result = self._fetch_and_merge_columns(all_relevant_columns, df)[all_relevant_columns].drop_duplicates(subset=all_relevant_columns, ignore_index=True)

                if no_dimension:  # fake dimension to group by, will be deleted later
                    metric_result[fake_dim_to_group_by] = True

                # Store masks for NaN values before filling
                filled_masks = {}
                if metric.fillna is not None:
                    for col in metric.columns:
                        filled_masks[col] = metric_result[col].isna()
                        metric_result.loc[filled_masks[col], col] = metric.fillna

                try:
                    # Row-condition filter
                    if metric.row_condition_expression:
                        row_condition_expr = brackets_to_backticks(metric.row_condition_expression)
                        metric_result = metric_result.query(row_condition_expr, engine='python', local_dict=self.registered_functions)

                    # Evaluate the metric expression
                    expr = add_quotes_to_brackets(metric.expression.replace('[', 'metric_result['))
                    expr = re.sub(r'@([A-Za-z_]\w*)', r'\1', expr)
                    eval_locals = {'metric_result': metric_result}
                    eval_globals = self.registered_functions
                    metric_result[metric.name] = eval(expr, eval_globals, eval_locals)

                except Exception as e:
                    self.log().error("Error evaluating metric expression: %s", e)
                    return None


                # Restore original NaN values
                if metric.fillna is not None:
                    for col, mask in filled_masks.items():
                        metric_result.loc[mask, col] = pd.NA

                # Nested: inner step uses metric_effective_dims + nested.dimensions
                if metric.nested:
                    metric_result = self._apply_nested(
                        metric_result=metric_result,
                        metric_name=metric.name,
                        outer_dimensions=metric_effective_dims,
                        nested_spec=metric.nested,
                        drop_null_dimensions=drop_null_dimensions,
                    )

                # Unified outer aggregation (same path for nested/non-nested)
                agg_fn = self._resolve_aggregation(metric.aggregation)
                if metric_effective_dims:
                    agg_result = (
                        metric_result
                        .groupby(metric_effective_dims, dropna=drop_null_dimensions)[metric.name]
                        .agg(agg_fn)
                        .reset_index()
                    )
                    # Broadcast only if some query dimensions were ignored
                    if base_dimensions_changed:
                        # Efficiently get all requested query-dimension combinations (filtered)
                        if no_dimension:
                            outer_combos = pd.DataFrame({fake_dim_to_group_by: [True]})
                        else:
                            outer_combos = self.dimensions(original_dimensions, False, context_state_name, query_filters)
                        metric_result = pd.merge(outer_combos, agg_result, on=metric_effective_dims, how='left')
                    else:
                        metric_result = agg_result
                else:
                    # Grand total: compute scalar and fill across all requested combos
                    total_agg_val = metric_result[metric.name].agg(agg_fn)
                    if no_dimension:
                        outer_combos = pd.DataFrame({fake_dim_to_group_by: [True]})
                    else:
                        outer_combos = self.dimensions(original_dimensions, False, context_state_name, query_filters)
                    metric_result = outer_combos
                    metric_result[metric.name] = total_agg_val

                if drop_null_metric_results:
                    metric_result = metric_result.dropna(subset=[metric.name])

                results.append(metric_result)
            final_result = results[0]
            for result in results[1:]:
                final_result = pd.merge(final_result, result, on=dimensions, how='outer')
            if no_dimension:
                final_result.drop(fake_dim_to_group_by, axis=1, inplace=True)

            return final_result

    def _deduplicate_state_filter_pairs(self, context_states_and_filter_pairs: List[tuple]) -> List[tuple]:
        """
        Remove duplicate state-filter pairs by converting filters to hashable representations.
            
        Returns:
            List of unique (context_state_name, filters) tuples
        """
        unique_pairs = []
        seen = set()
        
        for context_state_name, filters in context_states_and_filter_pairs:
            # Convert dict to frozenset of items for hashing
            if filters:
                # Convert lists/unhashable values to tuples for hashing
                hashable_items = []
                for key, value in filters.items():
                    if isinstance(value, list):
                        hashable_items.append((key, tuple(value)))
                    elif isinstance(value, dict):
                        # Handle nested dicts by converting to sorted tuples
                        hashable_items.append((key, tuple(sorted(value.items()))))
                    else:
                        hashable_items.append((key, value))
                filters_key = frozenset(hashable_items)
            else:
                filters_key = frozenset()
                
            pair_key = (context_state_name, filters_key)
            if pair_key not in seen:
                seen.add(pair_key)
                unique_pairs.append((context_state_name, filters))
                
        return unique_pairs

    def _multiple_state_and_filter_query(
        self,
        dimensions: List[str] = [],
        metrics: List[Metric] = [],
        drop_null_dimensions: bool = False,
        drop_null_metric_results: bool = False
    ) -> pd.DataFrame:
        if len(dimensions) == 0 and len(metrics) == 0:
            # If no dimensions and no metrics are provided, return an empty DataFrame
            return pd.DataFrame(columns=dimensions)
        # if no metrics are provided, return the dimensions (uses Default state and no filters, if want to use state and/or filters, use _single_state_and_filter_query or dimensions method instead)
        if len(metrics) == 0:
            return self._single_state_and_filter_query(dimensions, drop_null_dimensions = drop_null_dimensions, drop_null_metric_results = drop_null_metric_results)
        # Mutate metrics filters if required
        self._apply_metrics_ignore_filters(metrics)
        if len(metrics) == 1:
            # If there is only one metric, we can use _single_state_and_filter_query directly
            metric = metrics[0]
            return self._single_state_and_filter_query(dimensions, [metric], metric.metric_filters, metric.context_state_name, drop_null_dimensions = drop_null_dimensions, drop_null_metric_results = drop_null_metric_results)
        else:
            # If there are multiple metrics, we group them by state and metric filters
            context_states_and_filter_pairs = []
            for metric in metrics:
                context_states_and_filter_pairs.append((metric.context_state_name, metric.metric_filters))
            
            # Remove duplicates using helper method
            context_states_and_filter_pairs = self._deduplicate_state_filter_pairs(context_states_and_filter_pairs)
            
            if len(context_states_and_filter_pairs) == 1:
                # If there is only one state and metric filter pair, we can use _single_state_and_filter_query directly
                context_state_name, filters = context_states_and_filter_pairs[0]
                return self._single_state_and_filter_query(dimensions, metrics, filters, context_state_name, drop_null_dimensions = drop_null_dimensions, drop_null_metric_results = drop_null_metric_results)
            else:
                # Group metrics by context_states_and_filter_pairs
                grouped_metrics = []
                for context_state_name, group_filters in context_states_and_filter_pairs:
                    # Create a MetricGroup for each unique state and metric filter pair
                    grouped_metrics.append(
                        MetricGroup(
                            metric_group_name=f"{context_state_name}", # same state is used as group name, but they can have different fitlers
                            metrics=[m for m in metrics if m.context_state_name == context_state_name and m.metric_filters == group_filters],
                            group_filters=group_filters,
                            context_state_name=context_state_name
                        )
                    )

                results = []
                for group in grouped_metrics:
                    df = self._single_state_and_filter_query(dimensions, group.metrics, group.group_filters, group.context_state_name, drop_null_dimensions = drop_null_dimensions, drop_null_metric_results = drop_null_metric_results)
                    results.append(df)
                # join all results
                final_result = results[0]
                for result in results[1:]:
                    final_result = pd.merge(final_result, result, on=dimensions, how='outer')
        return final_result

    def _apply_nested(
        self,
        metric_result: pd.DataFrame,
        metric_name: str,
        outer_dimensions: List[str],
        nested_spec: Dict[str, Any],
        drop_null_dimensions: bool,
    ) -> pd.DataFrame:
        """
        Inner aggregate and optional compose step to support concat over inner rows.
        nested_spec keys:
        - dimensions: List[str] of inner grouping dimensions
        - aggregation: inner aggregation function/name (default 'sum')
        - compose (optional): str template or callable(row)->str to transform each inner aggregated row
        """
        # Normalize inner dimensions list
        by_val = nested_spec.get('dimensions') if isinstance(nested_spec, dict) else None
        if isinstance(by_val, str):
            inner_by: List[str] = [by_val]
        else:
            inner_by = list(by_val or [])

        inner_agg = self._resolve_aggregation(nested_spec.get('aggregation', 'sum')) if isinstance(nested_spec, dict) else 'sum'

        # Inner aggregation by outer dims + inner_by
        gb_inner = list(dict.fromkeys([*outer_dimensions, *inner_by]))
        inner_df = (
            metric_result
            .groupby(gb_inner, dropna=drop_null_dimensions)[metric_name]
            .agg(inner_agg)
            .reset_index()
        )

        # Optional compose formatting: convert the aggregated value into a labeled string per inner row
        compose = nested_spec.get('compose') if isinstance(nested_spec, dict) else None
        if compose is not None:
            if isinstance(compose, str):
                # Build a context with group-by keys and {value}
                def _fmt_row(r):
                    ctx = {k: r[k] for k in gb_inner if k in r}
                    ctx['value'] = r[metric_name]
                    return compose.format(**ctx)
                inner_df[metric_name] = inner_df.apply(_fmt_row, axis=1)
            elif callable(compose):
                inner_df[metric_name] = inner_df.apply(compose, axis=1)
            else:
                raise TypeError("nested.compose must be a str template or a callable(row)->str.")

        return inner_df

    def _apply_computed_metrics_and_having(
        self,
        df: pd.DataFrame,
        computed_metrics: Optional[List[str]] = None,
        having: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Post-aggregation stage with dependency resolution:
        - computed_metrics: list of names referencing persisted computed metrics
        - having: string expression to filter aggregated rows, also using [Column] syntax.
        """
        if df is None or df.empty:
            return df

        if not computed_metrics:
            computed_metrics = []
        
        # Now evaluate metrics in the correct order
        for name in computed_metrics:
            cm = self.computed_metrics[name]
            expression = cm.expression
            fillna_value = cm.fillna

            # If fill na, temporarily fill the dataframe column na values
            filled_masks = {}
            if fillna_value is not None:
                for col in cm.columns:
                    filled_masks[col] = df[col].isna()
                    df.loc[filled_masks[col], col] = fillna_value

            try:
                # Turn [col] into df['col'] for Python eval
                expr = add_quotes_to_brackets(expression.replace('[', 'df['))
                # Allow using @fn for registered functions
                expr = re.sub(r'@([A-Za-z_]\w*)', r'\1', expr)

                eval_locals = {"df": df}
                eval_globals = self.registered_functions
                df[name] = eval(expr, eval_globals, eval_locals)

            except Exception as e:
                raise ValueError(f"Error evaluating computed metric '{name}': {e}") from e
            
            # Restore original NaN values
            if fillna_value is not None:
                for col in cm.columns:
                    # Use the same masks to restore values
                    df.loc[filled_masks[col], col] = pd.NA

        # Apply HAVING-like filter
        if having:
            try:
                # Convert [col] -> `col` for DataFrame.query backtick syntax
                having_expr = brackets_to_backticks(having)
                df = df.query(having_expr, engine='python', local_dict=self.registered_functions)
            except Exception as e:
                raise ValueError(f"Error applying HAVING expression '{having}': {e}") from e

        return df

    def _apply_metrics_ignore_filters(self, metrics: List[Metric]):
        """
        Metrics can ignore specific context filters.
        We temporarily create a new metric object with the same properties as the original and change its context and filters to match the desired state.
        """
        for i, metric in enumerate(metrics):
            if not metric.ignore_context_filters:
                continue
            new_metric = copy.deepcopy(metric)
            # check if ignore filters is bool
            if isinstance(metric.ignore_context_filters, bool) and metric.ignore_context_filters:
                new_metric.context_state_name = 'Unfiltered'
                # metric specific filters will apply to only the Unfiltered context
            else:  # metric.ignore_context_filters is a list, ignore the specific filters of its context's filters
                new_filters = self.get_filters(context_state_name=new_metric.context_state_name) or {}
                for ignored_filter in new_metric.ignore_context_filters:
                    new_filters.pop(ignored_filter, None)
                # If the metric has metric-specific filters we will use them on top of the reduced context filters
                if metric.metric_filters:
                    new_filters.update(metric.metric_filters)
                # Now reset the metric filters by using the Unfiltered context and applying the new filters composed
                # by reduced context filters plus the metric filters
                new_metric.context_state_name = 'Unfiltered'
                new_metric.metric_filters = new_filters

            # now from metrics, replace the original metric with the new metric. 
            # This leaves the original metric intact and the new metric (updated on the fly depending on context) will be used instead for the query.
            metrics[i] = new_metric
    
    def _resolve_aggregation(self, agg: Any) -> Any:
        """Normalize aggregation spec into something pandas .agg(...) accepts.
        Supports:
        - pandas-native strings (sum, mean, nunique, ...)
        - friendly aliases (count_distinct -> nunique, avg -> mean)
        - names or dotted paths resolvable via self.registered_functions (e.g., 'np.nanmean')
        - callables (returned as-is)
        - list/tuple/dict containers resolved recursively
        """
        if agg is None:
            return agg
        if callable(agg):
            return agg
        # Alias map
        aliases: Dict[str, Any] = {
            # pandas-native (pass-through)
            "sum": "sum",
            "mean": "mean",
            "min": "min",
            "max": "max",
            "median": "median",
            "std": "std",
            "var": "var",
            "count": "count",
            "size": "size",
            "first": "first",
            "last": "last",
            "prod": "prod",
            "any": "any",
            "all": "all",
            "nunique": "nunique",
            # friendly aliases
            "avg": "mean",
            "count_distinct": "nunique",
            "distinct_count": "nunique",
            "countdistinct": "nunique",
            # string helpers
            "concat": lambda s: ", ".join(map(str, s.dropna())),
        }
        def norm(s: str) -> str:
            return s.strip().replace(" ", "_").replace("-", "_").lower()
        if isinstance(agg, str):
            key = norm(agg)
            if key in aliases:
                return aliases[key]
            # Try registry lookup
            registry = getattr(self, "registered_functions", {}) or {}
            # exact match first
            cand = registry.get(agg) or registry.get(key)
            if callable(cand):
                return cand
            # dotted resolution like 'np.nanmean'
            if "." in agg and registry:
                head, *rest = agg.split(".")
                base = registry.get(head)
                if base is not None:
                    obj: Any = base
                    ok = True
                    for part in rest:
                        if hasattr(obj, part):
                            obj = getattr(obj, part)
                        else:
                            ok = False
                            break
                    if ok and callable(obj):
                        return obj
            # Fallback: let pandas attempt to resolve string
            return agg
        if isinstance(agg, (list, tuple)):
            return type(agg)(self._resolve_aggregation(a) for a in agg)
        if isinstance(agg, dict):
            return {k: self._resolve_aggregation(v) for k, v in agg.items()}
        return agg
