import re
from typing import Optional, List, Callable, Union, Any, Dict
import copy
from .spec_validators import normalize_nested

def extract_columns(text: str = None) -> List[str]:
        # Extract the columns by looking for text between square brackets
        if text:
            return list(set(re.findall(r'\[(.*?)\]', text)))
        return []

class Metric:
    def __init__(
        self,
        name: Optional[str] = None,
        expression: Optional[str] = None,
        aggregation: Optional[Union[str, Callable[[Any], Any]]] = None,
        metric_filters: Optional[Dict[str, Any]] = None,
        row_condition_expression: Optional[str] = None,
        context_state_name: str = 'Default',
        ignore_dimensions: Union[bool, List[str]] = False,
        ignore_context_filters: Union[bool, List[str]] = False,
        fillna: Optional[any] = None,
        nested: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.expression = expression
        self.row_condition_expression = row_condition_expression
        self.aggregation = aggregation
        self.columns = extract_columns(str(self.expression) + str(self.row_condition_expression))
        self.metric_filters = metric_filters
        self.context_state_name = context_state_name
        self.ignore_dimensions = ignore_dimensions
        self.ignore_context_filters = ignore_context_filters
        self.fillna = fillna
        # Normalize/validate nested spec with a reusable helper
        self.nested = normalize_nested(nested, aggregation)

        # define nested dimensions if any, on queries we will need to bring those dimensions too
        self.nested_dimensions = []
        if self.nested:
            dim_nested = self.nested.get('dimensions')
            if dim_nested:
                if isinstance(dim_nested, str):
                    self.nested_dimensions = [dim_nested]
                else:
                    self.nested_dimensions = list(dim_nested)

        # Required for query processing. As indexes depend on hypercube inner traversal, they will be set on metric definition in hypercube. It comes handy to store this on the metric as they will be used repeatedly during query execution.
        self.columns_indexes = []
        self.query_relevant_columns = []  # (expression columns + nested dimensions + columns indexes)

    def get_metric_details(self):
        import inspect
        #return a dictionary with metric details
        aggregation_display = self.aggregation
        if callable(self.aggregation):
            try:
                # Get source for lambdas, or name for regular functions
                source = inspect.getsource(self.aggregation).strip()
                aggregation_display = source if source.startswith('lambda') else self.aggregation.__name__
            except (TypeError, OSError):
                # Fallback to name for built-in functions or if source is not available
                aggregation_display = self.aggregation.__name__

        return {
            "expression": self.expression,
            "row_condition_expression": self.row_condition_expression,
            "aggregation": aggregation_display,
            #"columns": self.columns,
            "metric_filters": self.metric_filters,
            "context_state_name": self.context_state_name,
            "ignore_dimensions": self.ignore_dimensions,
            "ignore_context_filters": self.ignore_context_filters,
            "fillna": self.fillna,
            "nested": self.nested,
        }

class MetricGroup: # group of metrics based on state and query filters
    def __init__(
            self, 
            metric_group_name: Optional[str], 
            metrics: List[Metric], 
            group_filters: Optional[Dict[str, Any]] = None, 
            context_state_name: str = 'Default'
    ) -> None:
        self.metric_group_name = metric_group_name
        self.metrics = copy.deepcopy(metrics)  # Ensure we work with a copy of the metrics
        self.group_filters = group_filters
        self.context_state_name = context_state_name


class DerivedMetric:
    """Represents a post-aggregation derived metric.

    These are evaluated after base metrics are aggregated. They can reference
    any column present in the aggregated result using [Column] syntax.
    """
    def __init__(
        self,
        name: str,
        expression: str,
        fillna: Optional[Any] = None,
    ) -> None:
        self.name = name
        self.expression = expression
        self.fillna = fillna
        self.columns = extract_columns(expression)

    def get_derived_metric_details(self) -> Dict[str, Any]:
        return {
            "expression": self.expression,
            "fillna": self.fillna,
        #    "columns": self.columns,
        }