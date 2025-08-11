# Hypercube API

The Hypercube class is the central component of Cube Alchemy, providing methods for creating, querying, and analyzing multidimensional data.

## Initialization

```python
Hypercube(
  tables: Dict[str, pd.DataFrame],
  apply_composite: bool = True,
  validate: bool = True,
  to_be_stored: bool = False
)
```

**Parameters:**

- `tables`: Dictionary mapping table names to pandas DataFrames
- `apply_composite`: Whether to automatically create composite keys for multi-column relationships
- `validate`: Whether to validate schema and build trajectory cache during initialization
- `to_be_stored`: Set to True if the hypercube will be serialized/stored (skips Default context state creation)

**Example:**

```python
import pandas as pd
from cube_alchemy import Hypercube

# Create the hypercube with tables
cube = Hypercube({
    'Product': products_df,
    'Customer': customers_df,
    'Sales': sales_df
})
```

## Core Methods

**visualize_graph**

```python
visualize_graph(layout_type: str = 'spring', w: int = 12, h: int = 8) -> None
```

Visualize the relationships between tables as a network graph.

*Parameters:*

- `layout_type`: Algorithm for graph layout ('spring', 'circular', etc.)

- `w`: Width of the plot

- `h`: Height of the plot

*Example:*

```python
# Visualize the data model relationships
cube.visualize_graph('spring', w=20, h=12)
```

**set_context_state**

```python
set_context_state(context_state_name: str) -> bool
```

Create a new context state for independent filtering environments.

*Parameters:*

- `context_state_name`: Name for the new context state

*Returns:*

- Boolean indicating success

*Example:*

```python
# Create a new context state
cube.set_context_state('Marketing Analysis')

# Apply filters specific to this context
cube.filter({'channel': ['Email', 'Social']}, context_state_name='Marketing Analysis')
```