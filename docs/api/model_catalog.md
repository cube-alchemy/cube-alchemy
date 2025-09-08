# Model Catalog API

## set_yaml_model_catalog

```python
set_yaml_model_catalog(
    path: Optional[str] = None,
    use_current_directory: bool = True,
    create_if_missing: bool = True,
    default_yaml_name: Optional[str] = None,
) -> Path
```

Attach a YAML file as a source for model definitions and return its resolved path.

## get_yaml_path_model_catalog

```python
get_yaml_path_model_catalog() -> Optional[Path]
```

Return the currently attached YAML path, if any.

## set_model_catalog

```python
set_model_catalog(sources: Iterable[Source], repo: Optional[Repository] = None) -> None
```

Attach multiple sources (merged by Catalog) with an optional repository (defaults to in-memory).

## load_from_model_catalog

```python
load_from_model_catalog(
    kinds: Optional[Iterable[str]] = None,
    clear_repo: bool = False,
    reload_sources: bool = True,
) -> None
```

Load from sources into the Catalog, then apply to the cube. Order: metrics -> derived_metrics -> queries -> plots -> transformers.

## save_to_model_catalog

```python
save_to_model_catalog() -> None
```

Save current cube definitions (metrics, derived metrics, queries, plots, transformers) through attached sources.

Notes:
- The Catalog repository acts as the in-memory store; sources decide persistence (e.g., YAML).

- Plots and transformers are serialized with their associated query reference.
