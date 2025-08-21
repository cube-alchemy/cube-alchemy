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
    query_name="regional_sales",
    dimensions={'region', 'category'},
    metrics=['Revenue', 'Order Count']
)

# Execute the query
result = cube.query("regional_sales")
```

### How Query Execution Works

When you run a query, Cube Alchemy efficiently processes your data in four steps:

1. **Group metrics by context**: Metrics sharing the same context state and custom metric filters are calculated together
2. **Fetch required data**: All necessary dimension and metric columns are retrieved automatically, traversing table relationships and getting the required metric columns' indexes
3. **Apply aggregations**: Each metric's aggregation is applied to the corresponding dimensions
4. **Merge results**: The individual metric calculations are combined based on your specified dimensions


## Query Types

Queries must contain either dimensions, metrics, or both (a query cannot lack both).

### Dimension-Only Queries

When you only need to see what unique dimension combinations:

```python
# Define a query with only dimensions
cube.define_query(
    query_name="dimension_combinations",
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
    query_name="global_totals",
    metrics=['Total Revenue', 'Total Orders']
)

# Execute the query
global_results = cube.query("global_totals")
```

## Query Options

Fine-tune your query results with these options:

- `drop_null_dimensions=True`: Remove rows with missing dimension values
- `drop_null_metric_results=True`: Remove rows with null metric results
- `computed_metrics=[...]`: Define post-aggregation columns derived from metric results (e.g., ratios and percentages)
- `having="..."`: Apply a HAVING-like filter on the aggregated result using metric columns

```python
cube.define_query(
    query_name="clean_sales_data",
    dimensions={'region', 'category'},
    metrics=['Revenue', 'Orders'],
    drop_null_dimensions=True,
    drop_null_metric_results=True
)
```

## Computed Metrics and HAVING

**Post-aggregation**

Sometimes you want to compute a value after metrics are aggregated, or filter rows by a metric result like in SQL's HAVING clause. You can do both at the query level:

```python
# Define base metrics
cube.define_metric(name='Cost',    expression='[cost]',           aggregation='sum')
cube.define_metric(name='Margin',  expression='[qty] * [price] - [cost]', aggregation='sum')

# Add a computed metric and a HAVING filter
cube.define_query(
    query_name='margin_by_product',
    dimensions={'product'},
    metrics=['Margin', 'Cost'],
    computed_metrics=[
        { 'name': 'Margin %', 'expression': '[Margin] / [Cost] * 100', 'fillna': 0 }
    ],
    having='[Margin %] >= 20'
)

df = cube.query('margin_by_product')
```

**Notes:**

- Use the same bracket syntax [Column] in expressions; registered functions are available as @name.

- Computed metrics run after aggregations and can reference any metric/dimension present in the result.

## Working with Filters

Queries automatically respect all active filters on your hypercube, allowing you to:

1. Define a query once
2. Apply different filters
3. Execute the same query to see different filtered views of your data

```python
# Define your query
cube.define_query(
    query_name="product_sales",
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
