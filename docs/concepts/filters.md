# Understanding Filters

Filters in Cube Alchemy let you focus your analysis on specific slices of data without modifying your underlying queries.

## How Filtering Works

When you apply a filter to a context state, all queries and metrics operate only on the filtered data until you change or remove the filter:

1. **Apply a filter** to select specific data values

2. **Execute queries** to analyze just the filtered data

3. **Modify or remove filters** when you want to change focus

```python
# Define metrics first
cube.define_metric(name='Revenue', expression='[qty] * [price]', aggregation='sum')

# Now all queries only see North and West data
cube.define_query(
    name="sales",
    dimensions={'category'},
    metrics=['Revenue']
)

# Focus on specific regions
cube.filter({'region': ['North', 'West']})

cube.query("sales")
```

It works seamlessly across all your connected tables. When you filter by customer region, it automatically affects sales data, product data, and anything else connected through your data model relationships.

## Basic Filtering Operations

### Apply Filters

Filters are defined as dictionaries where keys are dimension names and values are lists of allowed values:

```python
# Single dimension, multiple values
cube.filter({'region': ['North', 'West', 'South']})

# Multiple dimensions at once
cube.filter({
    'region': ['North', 'West'], 
    'product_category': ['Electronics'],
    'customer_segment': ['Enterprise', 'SMB']
})
```

### Remove Specific Filters

Remove filters from specific dimensions while keeping others intact:

```python
# Remove filter on region only (keep other filters)
cube.remove_filter(['region'])

# Remove multiple filters at once
cube.remove_filter(['region', 'product_category'])
```

### Reset All Filters

Clear all filters to return to the full dataset:

```python
# Remove all filters (back to unfiltered data)
cube.reset_filters(direction='all')
```

### View Current Filters

Check which filters are currently active:

```python
# Get dictionary of active filters
current_filters = cube.get_filters()
print(current_filters)
# Output: {'region': ['North', 'West'], 'category': ['Electronics']}
```

## Filter History and Undo/Redo

Cube Alchemy maintains your filtering history, allowing you to navigate through previous filter states:

```python
# Undo last filter operation (step backward)
cube.reset_filters(direction='backward')

# Redo previously undone filter (step forward)
cube.reset_filters(direction='forward')

# Clear all filters and history
cube.reset_filters(direction='all')

# See which dimensions currently have active filters
filtered_dims = cube.get_filtered_dimensions()
```

## Advanced Filtering Techniques

### Per-Metric Filters

While filters apply globally to your hypercube's context state, individual metrics can have their own additional filters:

```python
# Global filter: only Electronics category
cube.filter({'category': ['Electronics']})

# Define metric with additional filter: only Premium-tier electronics
cube.define_metric(
    name='Premium Revenue',
    expression='[qty] * [price]',
    aggregation='sum',
    metric_filters={'price_tier': ['Premium']}  # Additional filter just for this metric
)
```

### 'Unfiltered' and 'Default' Context States

Cube Alchemy maintains two special context states called 'Unfiltered' and 'Default'.

    - 'Unfiltered' always contains your full dataset in the context and cannot be updated. 

    - 'Default' is used as default (as you might have guessed). 

And 'Unfiltered' can also be used on the metric context state: 

```python
# Define standard revenue metric in the default (filtered) context
cube.define_metric(
    name='Filtered Revenue',
    expression='[qty] * [price]',
    aggregation='sum'
    #, context_state_name='Default'
)

# Apply some filters to the default context
cube.filter({'region': ['North', 'South']}) # Applies on 'Default'

# Define a metric using the special Unfiltered context
cube.define_metric(
    name='Total Revenue',
    expression='[qty] * [price]',
    aggregation='sum',
    context_state_name='Unfiltered'  # Always uses the full dataset
)

# Define a query that compares filtered and unfiltered metrics
cube.define_query(
    name="revenue_comparison",
    dimensions={'product_category'},
    metrics=['Filtered Revenue', 'Total Revenue']
)

# The result will show revenue for North and South regions alongside
# the total revenue across all regions for each product category
result = cube.query("revenue_comparison")
```
