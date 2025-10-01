# Filter Methods

## filter

```python
filter(
  criteria: Dict[str, List[Any]], 
  context_state_name: str = 'Default',
  is_reset: bool = False,
  save_state: bool = True,
) -> bool
```

Apply filters to a context state. Returns True on success.

## remove_filter

```python
remove_filter(
  dimensions: List[str],
  context_state_name: str = 'Default',
  is_reset: bool = False,
) -> bool
```

Remove filters for the specified dimensions from a context state.

## reset_filters

```python
reset_filters(
  direction: str = 'backward',
  context_state_name: str = 'Default'
) -> bool
```

Reset filters using undo/redo or clear all filters. Direction: 'backward', 'forward', or 'all'.

## get_filters

```python
get_filters(
  off_set: int = 0,
  context_state_name: str = 'Default'
) -> Dict[str, List[Any]]
```

Return the aggregated active filters up to the current history pointer plus off_set.

## get_filtered_dimensions

```python
get_filtered_dimensions(
  off_set: int = 0,
  context_state_name: str = 'Default'
) -> List[str]
```

Return only the dimension names that are currently filtered (order preserved, no duplicates).

## set_context_state

```python
set_context_state(
  context_state_name: str,
  base_context_state_name: str = 'Unfiltered'
) -> bool
```

Create a new context state cloned from base_context_state_name.

Notes:
- When creating a new context state, the implementation initializes `applied_filters[context_state_name]` as an empty list and sets `filter_pointer[context_state_name]` to 0. The new context is a copy of the specified base context state.
