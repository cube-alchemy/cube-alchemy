# Plotting System

Cube Alchemy includes a flexible plotting system that allows you to visualize query results using any visualization framework of your choice.

## Conceptual Overview

The plotting system in Cube Alchemy follows a clean separation of concerns:

1. **Query Definition**: Defines what data to fetch from your hypercube
2. **Plot Configuration**: Defines how to visualize that data (stored separately from queries)
3. **Renderer Interface**: Defines how to translate data and configuration into a visual representation

This separation allows Cube Alchemy to remain framework-agnostic while providing powerful visualization capabilities that can be extended to work with any visualization library or framework.

### What is an Interface?

In programming, an interface is like a contract that defines what methods a class must implement, but not how those methods are implemented. In the context of Cube Alchemy's plotting system:

- The `PlotRenderer` interface defines a common way to render plots
- Specific renderers (like a Streamlit renderer or a Matplotlib renderer) implement this interface
- This allows the Hypercube to work with any renderer without knowing its implementation details

This design follows the "dependency inversion principle" - the core hypercube doesn't depend on specific visualization frameworks, but rather on abstractions (interfaces).

## Why It's Separate from the Core Hypercube

The plotting system is deliberately separate from the core Hypercube functionality for several reasons:

1. **Modularity**: Keep data processing separate from visualization concerns
2. **Framework Independence**: Allow Cube Alchemy to work with any visualization library
3. **Lighter Core**: Users who don't need visualization don't have to load visualization dependencies
4. **Flexibility**: Users can create custom renderers for their specific needs
5. **Maintainability**: Visualization libraries evolve separately from data processing needs

When you import and use Cube Alchemy's Hypercube, you don't automatically import visualization dependencies, keeping your application lightweight. You only need to import renderers when you're ready to visualize data.

## Using the Plotting System

### 1. Define Query and Plot Configurations

Plot configurations are associated with queries but stored separately from the query definition, allowing multiple visualizations for the same data and easy reuse:

```python
# Define a query first (dimensions/metrics)
cube.define_query(name="sales_by_region", dimensions=["region"], metrics=["total_sales"])

# Define default plot configuration
cube.define_plot(
    query_name="sales_by_region",
    plot_name="Default",
    plot_type="bar",
    dimensions=["region"],
    metrics=["total_sales"],
    orientation="vertical",
    title="Sales by Region"
)

# Define an alternative plot configuration
cube.define_plot(
    query_name="sales_by_region",
    plot_name="horizontal_bars",
    plot_type="bar",
    dimensions=["region"],
    metrics=["total_sales"],
    orientation="horizontal",
    title="Sales by Region (Horizontal)",
    sort_values=True,
    set_as_default=False  # Don't make this the default
)
```

### 2. Create a Renderer

Create a renderer that implements the `PlotRenderer` interface:

```python
from cube_alchemy.plotting import PlotRenderer
import matplotlib.pyplot as plt

class MatplotlibRenderer(PlotRenderer):
    def render(self, data, plot_config, **kwargs):
        # Create figure
        fig, ax = plt.subplots(figsize=plot_config.get("figsize", (10, 6)))
        
        # Extract plot configuration (dimensions/metrics)
        dims = plot_config.get("dimensions") or []
        mets = plot_config.get("metrics") or []
        title = plot_config.get("title", "")
        
        # Simple example: single-metric vertical bar
        labels = data[dims].astype(str).agg(' | '.join, axis=1) if dims else data.index.astype(str)
        metric = mets[0]
        ax.bar(labels, data[metric])
        ax.set_title(title)
        ax.tick_params(axis='x', rotation=45)
        return fig
```

### 3. Plot Your Data

Use the renderer with any plot configuration:

```python
# Create an instance of your renderer
renderer = MatplotlibRenderer()

# Use the default plot configuration
cube.plot("sales_by_region", renderer=renderer)

# Or use a specific plot configuration
cube.plot("sales_by_region", plot_name="horizontal_bars", renderer=renderer)

# Or override configuration properties
cube.plot(
    "sales_by_region", 
    renderer=renderer, 
    metrics=["average_sales"],  # Use a different metric
    title="Average Sales by Region"  # Custom title
)
```

## API Reference

### PlotRenderer Interface

Base class that all renderers must implement:

```python
class PlotRenderer(ABC):
    @abstractmethod
    def render(self, 
               data: pd.DataFrame, 
               plot_config: Dict[str, Any],
               **kwargs) -> Any:
        """
        Render the plot using the given data and configuration.
        
        Args:
            data: DataFrame containing the data to plot
            plot_config: Dictionary with plot configuration
            **kwargs: Additional keyword arguments for the renderer
            
        Returns:
            The rendered plot object (framework-specific)
        """
        pass
```

### PlottingComponents Methods

These methods are mixed into the Hypercube class:

#### define_plot

```python
def define_plot(
    self,
    query_name: str,
    plot_name: str = "Default",
    plot_type: str = "bar",
    dimensions: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
    color_by: Optional[str] = None,
    title: Optional[str] = None,
    stacked: bool = False,
    figsize: Optional[Tuple[int, int]] = None,
    orientation: str = "vertical",
    palette: Optional[str] = None,
    sort_values: bool = False,
    sort_ascending: bool = True,
    limit: Optional[int] = None,
    formatter: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, Any]] = None,
    custom_options: Optional[Dict[str, Any]] = None,
    set_as_default: bool = True,
) -> "PlottingComponents":
    """Define a plot configuration for a query."""
    # Implementation details...
```

#### set_default_plot

```python
def set_default_plot(self, query_name: str, plot_name: str) -> "PlottingComponents":
    """Set the default plot for a query."""
    # Implementation details...
```

#### get_plot_config

```python
def get_plot_config(self, query_name: str, plot_name: Optional[str] = None) -> Dict[str, Any]:
    """Get the plot configuration for a query."""
    # Implementation details...
```

#### list_plots

```python
def list_plots(self, query_name: str) -> List[str]:
    """List all available plot configurations for a query."""
    # Implementation details...
```

#### plot

```python
def plot(self, query_name: str, renderer: PlotRenderer, 
         plot_name: Optional[str] = None, **kwargs):
    """Plot the results of a query using a provided renderer."""
    # Implementation details...
```

## Available Renderers

### Built-in Renderers

Cube Alchemy provides a few built-in renderers that you can use immediately:

- `MatplotlibRenderer`: For static plots using Matplotlib
- `StreamlitRenderer`: For interactive plots in Streamlit applications

### Creating Custom Renderers

You can create custom renderers for any visualization framework by implementing the `PlotRenderer` interface. Examples include:

- Plotly renderer for interactive plots
- Bokeh renderer for interactive web visualizations  
- Seaborn renderer for statistical visualizations
- D3.js renderer for web-based visualizations

## Examples

Check out the [examples folder](https://github.com/cube-alchemy/cube-alchemy-examples) for complete examples using different renderers with Cube Alchemy.

## Persisting Plot Configurations

Plot configurations can be saved/loaded with the Model Catalog (YAML-backed by default). See API: Model Catalog for how plots are serialized alongside metrics, queries, and computed metrics.
