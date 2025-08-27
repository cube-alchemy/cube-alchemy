from typing import List, Dict, Any, Optional, Union, Callable, Tuple
from ..metric import Metric, ComputedMetric, extract_columns
import re

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
        fillna: Optional[any] = None, ):
        
        new_metric = Metric(name,expression, aggregation, metric_filters, row_condition_expression, context_state_name, ignore_dimensions, fillna)
        self.metrics[new_metric.name] = new_metric
    
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
        dimensions = list(dimensions) 

        # Validate metric names exist now, but store only names to keep linkage live
        for metric_name in metrics:
            if metric_name not in self.metrics:
                print(f"Metric '{metric_name}' is not defined. Define it with define_metric().")

        for computed_metrics_name in computed_metrics:
            if computed_metrics_name not in self.computed_metrics:
                print(f"Computed metric '{computed_metrics_name}' is not defined. Define it with define_computed_metric().")
        
        having_columns: List[str] = extract_columns(having) if having else []
        self.queries[name] = {
            "dimensions": dimensions,
            "metrics": metrics,
            "computed_metrics": computed_metrics,
            "having": having,
            "having_columns": having_columns,
            "sort": sort,
            "drop_null_dimensions": drop_null_dimensions,
            "drop_null_metric_results": drop_null_metric_results,
        }

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