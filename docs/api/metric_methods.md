# Metric Methods

## Define Metric

```python
define_metric(
    name: Optional[str] = None,
    expression: Optional[str] = None,
    aggregation: Optional[Union[str, Callable[[Any], Any]]] = None,
    metric_filters: Optional[Dict[str, Any]] = None,
    row_condition_expression: Optional[str] = None,
    context_state_name: str = 'Default',
    fillna: Optional[any] = None
)
```

Defines a metric and stores it in the cube object for later use in queries.

**Parameters:**

- `name`: Label for the metric (used in query results)
- `expression`: Calculation formula using [column] references and @custom_functions
- `aggregation`: How to combine values - pandas aggregation string ('sum', 'mean', 'count') or custom callable
- `metric_filters`: Filters applied only when evaluating this specific metric
- `metric_filters`: Filters applied only when evaluating this specific metric
- `row_condition_expression`: Filter expression applied to rows before calculating the metric
- `context_state_name`: Which context state this metric operates in
- `fillna`: Value to use for replacing NaN results

**Example:**

```python
# Define a revenue metric
cube.define_metric(
    name='Revenue',
    expression='[qty] * [price]',
    aggregation='sum'
)

# Sum sales only from Australia
# Note: This differs from using metric_filters={'region': ['Australia']} in how the filtering is applied:
# - row_condition_expression: Fetches all the rows, then applies pandas .query() with backtick syntax
# - metric_filters: Applied at the context state level before metric calculation
# The row_condition_expression fetches all the rows for the column which can result in different aggregation values depending on your data relationships.
cube.define_metric(
    name='Australia Sales',
    expression='[sales_amount]',
    aggregation='sum',
    row_condition_expression='[region] == "Australia"'
)
```

**Syntax Rules**

- **Column References**: Columns in metric expressions **must** be enclosed in square brackets: `[qty]`, `[price]`, `[cost]`, etc.

- **Aggregation Methods**: The `aggregation` parameter accepts:

   - Pandas group by strings: `'sum'`, `'mean'`, `'count'`, `'min'`, `'max'`, etc.

   - Custom callable functions: `lambda x: x.quantile(0.95)` or any function that accepts a pandas Series

## Register Function

```python
register_function(**kwargs)
```

Register custom functions to use in metric expressions with @function_name syntax.

**Parameters:**

- `**kwargs`: Keyword arguments where each key is the name to use in expressions and each value is the function

**Example:**

```python
import numpy as np

# Define a custom function
def safe_division(numerator, denominator, default=0.0):
    """Safely divide two arrays, handling division by zero"""
    result = numerator / denominator
    return result.replace([np.inf, -np.inf], np.nan).fillna(default)

# Register the function with your hypercube
cube.register_function(safe_division=safe_division)

# Use in metric definition
cube.define_metric(
    name='Profit Margin %',
    expression='@safe_division([revenue] - [cost], [revenue]) * 100',
    aggregation='mean'
)
```
