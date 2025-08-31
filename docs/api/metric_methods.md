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
    ignore_dimensions: Union[bool, List[str]] = False,
    ignore_context_filters: Union[bool, List[str]] = False,
    fillna: Optional[any] = None
)
```

Defines a metric and stores it in the cube object for later use in queries.

**Parameters:**

- `name`: Label for the metric (used in query results)
- `expression`: Calculation formula using [column] references and @custom_functions
- `aggregation`: How to combine values - pandas aggregation string ('sum', 'mean', 'count') or custom callable
- `metric_filters`: Filters applied only when evaluating this specific metric
- `row_condition_expression`: Filter expression applied to rows before calculating the metric
- `context_state_name`: Which context state this metric operates in
- `ignore_dimensions`: Control how dimensions affect aggregation - `True` to ignore all dimensions (grand total), a list of dimension names to ignore specific dimensions, or `False` (default) for normal dimensional aggregation
 - `ignore_context_filters`: Control how context filters affect this metric – `True` to ignore all context filters when evaluating the metric, a list of filter keys to ignore only those specific context filters, or `False` (default) to respect the context filters. When a list is provided, remaining context filters still apply, and any `metric_filters` are applied on top. Note: `ignore_context_filters=True` is effectively the same as evaluating the metric in the `Unfiltered` context (i.e., like setting `context_state_name='Unfiltered'` for this metric).
- `fillna`: Value to use for replacing Null values on the metric expression and row_condition_expression columns before aggregation. Note: This parameter applies the same value to all columns. For column-specific NA handling, use `@pd.fillna()` or `@np.nan_to_num()` functions directly in the expression.

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

# Define a metric that ignores all dimensions (calculates grand total)
cube.define_metric(
    name='Total Revenue',
    expression='[qty] * [price]',
    aggregation='sum',
    ignore_dimensions=True  # Ignore all dimensions when aggregating
)

# Define a metric that ignores specific dimensions (partial total)
cube.define_metric(
    name='Revenue by Country', 
    expression='[qty] * [price]',
    aggregation='sum',
    ignore_dimensions=['city', 'product_category']  # Ignore these dimensions, aggregate only by remaining dimensions
)

# Ignore context filters completely for a metric (compute as if unfiltered context)
cube.define_metric(
    name='Revenue (All Context)',
    expression='[qty] * [price]',
    aggregation='sum',
    ignore_context_filters=True
)

# Ignore only certain context filters for a metric (others still apply)
cube.define_metric(
    name='Revenue (Ignoring Country Filter)',
    expression='[qty] * [price]',
    aggregation='sum',
    ignore_context_filters=['country']  # the metric ignores the 'country' filter from the current context
)

# Advanced NA handling - Using the simple fillna parameter (fills all columns with same value)
cube.define_metric(
    name='Revenue with NA Handling',
    expression='[qty] * [price]',
    aggregation='sum',
    fillna=0  # Fills both qty and price with 0
)

# Advanced NA handling - Using @functions for column-specific handling
cube.define_metric(
    name='Revenue with Column-Specific NA Handling',
    expression='@pd.Series([qty]).fillna(1) * @pd.Series([price]).fillna(0)',
    aggregation='sum'  # Fills [qty] with 1 and [price] with 0
)
```

**Syntax Rules**

- **Column References**: Columns in metric expressions **must** be enclosed in square brackets: `[qty]`, `[price]`, `[cost]`, etc.

- **Aggregation Methods**: The `aggregation` parameter accepts:

   - Pandas group by strings: `'sum'`, `'mean'`, `'count'`, `'min'`, `'max'`, etc.

   - Custom callable functions: `lambda x: x.quantile(0.95)` or any function that accepts a pandas Series


## Define Computed Metric

```python
define_computed_metric(
    name: str,
    expression: str,
    fillna: Optional[Any] = None
) -> None
```

Defines a post-aggregation computed metric that operates on already aggregated metrics and dimensions.

**Parameters:**

- `name`: Unique label for the metric (used in query results)
- `expression`: Calculation formula using [MetricName] references and dimension column references
- `fillna`: Optional value to replace NaN computed metrics expression columns before calculation.

**Example:**

```python
# Define a profit margin percentage computed metric
cube.define_computed_metric(
    name='Margin %',
    expression='([Revenue] - [Cost]) / [Revenue] * 100',
    fillna=0
)
```

**Using in queries:**

You must define computed metrics first, then reference them by name in queries:

```python
cube.define_query(
    query_name='sales_margin_named',
    dimensions={'product'},
    metrics=['Revenue', 'Cost'],
    computed_metrics=['Margin %'],
)
```


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
