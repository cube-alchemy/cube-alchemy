# Hypercube Analytics Specs

Inspect and manage analytics assets (dimensions, metrics, derived metrics, and queries) defined in the hypercube.

## define_metric

```python
define_metric(
	name: Optional[str] = None,
	expression: Optional[str] = None,
	aggregation: Optional[Union[str, Callable[[Any], Any]]] = None,
	metric_filters: Optional[Dict[str, Any]] = None,
	row_condition_expression: Optional[str] = None,
	context_state_name: str = 'Default',
	ignore_dimensions: bool = False,
	ignore_context_filters: bool = False,
	fillna: Optional[Any] = None,
	nested: Optional[Dict[str, Any]] = None,
) -> None
```

Define a base metric used by queries. The method constructs an internal `Metric` object, infers table/column contexts and registers dependency edges so queries referencing the metric can be refreshed automatically when the metric is added.

Parameters:

- `name`: Optional string name for the metric. If not provided, the Metric class may infer or raise according to its own rules.

- `expression`: The expression string describing how the metric is computed (column names, functions, etc.).

- `aggregation`: Aggregation to apply (string like 'sum', or a callable aggregator).

- `metric_filters`: Optional dict of filters to apply when computing the metric.

- `row_condition_expression`: Optional expression to filter rows before aggregation.

- `context_state_name`: Context state to attach the metric to (defaults to 'Default').

- `ignore_dimensions`: If True, dimensions will be ignored when computing the metric.

- `ignore_context_filters`: If True, context filters are ignored for this metric.

- `fillna`: Optional value to fill missing results.

- `nested`: Optional nested configuration used by composite/nested metrics.

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

## define_derived_metric

```python
define_derived_metric(name: str, expression: str, fillna: Optional[Any] = None) -> None
```

Persist a post-aggregation derived metric. Derived metrics are evaluated after base metric aggregation and can reference aggregated columns or dimensions using the library's computed-column syntax.

Parameters:

- `name`: Name of the derived metric (required).

- `expression`: Expression string for the derived metric (required).

- `fillna`: Optional value to use to fill missing values after evaluation.

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

## define_query

```python
define_query(
	name: str,
	dimensions: set[str] = {},
	metrics: List[str] = [],
	derived_metrics: List[str] = [],
	having: Optional[str] = None,
	sort: List[Tuple[str, str]] = [],
	drop_null_dimensions: bool = False,
	drop_null_metric_results: bool = False,
)
```

Create or redefine a query specification. The implementation precomputes "hidden" base and derived metrics required by requested derived metrics, HAVING expressions, and SORT columns. It also registers dependency edges so queries will be auto-refreshed when referenced metrics or derived metrics are later defined.

Parameters:
- `name`: Query identifier.
- `dimensions`: Ordered set/list of dimension column names used by the query.
- `metrics`: List of base metric names to compute.
- `derived_metrics`: List of derived metric names to compute (post-aggregation).
- `having`: Optional HAVING expression applied after aggregation.
- `sort`: List of (column, direction) tuples describing sort order.
- `drop_null_dimensions`: If True, rows with nulls in dimension columns are dropped.
- `drop_null_metric_results`: If True, rows with null metric results are dropped.

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
