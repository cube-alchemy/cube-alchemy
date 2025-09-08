# Hypercube Analyitics Assets

These methods let you see what is available and how your dimensions, metrics and queries are defined in your hypercube.

## Get Dimensions

```python
cube.get_dimensions() -> List[str]
```

Returns a list of all available dimension columns across all tables.

**Example:**

```python
# Get all available dimensions
all_dimensions = cube.get_dimensions()
print(f"Available dimensions: {all_dimensions}")
```

## Get a Single Dimension's Values

This accessor now lives under Query Methods as `cube.dimension(...)`.

```python
cube.dimension(dimension: str) -> List[str]
```

Returns the distinct values for a given dimension.

**Example:**

```python
# Get all distinct Product names
products = cube.dimension('Product')
print(products[:10])
```

## Get Metrics

```python
cube.get_metrics() -> Dict[str, Any]
```

Retrieve all defined metrics in the hypercube. Metrics are one of the core components of the hypercube, representing the calculated values and KPIs used for data analysis. Metrics encapsulate business logic, ensuring consistent calculations across all queries and reports.

*Returns:*

- Dictionary of metrics with their details (name, expression, aggregation, and other properties)

## Get a Single Metric

```python
cube.get_metric(metric: str) -> Dict[str, Any]
```

Returns a single metric definition with its details.

**Example:**

```python
revenue = cube.get_metric('Revenue')
print(revenue)
```

## Get Derived Metrics

```python
cube.get_derived_metrics() -> Dict[str, Any]
```

Retrieve all persisted derived metrics.

*Returns:*

- Dictionary mapping derived metric names to specs: expression, optional fillna, and referenced columns

## Get a Single Derived Metric

```python
cube.get_derived_metric(derived_metric: str) -> Dict[str, Any]
```

Returns a single derived metric definition.

**Example:**

```python
margin_pct = cube.get_derived_metric('Margin %')
print(margin_pct)
```

## Get Queries

```python
cube.get_queries() -> Dict[str, Any]
```

*Returns:*

- Dictionary of queries with their dimensions, metrics, and display options

## Get a Single Query

```python
cube.get_query(query: str) -> Dict[str, Any]
```

Returns the definition for a single query (dimensions, metrics, derived_metrics, and options like having).

**Example:**

```python
q = cube.get_query('Sales by Region')
print(q)
```
