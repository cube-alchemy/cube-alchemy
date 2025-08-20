# Hypercube Components

The Hypercube provides several methods to access its core analytical components. These methods let you see what's available and how everything is defined in your hypercube.

These methods are particularly useful for:

- Understanding the analytical capabilities of a hypercube
- Programmatically accessing and using the defined business logic
- Building dynamic UIs where users can select from available metrics and queries
- Documentation and metadata exploration
- Integrating with other systems that need to understand the data model


## Get Dimensions

```python
get_dimensions() -> List[str]
```

Returns a list of all available dimension columns across all tables.

**Example:**

```python
# Get all available dimensions
all_dimensions = cube.get_dimensions()
print(f"Available dimensions: {all_dimensions}")
```

## Get Metrics

```python
cube.get_metrics() -> Dict[str, Any]
```

Retrieve all defined metrics in the hypercube. Metrics are one of the core components of the hypercube, representing the calculated values and KPIs used for data analysis. Metrics encapsulate business logic, ensuring consistent calculations across all queries and reports.

*Returns:*

- Dictionary of metrics with their details (name, expression, aggregation, and other properties)

## Get Queries

```python
cube.get_queries() -> Dict[str, Any]
```

*Returns:*

- Dictionary of queries with their dimensions, metrics, and display options