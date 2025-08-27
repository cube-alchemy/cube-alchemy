
import re
import pandas as pd
import numpy as np
from ..metric import Metric, MetricGroup, ComputedMetric
from typing import Dict, List, Any, Optional

def add_quotes_to_brackets(expression: str) -> str:
                    return re.sub(r'\[(.*?)\]', r"['\1']", expression)

def brackets_to_backticks(expression: str) -> str:
    """Convert column references in square brackets to pandas query backtick syntax.

    Example: "[country] == 'US' & [age] >= 18" -> "`country` == 'US' & `age` >= 18"
    """
    return re.sub(r'\[(.*?)\]', lambda m: f"`{m.group(1)}`", expression)

class QueryMethods:
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

    def query(self, query_name: str, return_internal_metrics: bool = False):
        query = self.queries.get(query_name)
        if not query:
            raise ValueError(f"Query '{query_name}' not found.")
        
        # Build full set of metrics to compute:
        # - Base metrics the query asks for
        # - Base metrics required by computed metrics' expressions
        # - Base metrics required by HAVING expression
        missing_metrics: List[str] = []
        # From computed metrics' columns
        for cm_name in query["computed_metrics"]:
            cm_obj = self.computed_metrics[cm_name]
            for col in getattr(cm_obj, 'columns', []) or []:
                if col in self.metrics and col not in query["metrics"] and col not in missing_metrics:
                    missing_metrics.append(col)
        # From HAVING's referenced columns (precomputed at define_query)
        for col in query["having_columns"]:
            if col in self.metrics and col not in query["metrics"] and col not in missing_metrics:
                missing_metrics.append(col)
        # From SORT's referenced columns (metrics that need to be computed for sorting)
        for sort_col, _dir in query["sort"]:
            if sort_col in self.metrics and sort_col not in query["metrics"] and sort_col not in missing_metrics:
                missing_metrics.append(sort_col)

        all_metrics = query["metrics"] + missing_metrics
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
        # Apply post-aggregation operations
        # We may also need to compute computed metrics referenced by HAVING/SORT even if not requested for output
        missing_computed_metrics: List[str] = []
        for col in query["having_columns"]:
            if col in self.computed_metrics and col not in query["computed_metrics"]:
                missing_computed_metrics.append(col)
        for sort_col, _dir in query["sort"]:
            if sort_col in self.computed_metrics and sort_col not in query["computed_metrics"] and sort_col not in missing_computed_metrics:
                missing_computed_metrics.append(sort_col)

        computed_for_eval = query["computed_metrics"] + missing_computed_metrics
        query_result = self._apply_computed_metrics_and_having(
            query_result,
            computed_for_eval,
            query["having"]
        )

        # Sort if requested (list of tuples: [(column, 'asc'|'desc'), ...])
        if query["sort"]:
            by = [c for c, _ in query["sort"]]
            ascending = [str(d).lower() == 'asc' for _, d in query["sort"]]
            query_result = query_result.sort_values(by=by, ascending=ascending)

        if return_internal_metrics:
            return query_result
        else:
            # Return only requested dimensions, metrics, and computed metrics
            return query_result[query["dimensions"] + query["metrics"] + query["computed_metrics"]]
        
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
        no_dimension = False
        metrics_list_len = len(metrics)
        if metrics_list_len == 0:
            df = self.dimensions(dimensions, False, context_state_name, query_filters)
            return df
        else:
            if len(dimensions) > 0:
                df = self.dimensions(dimensions, True, context_state_name, query_filters)          
            else:
                df = self.context_states[context_state_name].copy() # I copy the state DataFrame to avoid modifying the original state
                df = self._apply_filters_to_dataframe(df, query_filters)
                df['<all>'] = 1
                dimensions = ['<all>']
                no_dimension = True
            results = []          
            for metric in metrics:
                metric_tables = set()
                metric_keys = set()
                metric_columns_indexes = set()                

                for column in metric.columns:
                    table_name = self.column_to_table.get(column)
                    if table_name:
                        metric_tables.add(table_name)
                    else:
                        print(f"Warning: Column {column} not found in any table.")
                        continue
                    
                metric_tables_dict = {table_name: self.tables[table_name] for table_name in metric_tables if table_name is not None}

                trajectory_tables = self._find_complete_trajectory(metric_tables_dict)
                
                for table_name in trajectory_tables:
                    if table_name not in self.link_tables:
                        metric_columns_indexes.add(f"_index_{table_name}")
                    for col in self.tables[table_name].columns:
                        if col in self.link_table_keys:
                            metric_keys.add(col)

                keys_and_dimensions = list(metric_keys | {col for col in dimensions if col not in metric.columns}) # If a dimension is also a metric column (I want to bring all the rows not just distinct)
                if metrics_list_len == 1:
                    metric_result = df[keys_and_dimensions].drop_duplicates() 
                else: # copy as each metric has its own set of columns
                    metric_result = df.copy()[keys_and_dimensions].drop_duplicates()

                if len(metric_columns_indexes) > 1:
                    metric_result = self._fetch_and_merge_columns(list(set(metric.columns + list(metric_columns_indexes))), metric_result, drop_duplicates=True)
                else:
                    metric_result = self._fetch_and_merge_columns(metric.columns, metric_result)
              
                if metric.fillna is not None:
                    for col in metric.columns:
                        metric_result[col] = metric_result[col].fillna(metric.fillna)
                try:
                    # If metric has row condition filter down the data based on it
                    if metric.row_condition_expression:
                        row_condition_expr = brackets_to_backticks(metric.row_condition_expression)
                        metric_result = metric_result.query(row_condition_expr, engine='python', local_dict=self.registered_functions)
                    
                    expr = add_quotes_to_brackets(metric.expression.replace('[', 'metric_result['))
                    # Turn @name into name so Python eval can see it in globals
                    expr = re.sub(r'@([A-Za-z_]\w*)', r'\1', expr)
                    eval_locals = {'metric_result': metric_result}
                    eval_globals = self.registered_functions
                    metric_result[metric.name] = eval(expr, eval_globals, eval_locals)
                except Exception as e:
                    print(f"Error evaluating metric expression: {e}")
                    return None

                # Handle ignore_dimensions (ignore all or specific dimensions)
                if metric.ignore_dimensions:
                    if isinstance(metric.ignore_dimensions, list):
                        # Exclude specified dimensions (partial ignore)
                        group_dims = [d for d in dimensions if d not in metric.ignore_dimensions]
                        if group_dims:
                            # Group by remaining dimensions
                            agg_result = metric_result.groupby(group_dims, dropna=drop_null_dimensions)[metric.name].agg(metric.aggregation).reset_index()
                            # Get all dimension combinations to join back
                            all_dims = df[dimensions].drop_duplicates()
                            metric_result = pd.merge(all_dims, agg_result, on=group_dims, how='left')
                        else:
                            # If all dimensions are excluded, calculate grand total
                            total_agg_val = metric_result[metric.name].agg(metric.aggregation)
                            metric_result = df[dimensions].drop_duplicates()
                            metric_result[metric.name] = total_agg_val
                    else:
                        # Boolean True - ignore all dimensions (grand total)
                        total_agg_val = metric_result[metric.name].agg(metric.aggregation)
                        metric_result = df[dimensions].drop_duplicates()
                        metric_result[metric.name] = total_agg_val
                else:
                    # Normal aggregation with all dimensions
                    metric_result = metric_result.groupby(dimensions, dropna=drop_null_dimensions)[metric.name].agg(metric.aggregation).reset_index()
                
                if drop_null_metric_results:
                    metric_result = metric_result.dropna(subset=[metric.name])
                results.append(metric_result)
                
            final_result = results[0]
            for result in results[1:]:
                final_result = pd.merge(final_result, result, on=dimensions, how='outer')
            if no_dimension:
                final_result.drop('<all>', axis=1, inplace=True)

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
        elif len(metrics) == 1:
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

    def _apply_computed_metrics_and_having(
        self,
        df: pd.DataFrame,
        computed_metrics: Optional[List[str]] = None,
        having: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Post-aggregation stage:
        - computed_metrics: list of names referencing persisted computed metrics
        - having: string expression to filter aggregated rows, also using [Column] syntax.
        """
        if df is None or df.empty:
            return df

        # Evaluate computed metrics (resolve names to ComputedMetric instances)
        for name in (computed_metrics or []):
            if name not in self.computed_metrics:
                raise ValueError(
                    f"Computed metric '{name}' is not defined. Define it first with define_computed_metric()."
                )
            cm = self.computed_metrics[name]
            expression = cm.expression
            fillna_value = cm.fillna

            try:
                # Turn [col] into df['col'] for Python eval
                expr = add_quotes_to_brackets(expression.replace('[', 'df['))
                # Allow using @fn for registered functions
                expr = re.sub(r'@([A-Za-z_]\w*)', r'\1', expr)

                eval_locals = {"df": df}
                eval_globals = self.registered_functions
                df[name] = eval(expr, eval_globals, eval_locals)

                # Optional fillna for computed metric (allow 0 and False)
                if fillna_value is not None:
                    df[name] = df[name].fillna(fillna_value)
            except Exception as e:
                raise ValueError(f"Error evaluating computed metric '{name}': {e}") from e

        # Apply HAVING-like filter
        if having:
            try:
                # Convert [col] -> `col` for DataFrame.query backtick syntax
                having_expr = brackets_to_backticks(having)
                df = df.query(having_expr, engine='python', local_dict=self.registered_functions)
            except Exception as e:
                raise ValueError(f"Error applying HAVING expression '{having}': {e}") from e

        return df
