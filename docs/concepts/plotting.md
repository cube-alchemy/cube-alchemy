# Plotting System

Cube Alchemy includes a flexible plotting system that allows you to visualize your query results with any visualization framework of your choice.

The plotting system is a framework-agnostic approach to visualizing data from your hypercube. It separates:

- **What data to show** (from your queries)

- **How to configure the visualization** (plot configurations)

- **How to render the visualization** (through renderer interfaces)

## Core Components

### Plot Configurations

Plot configurations are stored within queries and define how data should be visualized:

```python
# Define the query with dimensions and metrics
cube.define_query(
    name="sales analysis",
    dimensions=["region"],
    metrics=["revenue"],
)

cube.define_plot(
    query_name="sales analysis",
    plot_name="simple_bar",
    plot_type="bar",
    #dimensions=["region"],
    #metrics=["revenue"],
    orientation="horizontal",
    sort_values=True,
    title="Revenue by Region" # if ommited, it will be the query name
)

# cube.set_plot_renderer(MyRenderer()) # If you want to set up a customer renderer. See Plot Renders below

# Use it with default plot configuration
cube.plot('sales analysis')

```

### Plot configuration parameters

The plotting interface accepts a rich set of configuration parameters. Below is the full list used by the current implementation, with short descriptions and default values:

- query_name: str
    - The name of the query this plot config belongs to. (required)
- plot_name: Optional[str] = None
    - A name for the plot configuration. If omitted, a name will be inferred.
- plot_type: Optional[str] = None
    - Type of visualization (e.g., 'bar', 'line', 'area', 'table', 'heatmap'). Renderer-specific handlers may accept custom types.
- dimensions: Optional[List[str]] = None
    - Override the query dimensions for this plot. Provide a list of column names. If not passed all the query dimensions will be used.
- metrics: Optional[List[str]] = None
    - Override the query metrics for this plot. Provide a list of metric names. If not passed all the query metrics and derived metrics will be used.
- color_by: Optional[str] = None
    - Column (dimension or metric) used to color lines/bars/categories.
- title: Optional[str] = None
    - Plot title. If omitted, the query or plot name is used.
- stacked: bool = False
    - For area/bar charts, whether series should be stacked.
- figsize: Optional[Tuple[int, int]] = None
    - Figure size in inches as (width, height). If None, renderer defaults are used.
- orientation: str = "vertical"
    - 'vertical' or 'horizontal' orientation for bar-like charts.
- palette: Optional[str] = None
    - Color palette name or list accepted by the renderer.
- sort_values: bool = False
    - Whether to sort rows before plotting.
- sort_ascending: Union[bool, List[bool]] = True
    - Sort direction(s). Can be a single bool or a list aligned with `sort_by`.
- sort_by: Optional[Union[str, List[str], Tuple[str, ...], List[Tuple[str, ...]]]] = None
    - Column(s) to sort by. Accepts a string, list of strings, or tuple(s) for composite sort keys.
- pivot: Optional[Union[str, List[str]]] = None
    - Pivot the data on the given column(s) before rendering (e.g., create a wide table from long data).
- limit: Optional[int] = None
    - Limit the number of rows (e.g., top-N) after sorting.
- formatter: Optional[Dict[str, str]] = None
    - Mapping of column name -> format string (e.g., { 'revenue': '0.2f', 'date': '%Y-%m' }). Used when rendering text values.
- legend_position: Optional[str] = None
    - Position for the legend (e.g., 'best', 'upper right', 'bottom'). Renderer-dependent.
- annotations: Optional[Dict[str, Any]] = None
    - Annotation options passed to the renderer (e.g., {'show_values': True, 'format': '0.0f'}).
- custom_options: Optional[Dict[str, Any]] = None
    - Arbitrary renderer-specific options. Useful for passing through parameters not supported by the core.
- hide_index: bool = False
    - Hide index labels/axis when rendering tables or DataFrame-like outputs.
- row_color_condition: Optional[str] = None
    - A boolean expression (using column names) that determines which rows get special coloring (e.g., '[revenue] > 10000').
- row_colors: Optional[Dict[str, str]] = None
    - Mapping of value -> color for row-level coloring when `row_color_condition` or categorical coloring is used.
- set_as_default: bool = True
    - If True, mark this plot configuration as the default for the query.

Example usage:

```python
cube.define_plot(
        query_name='sales analysis',
        plot_name='top_regions',
        plot_type='bar',
        dimensions=['region'],
        metrics=['revenue'],
        title='Top Regions by Revenue',
        stacked=False,
        figsize=(10, 6),
        orientation='vertical',
        sort_values=True,
        sort_by='revenue',
        limit=10,
        palette='tab10',
        set_as_default=True
)
```

Each query can have multiple plot configurations with one designated as the default.

### Plot Renderers

Renderers are responsible for creating the visualization based on the data and plot configuration. They implement a common interface:

```python
from cube_alchemy.plot_renderer import PlotRenderer

class MyRenderer(PlotRenderer):
    def render(self, data, plot_config, **kwargs):
        # Create and return a visualization using the data and configuration
```

This design allows Cube Alchemy to integrate with any visualization framework in python including:

- Matplotlib (set as Default, thought it could be a brand new one designed)

- Streamlit

- Plotly

- Etc

### Registering a Custom Plot

You can add new plot types at runtime. The simplest handler accepts only a DataFrame; the renderer also supports richer signatures.

```python
def custom_render(df, dims, mets):
    print("dims:", dims)
    print("mets:", mets)
    print(df)

cube.plot_renderer.register_plot("custom", custom_render) ## This will work on the default Matplotlib Renderer, it adds a new rendering function to it which can be called for all plot_types = custom

cube.plot('Your Query', plot_type="custom")

## Or use a brand new renderer that knows how to render the plot_type = custom
my_renderer = CustomRenderer()
cube.plot('Your Query', renderer = my_renderer, plot_type="custom")

# Note: register_plot() is not part of PlotRenderer (ABC) but a special method for the Default MatplotlibRenderer installed with the Hypercube. If you use custom a renderer it will not be there.
```

Notes:

- Registration is per Python run; call it during startup or from a module that’s imported early.

- The same `plot_type` name will override an existing handler.

## Why a Separate Interface?

The plotting layer is separate from the core so you can:

- Keep data and visualization concerns independent
- Swap visualization frameworks without touching core logic
- Evolve as libraries change without core refactors
- Skip extra dependencies when visualization isn't needed

You can always plot DataFrames directly. Using the plotting interface (renderers and plot configurations) keeps things organized, improves readability and maintainability, and makes updates or framework switches easier.

## Default and Custom Plot Renderers

Cube Alchemy includes a built-in Matplotlib renderer that is used by default. It works well in Jupyter notebooks and can also render charts inside Streamlit apps.

When the plotting system calls a renderer it provides the prepared DataFrame and the complete plot configuration. The renderer decides which configuration fields to apply (for example: title, figsize, palette, annotations, etc.). Custom renderers should accept the data and config and use the keys they need; any unused keys can be ignored.

A Streamlit renderer is included as a convenience example. Rendering is intentionally separated from the core: renderers can be extended or replaced without changing core functionality Ideally all but the default renderer will live on it's own project/repo in the future.
