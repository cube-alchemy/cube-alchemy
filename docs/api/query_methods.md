# Query Methods

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
) -> None
```

Persist a named query (dimensions + metrics) with optional derived metrics, having, and sort. Hidden dependencies are computed automatically.

Parameters:
- name: Unique query name.

- dimensions: Set[str] of dimension columns.

- metrics: List[str] of base metric names.

- derived_metrics: List[str] of derived metric names.

- having: Expression using [Column] syntax, applied after aggregation.

- sort: List of (column, direction) where direction is 'asc'|'desc'.

- drop_null_dimensions: Drop rows with null dimension values.

- drop_null_metric_results: Drop rows with null metric results.

## query

```python
query(
    query_name: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame
```

Execute a stored query by name, or pass options to run an ad‑hoc query (without persisting it).

When options is provided, accepted keys mirror define_query parameters: dimensions, metrics, derived_metrics, having, sort, drop_null_dimensions, drop_null_metric_results.

## add_functions

```python
add_functions(**kwargs) -> None
```

Add variables/functions available to expressions and `DataFrame.query` via `@name`.

Notes:
- Use `cube.add_functions(my_udf=my_udf, normalize=normalize)` to register.
- Access/replace the whole registry via `cube.function_registry` (a dict-like object).
 - Only importable, top-level functions/classes/modules are persisted across `cube.save_as_pickle()`/`Hypercube.load_pickle()`; lambdas and locally defined callables are skipped.
 - If a query references a function that wasn’t restored after load, execution raises; re-register the function first.

## dimensions

```python
dimensions(
    columns_to_fetch: List[str],
    retrieve_keys: bool = False,
    context_state_name: str = 'Default',
    query_filters: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame
```

Return unique combinations for requested dimensions, optionally including link keys.

## dimension

```python
dimension(
    dimension: str,
    context_state_name: str = 'Default',
    query_filters: Optional[Dict[str, Any]] = None,
) -> List[str]
```

Return distinct values for a single dimension.
