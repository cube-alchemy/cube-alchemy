You can think of it as a separate filtering environment.

There are two main context states:

- **'Unfiltered'**: This is created at the hypercube initialization. It has all the relationships that exists accross all the tables that conform the DAG when there is no filter applied. It is a special internal use state, and is not allowed to filter on it.
    
- **'Default'**: When initializing the hypercube *on memory*, we take a copy of the unfiltered state. Then by default the filters and queries will use this context state, but you can change that..

**More states (?)**

You can also create more context states, as many as you want. They allow you to create multiple independent filtering contexts within the same app so you can compare, isolate, simulate different scenarios side by side or use to create more advanced filtering scenarios.

**Creating new context states:**

```python
# Create a new filtering environment
cube.set_context_state('New Analysis')

# Apply filters specific to this context
cube.filter(
    {'date': ['2024-10-01', '2024-11-01', '2024-12-01']}, 
    context_state_name='New Analysis'
)

# Define metrics using the specific context state
cube.define_metric(
    name='New Analysis Revenue',
    expression='[qty] * [price]', 
    aggregation='sum',
    context_state_name='New Analysis'  # This metric uses the New Analysis context
)

# Define regular metrics (using Default context)
cube.define_metric(
    name='Regular Revenue',
    expression='[qty] * [price]', 
    aggregation='sum'
    # No context_state_name means it uses 'Default'
)

# Define a query that will use both metrics
cube.define_query(
    name="revenue_comparison",
    dimensions={'region'},
    metrics=['Regular Revenue', 'New Analysis Revenue']
    # Queries don't have context_state_name parameter
)

# Execute the query - it will show revenue from both context states
comparison_results = cube.query("revenue_comparison")
```

*Bear in mind that when creating a new context state, a copy of the 'Unfiltered' context state holding all the relationships will be made and stored on memory.*