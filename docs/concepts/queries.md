# Understanding Queries

Queries in Cube Alchemy bring together metrics and dimensions to answer specific questions.

A query consists of three key components:

- **Query name**: A unique identifier for referencing the query

- **Dimensions**: Columns to group by (the "by what" in your analysis)

- **Metrics**: Measures to calculate (the "what" in your analysis)

```python
# Define metrics
cube.define_metric(name='Revenue', expression='[qty] * [price]', aggregation='sum')
cube.define_metric(name='Order Count', expression='[order_id]', aggregation='count')

# Define a query by region and product category
cube.define_query(
    name="regional_sales",
    dimensions={'region', 'category'},
    metrics=['Revenue', 'Order Count']
)

# Execute the query
result = cube.query("regional_sales")
```

### Execution Pipeline

When you run a query, Cube Alchemy processes your data in a clear, ordered pipeline:

```mermaid
flowchart LR
  A["Apply Context State Filters"] --> B["Fetch Dimensions"]
  B --> C["Calculate Metrics (Aggregations)"]
  C --> D["Compute Post-Aggregation Metrics"]
  D --> E["Apply DataFrame Transformer"]
  E --> F["Apply HAVING Filter"]
  F --> G["Apply SORT"]
  G --> H["Return Final Result"]
```

## Query Types

Queries must contain either dimensions, metrics, or both (a query cannot lack both).

### Dimension-Only Queries

When you only need to see what unique dimension combinations:

```python
# Define a query with only dimensions
cube.define_query(
    name="dimension_combinations",
    dimensions={'region', 'category'}
)

# Get all unique region/category combinations
combinations = cube.query("dimension_combinations")
```

### Metric-Only Queries

When you need to calculate global aggregates:

```python
# Define metrics
cube.define_metric(name='Total Revenue', expression='[qty] * [price]', aggregation='sum')
cube.define_metric(name='Total Orders', expression='[order_id]', aggregation='count')

# Define a query with no dimensions
cube.define_query(
    name="global_totals",
    metrics=['Total Revenue', 'Total Orders']
)

# Execute the query
global_results = cube.query("global_totals")
```

## Derived Metrics and HAVING

Derived metrics are calculated after base metrics are aggregated. Define them once, then reference by name in queries.

```python
# Define base metrics
cube.define_metric(name='Cost',   expression='[cost]',           aggregation='sum')
cube.define_metric(name='Margin', expression='[qty] * [price] - [cost]', aggregation='sum')

# Define a derived metric (post-aggregation)
cube.define_derived_metric(
    name='Margin %',
    expression='[Margin] / [Cost] * 100',
    fillna=0
)

# Use derived metric by name and add a HAVING filter
cube.define_query(
    name='margin_by_product',
    dimensions={'product'},
    metrics=['Margin', 'Cost'],
    derived_metrics=['Margin %'],
    having='[Margin %] >= 20'
)

df = cube.query('margin_by_product')
```

Notes:

- Use [Column] syntax in expressions; functions you register are available as `@name`.
- Register functions with `cube.add_functions(...)`. You can inspect or replace the full registry via `cube.function_registry`.
- Derived metrics reference columns present in the aggregated result (metrics and dimensions).

### Registered Functions

You can register helper functions for use in metrics. 

All registered functions operate on 1D data: the first argument is a pandas `Series` (or NumPy array-like). You may add extra parameters as needed.

- Expression functions: return a `Series` of the same length. Used inside expressions via `@name(...)`.
- Filter/HAVING functions: return a boolean `Series` of the same length. Used in HAVING via `@name(...)`.
- Aggregation functions: return a single value per group (e.g., number, text, or list).

Access:
- In expressions and HAVING (string evaluation): use `@function_name(...)`.
- For aggregations: reference by name (no `@`), e.g., `aggregation='p90'`. You can pass a callable, but it will not persist to pickle or YAML; prefer registering the function and using its name.

Examples

```python
# 1) Expression function: register and use in a metric
def double_series(s):
    return s * 2

cube.add_functions(double=double_series)
cube.define_metric(
    name='Double Revenue',
    expression='@double([qty]) * [price]',
    aggregation='sum'
)

cube.define_query(
    name='double_revenue_by_segment',
    dimensions=['segment'],
    metrics=['Double Revenue']
)
df = cube.query('double_revenue_by_segment')

# 2) HAVING function: register and use as a filter
def above(s, threshold):
    return s >= threshold

cube.add_functions(above=above)
cube.define_metric(name='Revenue', expression='[qty] * [price]', aggregation='sum')
cube.define_query(
    name='big_segments',
    dimensions={'segment'},
    metrics=['Revenue'],
    having='@above([Revenue], 1000)'
)
df2 = cube.query('big_segments')

# Tip: to persist functions across save/load, define them in a module and import before registering
# from udfs import double_series, above
# cube.add_functions(double=double_series, above=above)

# 3) Aggregation function: register and reference by name (persists if importable)
import numpy as np, pandas as pd
def p90(x):
    a = np.asarray(pd.Series(x).dropna())
    return float(np.percentile(a, 90)) if a.size else float('nan')

cube.add_functions(p90=p90)
cube.define_metric(name='P90 Revenue', expression='[qty] * [price]', aggregation='p90')
cube.define_query(
    name='p90_revenue_by_segment',
    dimensions={'segment'},
    metrics=['P90 Revenue']
)
df3 = cube.query('p90_revenue_by_segment')
```

### Persistence and Function Registry

Hypercubes can be saved and loaded with `cube.save_as_pickle(...)` and `Hypercube.load_pickle(...)`. The function registry persists by import spec:

- Importable top-level objects (modules, functions, classes) are restored.
- Lambdas, closures, and locally defined callables are not persisted and will be dropped silently.

Example:

```python
from cube_alchemy.core.hypercube import Hypercube
from udfs import double  # top-level function in an importable module

cube.add_functions(double=double)        # persisted IF 'udfs' is importable at load time
cube.add_functions(tmp=lambda x: x + 1)  # not persisted

path = cube.save_as_pickle(pickle_name="cube.pkl")
cube2 = Hypercube.load_pickle(path)

assert 'double' in cube2.function_registry  # only if 'udfs' is on sys.path
assert 'tmp' not in cube2.function_registry
```

Important:
- A function persists only if its defining module is importable in the loading environment (on sys.path, correct module name).
- If a query or metric references a non-restored function (e.g., a lambda or a function defined only in __main__), evaluation will raise. Re-register an importable function with the same name before running the query again.

### Effective dimensions

Effective dimensions are the dimensions that actually determine how a metric is aggregated. They are derived from the query’s dimensions after applying the metric’s `ignore_dimensions` setting:

- `ignore_dimensions=False` (default): effective dimensions = query dimensions.

- `ignore_dimensions` is a list: effective dimensions = query dimensions minus those listed.

- `ignore_dimensions=True`: no effective dimensions (grand total).

Nested metrics use the same effective dimensions in both inner and outer steps; `nested.dimensions` are added only for the inner step.

## Nested aggregation (inner → outer)

Use `nested` on a metric to aggregate in two steps: first by `nested.dimensions` (inner), then at the query dimensions (outer).

- Inner: aggregate the metric by the effective dimensions plus `nested.dimensions`.

- Outer: aggregate those inner results by the effective dimensions. If you display extra dimensions, results are broadcast to them.

Note: `ignore_dimensions` sets the metric’s effective dimensions and applies to both steps so results stay unbiased and consistent.

Minimal example:

```python
cube.define_metric(
    name='Avg Product Revenue',
    expression='[qty] * [price]',
    aggregation='mean',
    nested={'dimensions': 'Product', 'aggregation': 'sum'},
    ignore_dimensions=['Store']  # compute at Country-level; broadcast when displaying Store
)
```

## Working with Filters

Queries automatically respect all active filters on your hypercube, allowing you to:

1. Define a query once

2. Apply different filters

3. Execute the same query to see different filtered views of your data

```python
# Define your query
cube.define_query(
    name="product_sales",
    dimensions={'region', 'product_category'},
    metrics=['Revenue', 'Order Count']
)

# Get unfiltered results
unfiltered_results = cube.query("product_sales")

# Apply filters
cube.filter({'product_type': ['Electronics', 'Home']})

# Get filtered results using the same query
filtered_results = cube.query("product_sales")
```
