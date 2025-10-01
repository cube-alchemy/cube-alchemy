# Transformation API

Manage query transformations (single-step dataframe augmentations) via registered transformers.

## register_transformer

```python
register_transformer(name: str, transformer: Union[Transformer, Callable[..., pd.DataFrame]]) -> None
```

Register an transformer by name.
Notes:

- The implementation registers a set of default transformers (if available) during initialization. You can override or add new transformers via this method.

- `transformer` may be an instance implementing the `Transformer` interface or a plain callable that accepts a DataFrame and returns a DataFrame.

## define_transformation

```python
define_transformation(
  query_name: str,
  transformer: str,
  params: Optional[Dict[str, Any]] = None,
) -> None
```

Create or update an transformation for a query. Each transformer can be configured at most once per query.
Notes:
- Defining a transformation registers a dependency in the cube's dependency index so downstream refreshes can be tracked.

## list_transformations

```python
list_transformations(query_name: str) -> List[str]
```

List configured transformer names for the query.

## get_transformation_config

```python
get_transformation_config(query_name: str, transformer: Optional[str] = None) -> Dict[str, Any]
```

Return stored parameters for a transformer in a query.
Notes:

- If `overwrite=True` the transform result replaces the provided DataFrame; otherwise only newly added columns are joined into the original result.

- If `copy_input=True` the input DataFrame is copied before calling the transformer; otherwise the transformer may mutate the provided DataFrame.

- The method raises if the named transformer is not registered.

## delete_transformation

```python
delete_transformation(query_name: str, transformer: str) -> None
```

Delete an transformation configuration from a query.

## transform

```python
transform(
  df: pd.DataFrame,
  transformer: Optional[str] = None,
  params: Optional[Dict[str, Any]] = None,
  *,
  overwrite: bool = False,
  copy_input: bool = False,
  **overrides,
) -> pd.DataFrame
```

Run a single-step transformation using a registered transformer on the given DataFrame.
