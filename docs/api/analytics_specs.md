# Hypercube Analytics Specs

Inspect and manage analytics assets (dimensions, metrics, derived metrics, and queries) defined in the hypercube.

## get_dimensions

```python
get_dimensions() -> List[str]
```

Return all available dimension columns across all tables.

Note: to fetch distinct values for a single dimension, see Query API: `dimension(dimension: str) -> List[str]`.

## get_metrics

```python
get_metrics() -> Dict[str, Any]
```

Retrieve all defined base metrics. 

*Returns:*

- Dictionary of metrics with their details (name, expression, aggregation, and other properties)

## get_metric

```python
get_metric(metric: str) -> Dict[str, Any]
```

Return a single base metric definition.

## get_derived_metrics

```python
get_derived_metrics() -> Dict[str, Any]
```

Retrieve all persisted derived metrics.

*Returns:*

- Dictionary mapping derived metric names to specs: expression, optional fillna, and referenced columns

## get_derived_metric

```python
get_derived_metric(derived_metric: str) -> Dict[str, Any]
```

Return a single derived metric definition.

## get_queries

```python
get_queries() -> Dict[str, Any]
```

*Returns:*

- Dictionary of queries with their dimensions, metrics, and display options

## get_query

```python
get_query(query: str) -> Dict[str, Any]
```

Return the definition for a single query (dimensions, metrics, derived_metrics, and options like having and sort).

Fields include:
- `dimensions`: List[str]

- `metrics`: List[str]

- `derived_metrics`: List[str]

- `having`: Optional[str]

- `sort`: List[Tuple[str, str]]

- `drop_null_dimensions`: bool

- `drop_null_metric_results`: bool

See Query API for creation and execution semantics.

## delete_query

```python
delete_query(name: str) -> None
```

Remove a query definition and its dependency edges. Any linked plots are detached.

## delete_metric

```python
delete_metric(name: str) -> None
```

Remove a base metric. Dependent queries will still reference the name and appear missing until redefined.

## delete_derived_metric

```python
delete_derived_metric(name: str) -> None
```

Remove a derived metric. Dependent queries will still reference the name and appear missing until redefined.

## debug_dependencies

```python
debug_dependencies() -> Dict[str, List[List[str]]]
```

Return a snapshot of dependency edges from sources (metric/derived metric/query names) to their dependents.

## debug_missing_dependencies

```python
debug_missing_dependencies() -> Dict[str, List[List[str]]]
```

Return only unresolved sources (not a defined base metric, not a defined derived metric, not a known dimension, and not a query). Useful to identify missing definitions referenced by queries or plots.
