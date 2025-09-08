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
