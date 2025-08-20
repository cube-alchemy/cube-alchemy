# Hypercube Components

These methods let you see what's available and how everything is defined in your hypercube.

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