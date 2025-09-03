# Model Catalog API

## Set YAML Source

```python
cube.set_yaml_model_catalog(
    path: Optional[str] = None, 
    use_current_directory: bool = True,
    create_if_missing: bool = True,
    default_yaml_name: Optional[str] = None
) -> Path
```

Attaches a YAML file as a source for model definitions and returns its resolved path.

**Parameters:**

- `path`: Path to the YAML file. If None, uses `default_yaml_name`

- `use_current_directory`: If True, path is relative to current directory

- `create_if_missing`: If True, creates an empty file if it doesn't exist

- `default_yaml_name`: Default filename if path is None ("model_catalog.yaml")

**Returns:**

- Resolved absolute Path to the YAML file

**Example:**
```python
# Attach the default "model_catalog.yaml" in current directory
path = cube.set_yaml_model_catalog()

# Attach a specific file in another location
path = cube.set_yaml_model_catalog("/path/to/my_definitions.yaml", use_current_directory=False)
```

## Get YAML Path

```python
cube.get_yaml_path_model_catalog() -> Optional[Path]
```

Returns the current YAML path if one has been set.

**Returns:**

- Path to the currently attached YAML file, or None if not set

**Example:**
```python
path = cube.get_yaml_path_model_catalog()
print(f"Using definitions from: {path}")
```

## Attach Custom Sources

```python
cube.set_model_catalog(
    sources: Iterable[Source],
    repo: Optional[Repository] = None
) -> None
```

Attaches multiple definition sources with an optional custom repository.

**Parameters:**

- `sources`: List of Source objects to attach

- `repo`: Optional Repository to use (creates InMemoryRepository if None)

**Example:**
```python
from cube_alchemy.catalogs import Source

class MyCustomSource(Source):
    #....

# Attach sources
sources = [
    MyCustomSource()
]
cube.set_model_catalog(sources)
```

## Refresh Definitions Into Cube

```python
cube.load_from_model_catalog(
    kinds: Optional[Iterable[str]] = None,
    clear_repo: bool = False,
    reload_sources: bool = True
) -> None
```

Loads definitions from attached sources into the catalog, then applies them to the cube.

**Parameters:**

- `kinds`: Optional list of definition types to refresh ("metrics", "queries", etc.)

- `clear_repo`: If True, clears existing repository before refreshing

- `reload_sources`: If True, reloads from sources instead of using cache

**Example:**
```python
# Load all definitions from YAML into cube
cube.load_from_model_catalog()

# Only refresh metrics definitions
cube.load_from_model_catalog(kinds=["metrics"])
```

## Save Definitions

```python
cube.save_to_model_catalog() -> None
```

Saves the current cube metrics, computed metrics, queries and plot config definition contents to attached sources.

**Example:**
```python
# Define metrics and queries
cube.define_metric("revenue", expression="[sales] * [price]", aggregation="sum")
cube.define_query("sales_by_region", dimensions=["region"], metrics=["revenue"])

# Save to YAML (pulls from cube to repo internally)
cube.save_to_model_catalog()
```

## List Definitions

Use the underlying Catalog directly:

```python
# List all metrics
metrics = cube.model_catalog.list("metrics")
print(f"Available metrics: {metrics}")

# List all queries
queries = cube.model_catalog.list("queries")
print(f"Available queries: {queries}")
```

## Typical Workflow

```python
# 1. Attach a YAML file
cube.set_yaml_model_catalog("model_catalog.yaml")

# 2. Load existing definitions into the cube
cube.load_from_model_catalog()

# 3. Create or modify definitions
cube.define_metric("revenue", expression="[sales] * [price]", aggregation="sum")

# 4. Save changes back to YAML
cube.save_to_model_catalog()
```
