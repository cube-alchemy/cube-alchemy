# Understanding Metrics

A metric is a calculated measure that aggregates data in some meaningful way. Think revenue, profit margin, average order size, customer count—basically any aggregated value that helps you analyze your data.

In Cube Alchemy, metrics are defined once and stored within the cube object for later use:

1. You **define a metric** using `cube.define_metric()` providing at least a name, expression, and aggregation method
2. The metric is **stored in the cube object**
3. Later, you **reference metrics by name** when defining queries

## Building a Metric

Every metric needs three essential components:

1. **Name**: A clear, descriptive label for the metric (e.g., 'Revenue', 'Customer Count')
2. **Expression**: The calculation formula, using dimension references inside square brackets (e.g., `[qty] * [price]`)
3. **Aggregation**: How to combine values—standard methods like `sum`, `mean`, `count`, or custom functions


```python
# Step 1: Define your metrics
cube.define_metric(
    name='Revenue',
    expression='[qty] * [price]',
    aggregation='sum'
)

cube.define_metric(
    name='Average Order Value', 
    expression='[price]',
    aggregation='mean'
)

cube.define_metric(
    name='Number of Orders',
    expression='[order_id]',
    aggregation=lambda x: x.nunique()
)

# Step 2: Define a query that uses these metrics
cube.define_query(
    name="sales_performance",
    dimensions={'region', 'product_category'},
    metrics=['Revenue', 'Average Order Value', 'Number of Orders']
)

# Step 3: Execute the query by referencing its name
result = cube.query("sales_performance")

# The metrics are calculated and returned as columns in the result DataFrame
```

## Syntax Rules

- **Column References**: Columns in metric expressions **must** be enclosed in square brackets: `[qty]`, `[price]`, `[cost]`, etc.

- **Aggregation Methods**: The `aggregation` parameter accepts:

    - Pandas group by strings: `'sum'`, `'mean'`, `'count'`, `'min'`, `'max'`, etc.

    - Custom callable functions: `lambda x: x.quantile(0.95)` or any function that accepts a pandas Series

## Computed Metrics

Computed metrics are calculated after aggregation has already occurred. While regular metrics aggregate over dimensions, computed metrics work with already aggregated results, letting you create ratios, percentages, and other derivative calculations.

```python
# First define the metrics needed for the computation
cube.define_metric(
    name='Revenue',
    expression='[qty] * [price]',
    aggregation='sum'
)

cube.define_metric(
    name='Cost',
    expression='[qty] * [unit_cost]',
    aggregation='sum'
)

# Then define a computed metric that uses them
cube.define_computed_metric(
    name='Profit Margin %',
    expression='([Revenue] - [Cost]) / [Revenue] * 100'
)

# Use both regular and computed metrics in queries
cube.define_query(
    name="profitability_analysis",
    dimensions={'product_category', 'region'},
    computed_metrics=['Profit Margin %']
)

# Execute the query
result = cube.query("profitability_analysis")
```

The workflow is:

1. Define regular metrics that perform aggregation

2. Define computed metrics that reference those aggregated metrics

3. Include them in your queries (computed metrics are passed separately)

## Advanced Features

For more sophisticated analysis, metrics support several powerful options:

- **Different context states**: Calculate metrics in different filtering environments
- **Metric filters**: Apply specific filters only for a particular metric
- **Row conditions**: Pre-filter rows before calculating the metric
- **Custom functions**: Use your own Python functions for complex logic
- **Computed metrics**: Create post-aggregation calculations like margins and ratios

Each of these options allows you to create highly specialized metrics that can answer specific more sophisticated questions.

```python
# Only count high-value orders
cube.define_metric(
    name='High Value Orders',
    expression='[order_id]',
    aggregation='count',
    row_condition_expression='[price] > 100'
)

# Revenue only from specific regions (metric-level filter)
cube.define_metric(
    name='Regional Revenue',
    expression='[qty] * [price]',
    aggregation='sum',
    metric_filters={'region': ['North', 'West']}
)

# Create a new Context State
cube.set_context_state('My New Context')

# Apply different filters to it
cube.filter(
    {'date': ['2024-10-01', '2024-11-01', '2024-12-01']},
    context_state_name='My New Context'
)

# Define a metric using the new context
cube.define_metric(
    name='High Value Orders',
    expression='[order_id]',
    aggregation='count',
    context_state_name='My New Context'
)

# Define a query with these metrics
cube.define_query(
    name="advanced_analysis",
    dimensions=set(my_query_dimensions),
    metrics=['High Value Orders', 'Regional Revenue', 'High Value Orders']
)

# Execute the query
result = cube.query("advanced_analysis")
```

## Custom Functions

When your analysis requires logic that goes beyond basic arithmetic, you can register and use custom Python functions:

1. **Define a Python function** that performs your specialized calculation
2. **Register the function** with your cube using `cube.register_function()`
3. **Reference the function** in your metric expressions using the `@function_name` syntax

This powerful feature allows you to implement virtually any calculation logic while keeping your metric definitions clean and readable.

```python
import numpy as np

# Define and register a safe division function
def safe_division(numerator, denominator, default=0.0):
    """Safely divide two arrays, handling division by zero"""
    result = numerator / denominator
    return result.replace([np.inf, -np.inf], np.nan).fillna(default)

# Register the function with your hypercube
cube.register_function(safe_division=safe_division)

# Use it in a metric definition
cube.define_metric(
    name='Profit Margin %',
    expression='@safe_division([revenue] - [cost], [revenue]) * 100',
    aggregation='mean'
)

# Another example: categorizing data
def categorize_revenue(revenue_values):
    """Categorize revenue into tiers"""
    conditions = [
        revenue_values < 1000,
        (revenue_values >= 1000) & (revenue_values < 5000),
        revenue_values >= 5000
    ]
    choices = ['Low', 'Medium', 'High']
    return np.select(conditions, choices, default='Unknown')

cube.register_function(categorize_revenue=categorize_revenue)

# Use for conditional logic - count how many sales fall into each tier
cube.define_metric(
    name='Revenue Tier Count',
    expression='@categorize_revenue([qty] * [price])',
    aggregation=lambda x: len(x)
)

# Or get the most common revenue tier
cube.define_metric(
    name='Most Common Revenue Tier',
    expression='@categorize_revenue([qty] * [price])',
    aggregation=lambda x: x.value_counts().index[0]
)
```

**Note on Function Handling**

Metric aggregation allows you to pass custom functions directly while expression functions need to be registered on the hypercube first and referenced with `@function_name`. This difference exists due to their roles in the processing pipeline:

- **Expression functions** operate inside within dataframe rows before aggregation
- **Aggregation functions** work outside on the grouped data