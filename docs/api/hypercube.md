# Hypercube API

The Hypercube class is the central component of Cube Alchemy, providing methods for creating, querying, and analyzing multidimensional data.

## Initialization

The Hypercube can be initialized in two ways:

```python
# Option 1: Initialize with data
Hypercube(
  tables: Dict[str, pd.DataFrame] = None,
  rename_original_shared_columns: bool = True,
  apply_composite: bool = True,
  validate: bool = True,
  to_be_stored: bool = False
)

# Option 2: Initialize empty and load data later
Hypercube()
load_data(
  tables: Dict[str, pd.DataFrame],
  rename_original_shared_columns: bool = True,
  apply_composite: bool = True,
  validate: bool = True,
  to_be_stored: bool = False,
  reset_all: bool = False
)
```

The `load_data()` method can also be used to reload or update data in an existing hypercube.

**Parameters:**

- `tables`: Dictionary mapping table names to pandas DataFrames

- `rename_original_shared_columns`: Controls what happens to shared columns in source tables.  

  - True (default): keep them, renamed as `<column> (<table_name>)`. Enables per‑table counts/aggregations.  

  - False: drop them from source tables (values remain in link tables). Saves time and memory if per‑table analysis isn’t needed.  

- `apply_composite`: Whether to automatically create composite keys for multi-column relationships

- `validate`: Whether to validate schema and build trajectory cache during initialization

- `to_be_stored`: Set to True if the hypercube will be serialized/stored (skips Default context state creation)

- `reset_all` *(only load_data method)*: Whether to reset metrics and queries definitions, as well as registered functions when reloading data

**Examples:**

```python
import pandas as pd
from cube_alchemy import Hypercube

# Option 1: Initialize with data (keep renamed shared columns)
cube1 = Hypercube({
    'Product': products_df,
    'Customer': customers_df,
    'Sales': sales_df
}, rename_original_shared_columns=True)

# Option 2: Initialize empty first, then load data
cube2 = Hypercube()
cube2.load_data({
    'Product': products_df,
    'Customer': customers_df,
    'Sales': sales_df
}, rename_original_shared_columns=False)

# Reload data in an existing hypercube (e.g., when data is updated)
cube1.load_data({
    'Product': updated_products_df,
    'Customer': updated_customers_df,
    'Sales': updated_sales_df
})

# Reset metrics and queries when loading new data schema
cube2.load_data(new_data, reset_all=True)
```

## Core Methods

### visualize_graph

```python
visualize_graph(
  w: Optional[float] = None,
  h: Optional[float] = None,
  full_column_names: bool = False,
  seed: Optional[int] = None,
  show: bool = True,
  return_fig: bool = False,
) -> Optional[matplotlib.figure.Figure]
```

Visualize the relationships between tables as a network graph.

*Parameters:*

- `w`: Width of the plot in inches. If None, an automatic size is chosen based on graph size.

- `h`: Height of the plot in inches. If None, an automatic size is chosen based on graph size.

- `full_column_names`: Whether to show renamed columns with table reference (e.g., `column <table_name>`) or just the original column names.

- `seed`: RNG seed for the spring layout; set a fixed value to make the layout reproducible.

- `show`: If True, call `plt.show()` to display the figure.

- `return_fig`: If True, return the Matplotlib Figure instead of None.



*Example:*

```python
# Visualize the data model relationships
cube.visualize_graph()

# Hide renamed column format for cleaner display
cube.visualize_graph(full_column_names=False)
```
*Note: If the displayed graph doesn't look so good try a couple of times or adjust the size.*

### relationship_matrix

```python
relationship_matrix(context_state_name: str = 'Unfiltered') -> pd.DataFrame
```
Reconstruct the original shared columns across the model to inspect connectivity.

### get_cardinalities

```python
get_cardinalities(context_state_name: str = 'Unfiltered', include_inverse: bool = False) -> pd.DataFrame
```
Compute relationship cardinalities for shared keys between base tables; optionally include inverse orientation.

## Shared columns: counts and distincts

When multiple tables share a column (for example, `customer_id`), Cube Alchemy builds a link table containing the distinct values of that column across all participating tables. This has two practical implications:

- Counting on the shared column name (e.g., `customer_id`) uses the link table and therefore reflects distinct values in the current filtered context across all tables that share it.

- Counting on a per-table renamed column (e.g., `customer_id <orders>` or `customer_id <customers>`) uses that table’s own column values. The result can differ from the shared-column count because it’s scoped to that single table's values and is not the cross-table distinct set.

Example idea:

- Count distinct `customer_id` (shared) → distinct customers across all linked tables.

- Count distinct `customer_id <orders>` → distinct customers present in the Orders table specifically.

Choose the one that matches your analytical intent: cross-table distincts via the shared column, or table-specific distincts via the renamed columns. Note: per-table renamed columns are available only when `rename_original_shared_columns=True`; set it to False to drop them and reduce memory/processing if you don’t need that analysis.