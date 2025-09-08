# Metric Methods

## define_metric

```python
define_metric(
    name: Optional[str] = None,
    expression: Optional[str] = None,
    aggregation: Optional[Union[str, Callable[[Any], Any]]] = None,
    metric_filters: Optional[Dict[str, Any]] = None,
    row_condition_expression: Optional[str] = None,
    context_state_name: str = 'Default',
    ignore_dimensions: Union[bool, List[str]] = False,
    ignore_context_filters: Union[bool, List[str]] = False,
    fillna: Optional[Any] = None,
    nested: Optional[Dict[str, Any]] = None,
) -> None
```

Persist a base metric for later use in queries.

Parameters:
- name: Label of the resulting column.

- expression: Formula using [column] references and optional @functions.

- aggregation: Pandas aggregation name or callable; aliases like avg, count_distinct supported.

- metric_filters: Filters applied only when evaluating this metric.

- row_condition_expression: Row filter (DataFrame.query style; use [col] references).

- context_state_name: Context state to read from.

- ignore_dimensions: True for grand total, list[str] to ignore specific dims, or False.

- ignore_context_filters: True to ignore all context filters, list[str] to ignore specific ones, or False.

- fillna: Single value to fill NA on referenced columns before evaluation.

- nested: Dict with keys: dimensions (str|list[str]); aggregation (str|callable, default 'sum'); compose (str template or callable(row)->str).

Notes:
- Column references must use square brackets: [qty], [price], ...

- Aggregation accepts pandas names, callables, lists/tuples/dicts, and common aliases.

## define_derived_metric

```python
define_derived_metric(
    name: str,
    expression: str,
    fillna: Optional[Any] = None
) -> None
```

Persist a post-aggregation derived metric computed from aggregated columns (metrics or dimensions).

Parameters:
- name: Result column label.

- expression: Formula using [MetricName] and/or [Dimension] references.

- fillna: Optional value to temporarily fill NA on referenced columns during evaluation.
