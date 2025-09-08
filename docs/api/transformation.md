# Transformation API

Manage query transformations (single-step dataframe augmentations) via registered transformers.

## register_transformer

```python
register_transformer(name: str, transformer: Union[Transformer, Callable[..., pd.DataFrame]]) -> None
```

Register an transformer by name.

## define_transformation

```python
define_transformation(
  query_name: str,
  transformer: str,
  params: Optional[Dict[str, Any]] = None,
) -> None
```

Create or update an transformation for a query. Each transformer can be configured at most once per query.

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
