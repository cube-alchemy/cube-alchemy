# Filter Methods

## Apply Filter

```python
filter(
  criteria: Dict[str, List[Any]], 
  context_state_name: str = 'Default',
  is_reset: bool = False,
  save_state: bool = True
) -> bool
```

Apply filters to focus analysis on specific data slices.

**Parameters:**

- `criteria`: Dictionary mapping dimension names to lists of values to keep
- `context_state_name`: Which context state to filter
- `is_reset`: Whether to replace existing filters (True) or add to them (False)
- `save_state`: Whether to save the filter state for undo/redo operations

**Returns:**

- Boolean indicating success

**Example:**

```python
# Filter to specific regions
cube.filter({'region': ['North', 'South']})

# Filter to specific products within those regions
cube.filter({'product': ['Electronics', 'Home']})

# Replace all filters with a new one
cube.filter({'customer_segment': ['Enterprise']}, is_reset=True)

# Filter in a different context state
cube.filter({'region': ['West']}, context_state_name='State1')
```

## Remove Filter

```python
remove_filter(
  dimensions: List[str],
  context_state_name: str = 'Default',
  is_reset: bool = False
) -> bool
```

Remove filters from specified dimensions.

**Parameters:**

- `dimensions`: List of dimension names to remove filters from
- `context_state_name`: Which context state to modify
- `is_reset`: Whether to reset the filter pointer for undo/redo operations

**Returns:**

- Boolean indicating success

**Example:**

```python
# Remove region filter
cube.remove_filter(['region'])
```

## Reset Filters

```python
reset_filters(
  direction: str = 'backward',
  context_state_name: str = 'Default'
) -> bool
```

Reset filters using undo/redo functionality or clear all filters.

**Parameters:**

- `direction`: 'backward' (undo), 'forward' (redo), or 'all' (clear all filters)
- `context_state_name`: Which context state to modify

**Returns:**

- Boolean indicating success

**Example:**

```python
# Undo last filter operation
cube.reset_filters('backward')

# Redo previously undone filter operation
cube.reset_filters('forward')

# Clear all filters
cube.reset_filters('all')
```

## Get Filters

```python
get_filters(
  off_set: int = 0,
  context_state_name: str = 'Default'
) -> Dict[str, List[Any]]
```

Get currently active filters.

**Parameters:**

- `off_set`: How many steps back in filter history to look
- `context_state_name`: Which context state to check

**Returns:**

- Dictionary of active filters

**Example:**

```python
# Get current filters
current_filters = cube.get_filters()
print(f"Current filters: {current_filters}")
```

## Get Filtered Dimensions

```python
get_filtered_dimensions(
  off_set: int = 0,
  context_state_name: str = 'Default'
) -> List[str]
```

Get list of currently filtered dimension names.

**Parameters:**

- `off_set`: How many steps back in filter history to look
- `context_state_name`: Which context state to check

**Returns:**

- List of dimension names that are currently filtered

**Example:**

```python
# Get list of filtered dimensions
filtered_dims = cube.get_filtered_dimensions()
print(f"Currently filtered dimensions: {filtered_dims}")
```

**Notes:**
- The special `Unfiltered` state is reserved and cannot be modified.
