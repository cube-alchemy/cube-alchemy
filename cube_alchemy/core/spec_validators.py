from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Union


def validate_keys(
    obj: Dict[str, Any],
    *,
    allowed: Iterable[str],
    required: Iterable[str] = (),
    label: str = "object",
) -> None:
    """Validate that a dict only contains allowed keys and includes required ones.

    Raises ValueError on invalid or missing keys.
    """
    allowed_set: Set[str] = set(allowed)
    required_set: Set[str] = set(required)

    extra = set(obj.keys()) - allowed_set
    if extra:
        raise ValueError(
            f"{label} contains invalid keys: {sorted(extra)}. Only {sorted(allowed_set)} allowed."
        )
    missing = required_set - set(obj.keys())
    if missing:
        raise ValueError(
            f"{label} is missing required keys: {sorted(missing)}."
        )


def ensure_list_of_str(value: Union[str, List[str]], label: str) -> List[str]:
    """Coerce a string or list of strings into a non-empty list[str]."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise TypeError(f"{label} must be a str or a list[str].")
    if len(value) == 0:
        raise ValueError(f"{label} cannot be an empty list.")
    return value


def normalize_nested(
    nested: Optional[Dict[str, Any]],
    metric_aggregation: Optional[Union[str, Callable[[Any], Any]]],
) -> Optional[Dict[str, Any]]:
    """Validate and normalize the `nested` specification.

        Accepts:
        nested = {
            'dimensions': str | list[str],               # required
            'aggregation': str | callable | None,        # optional (defaults to 'sum')
            'compose': str | callable | None             # optional, template or row->str to format inner rows
        }

    Returns a normalized dict with:
      - dimensions: list[str]
      - aggregation: str | callable | None
    or None if nested is None.
    """
    if nested is None:
        return None
    if not isinstance(nested, dict):
        raise TypeError("nested must be a dict with keys 'dimensions' and optional 'aggregation'/'compose'.")

    validate_keys(
        nested,
        allowed={"dimensions", "aggregation", "compose"},
        required={"dimensions"},
        label="nested",
    )

    dims_list = ensure_list_of_str(nested["dimensions"], "nested.dimensions")

    # Default inner aggregation to 'sum' if not provided
    inner_agg = nested.get("aggregation", "sum")
    # compose can be a format string or a callable(row)->str
    compose = nested.get("compose")
    if compose is not None and not (isinstance(compose, str) or callable(compose)):
        raise TypeError("nested.compose must be a format string or a callable(row)->str.")

    return {"dimensions": dims_list, "aggregation": inner_agg, "compose": compose}
