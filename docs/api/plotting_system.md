# Plotting System

Manage plot configurations per query and render via pluggable renderers.

## define_plot

```python
define_plot(
    query_name: str,
    plot_name: Optional[str] = None,
    plot_type: Optional[str] = None,
    dimensions: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
    color_by: Optional[str] = None,
    title: Optional[str] = None,
    stacked: bool = False,
    figsize: Optional[Tuple[int, int]] = None,
    orientation: str = 'vertical',
    palette: Optional[str] = None,
    sort_values: bool = False,
    sort_ascending: bool = True,
    limit: Optional[int] = None,
    formatter: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, Any]] = None,
    custom_options: Optional[Dict[str, Any]] = None,
    set_as_default: bool = True,
) -> None
```

Persist a plot configuration for a query. If plot_type is None, an appropriate type is suggested.

## get_plots

```python
get_plots(query_name: str) -> Dict[str, Dict[str, Any]]
```

Return all plot configurations for a query.

## get_plot_config

```python
get_plot_config(query_name: str, plot_name: Optional[str] = None) -> Dict[str, Any]
```

Return the configuration for a specific plot (default if None).

## set_default_plot

```python
set_default_plot(query_name: str, plot_name: str) -> None
```

Set the default plot for a query.

## get_default_plot

```python
get_default_plot(query_name: str) -> Optional[str]
```

Return the default plot name.

## list_plots

```python
list_plots(query_name: str) -> List[str]
```

List all plot names for a query.

## suggest_plot_types

```python
suggest_plot_types(query_name: str) -> List[Dict[str, Any]]
```

Suggest suitable plot types given the query’s (dimensions, metrics).

## set_plot_renderer

```python
set_plot_renderer(renderer: PlotRenderer) -> None
```

Set the default renderer.

## set_config_resolver

```python
set_config_resolver(resolver: PlotConfigResolver) -> None
```

Set the suggestion/validation resolver.

## plot

```python
plot(
    query_name: Optional[str] = None,
    query_options: Optional[Dict[str, Any]] = None,
    plot_name: Optional[Union[str, List[str]]] = None,
    plot_type: Optional[str] = None,
    renderer: Optional[PlotRenderer] = None,
    **kwargs,
) -> Any
```

Render a plot for a stored or ad‑hoc query. If plot_name is a list, returns multiple outputs using a shared query result.

## delete_plot

```python
delete_plot(query_name: str, plot_name: str) -> None
```

Remove a plot configuration and its dependency edges.

Notes:
- Dimensions/metrics default to the query definition if omitted.

- When a query is redefined, linked plot configs auto-refresh to reflect updated dims/mets.

- Plot configurations are persisted via the Model Catalog alongside metrics, queries, and transformers.
