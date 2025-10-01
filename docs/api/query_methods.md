# Query Methods

## query

```python
query(
    query_name: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame
```

Execute a stored query by name, or pass options to run an ad‑hoc query (without persisting it).

When options is provided, accepted keys mirror define_query parameters: dimensions, metrics, derived_metrics, having, sort, drop_null_dimensions, drop_null_metric_results.

Note: the implementation also accepts an internal flag `_retrieve_query_name: bool` (used when plotting or creating ad-hoc queries) which, if True, returns a tuple (generated_query_name, DataFrame) instead of only the DataFrame. This parameter is primarily for internal use but exists on the public method signature.

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

## reset_specs

```python
reset_specs() -> None
```

Clear all defined analytics specifications in the hypercube: base metrics, derived metrics, queries, plotting components, transformation components, and reset the function registry to defaults. This also clears the dependency index used to track sources -> dependents. Use this when you want a clean slate for analytics definitions.

## function_registry (property)

```python
function_registry -> Any
# setter accepts: FunctionRegistry | dict | None | mapping-convertible
```

Central registry of functions/modules available to metric and derived-metric expressions and to DataFrame.query (via `@name`).

Setting the `function_registry` accepts:
- a `FunctionRegistry` instance,
- a `dict` of name->callable,
- `None` to reset to defaults,
- or any mapping convertible to `dict`.

The registry is used during evaluation and also controls which callables are persisted when pickling the hypercube (only importable top-level callables are storable).
