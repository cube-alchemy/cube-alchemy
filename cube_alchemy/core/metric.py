import re
from typing import Optional, List, Callable, Union, Any, Dict

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
        fillna: Optional[any] = None, 
    ) -> None:
        self.name = name
        self.expression = expression
        self.row_condition_expression = row_condition_expression
        self.aggregation = aggregation
        self.columns = extract_columns(str(self.expression) + str(self.row_condition_expression))
        self.metric_filters = metric_filters
        self.context_state_name = context_state_name
        self.fillna = fillna
    
    def get_metric_details(self):
        #return a dictionary with metric details
        return {
            "expression": self.expression,
            "row_condition_expression": self.row_condition_expression,
            "aggregation": self.aggregation,
            "columns": self.columns,
            "metric_filters": self.metric_filters,
            "context_state_name": self.context_state_name,
            "fillna": self.fillna
        }

class MetricGroup: # group of metrics based on state and query filters
    def __init__(
            self, 
            metric_group_name: Optional[str], 
            metrics: List[Metric], 
            group_filters: Optional[Dict[str, Any]] = None, 
            context_state_name: str = 'Default'
    ) -> None:
        import copy
        self.metric_group_name = metric_group_name
        self.metrics = copy.deepcopy(metrics)  # Ensure we work with a copy of the metrics
        self.group_filters = group_filters
        self.context_state_name = context_state_name

        # Rename each metric to include the group name in parentheses
        if self.metric_group_name:
            for metric in self.metrics:
                if metric.name and not metric.context_state_name == 'Default':
                    metric.name = f"{metric.name} ({self.metric_group_name})"