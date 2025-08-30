from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
from cube_alchemy.plot_renderer import PlotRenderer

class PlottingComponents:
    """Component for managing plot configurations for queries."""
    def __init__(self):
        # Structure: {query_name: {plot_name: plot_config}}
        if not hasattr(self, 'plot_configs'):
            self.plot_configs: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # Default plot name for each query
        if not hasattr(self, 'default_plots'):
            self.default_plots: Dict[str, str] = {}
    # Default renderer (initially None - must be set with set_plot_renderer)
        self.plot_renderer = None

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
        secondary_y: Optional[List[str]] = None,
        formatter: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, Any]] = None,
        custom_options: Optional[Dict[str, Any]] = None,
        set_as_default: bool = True,
    ) -> "PlottingComponents":
        """Define a plot configuration for a query.
        
        Args:
            query_name: Name of the query to visualize
            plot_name: Name of this plot configuration (default: "Default")
            plot_type: Type of plot (bar, line, scatter, pie, area, heatmap, table)
            dimensions: Dimensions to use
            metrics: Metrics to use
            color_by: Column to group/color by (default: none)
            title: Plot title (default: query_name)
            stacked: Whether to stack bars in bar chart
            figsize: Figure size as (width, height) tuple
            orientation: "vertical" or "horizontal" for bar charts
            palette: Color palette name
            sort_values: Whether to sort values
            sort_ascending: Sort order if sort_values is True
            limit: Limit number of items to show
            secondary_y: List of metrics to plot on secondary y-axis
            formatter: Dictionary mapping column names to format strings
            annotations: Custom annotations for the plot
            custom_options: Additional framework-specific options
            set_as_default: Whether to set this as the default plot for the query
        """
        # Check if the query exists
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            raise ValueError(f"Query '{query_name}' not defined")

        # Derive dimensions/metrics from query if not provided
        qdef = self.queries[query_name]
        if dimensions is None or len(dimensions) == 0:
            dims = qdef.get('dimensions', []) or []
        else:
            dims = dimensions
        # include both metrics and computed metrics
        if metrics is None or len(metrics) == 0:
            mets = (qdef.get('metrics', []) or []) + (qdef.get('computed_metrics', []) or [])
        else:
            mets = metrics

        # Create plot configuration (new schema)
        plot_config = {
            'plot_type': plot_type,
            'dimensions': dims,
            'metrics': mets,
            'color_by': color_by,
            'title': title or query_name,
            'stacked': stacked,
            'figsize': figsize,
            'orientation': orientation,
            'palette': palette,
            'sort_values': sort_values,
            'sort_ascending': sort_ascending,
            'limit': limit,
            'secondary_y': secondary_y,
            'formatter': formatter,
            'annotations': annotations,
            'custom_options': custom_options or {},
            '_input_dimensions': dimensions, #store original user input to refresh in case of query changes after plot definition
            '_input_metrics': metrics,
        }
        
        # Initialize plot_configs for this query if not exists
        if query_name not in self.plot_configs:
            self.plot_configs[query_name] = {}
        
        # Store the plot configuration
        self.plot_configs[query_name][plot_name] = plot_config
        
        # Set as default if requested or if it's the first plot for this query
        if set_as_default or query_name not in self.default_plots:
            self.default_plots[query_name] = plot_name
        
        return self
    
    def set_default_plot(self, query_name: str, plot_name: str) -> "PlottingComponents":
        """Set the default plot for a query.
        
        Args:
            query_name: Name of the query
            plot_name: Name of the plot to set as default
        """
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            raise ValueError(f"Query '{query_name}' not defined")
        
        if query_name not in self.plot_configs or plot_name not in self.plot_configs[query_name]:
            raise ValueError(f"Plot '{plot_name}' not found for query '{query_name}'")
        
        self.default_plots[query_name] = plot_name
        return self
    
    def get_plot_config(self, query_name: str, plot_name: Optional[str] = None) -> Dict[str, Any]:
        """Get the plot configuration for a query.
        
        Args:
            query_name: Name of the query
            plot_name: Name of the plot configuration (default: use the default plot)
            
        Returns:
            Plot configuration dictionary
        """
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            raise ValueError(f"Query '{query_name}' not defined")
        
        if query_name not in self.plot_configs:
            raise ValueError(f"Query '{query_name}' has no plot configurations")
        
        # Use specified plot_name or the default
        if plot_name is None:
            plot_name = self.default_plots.get(query_name)
            if plot_name is None:
                raise ValueError(f"No default plot defined for query '{query_name}'")
        
        if plot_name not in self.plot_configs[query_name]:
            raise ValueError(f"Plot '{plot_name}' not found for query '{query_name}'")
        
        return self.plot_configs[query_name][plot_name]
    
    def list_plots(self, query_name: str) -> List[str]:
        """List all available plot configurations for a query.
        
        Args:
            query_name: Name of the query
            
        Returns:
            List of plot names for the query
        """
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            return []
        
        if query_name not in self.plot_configs:
            return []
        
        return list(self.plot_configs[query_name].keys())
    
    def prepare_plot_data(self, query_name: str, plot_name: Optional[str] = None, 
                         **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Prepare data for plotting by applying the plot configuration.
        
        Args:
            query_name: Name of the query to prepare data for
            plot_name: Name of the plot configuration (default: use the default plot)
            **kwargs: Override plot configuration parameters
            
        Returns:
            Tuple of (prepared data, plot config)
        """
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            raise ValueError(f"Query '{query_name}' not defined")
            
        # Get the query result
        plot_df = self.query(query_name)
        
        # Get plot configuration (or create a default one if not exists)
        try:
            config = self.get_plot_config(query_name, plot_name).copy()
        except ValueError:
            if plot_name == None:
                print("No plot name specified, using default bar chart")
            else:
                print(f"Plot '{plot_name}' not found for query '{query_name}'. Using default bar chart.")
            # Auto-create a default config based on query definition
            query_def = self.queries[query_name]
            dimensions = query_def.get('dimensions', []) or []
            metrics = (query_def.get('metrics', []) or []) + (query_def.get('computed_metrics', []) or [])
            
            config = {
                'plot_type': 'bar',
                'dimensions': dimensions,
                'metrics': metrics,
                'title': query_name
            }
        
        # Override config with kwargs (only known keys)
        for k, v in kwargs.items():
            if k in config:
                config[k] = v
        # Also accept direct overrides for dimensions/metrics
        if 'dimensions' in kwargs:
            config['dimensions'] = kwargs['dimensions']
        if 'metrics' in kwargs:
            config['metrics'] = kwargs['metrics']
        
        # Sort if requested (single-metric convenience only)
        mets = config.get('metrics') or []
        if config.get('sort_values', False) and isinstance(mets, list) and len(mets) == 1:
            metric_to_sort = mets[0]
            if metric_to_sort in plot_df.columns:
                plot_df = plot_df.sort_values(
                    by=metric_to_sort,
                    ascending=config.get('sort_ascending', True)
                )
        
        # Limit rows if requested
        limit = config.get('limit')
        if limit is not None:
            plot_df = plot_df.head(limit)
        
        return plot_df, config

    def suggest_plot_types(self, query_name: str) -> List[Dict[str, Any]]:
        """Suggest available plot types based on query's dimensions and metrics.

        Returns a list of suggestion dictionaries like:
        { 'plot_type': 'bar', 'description': 'One dimension, one metric', 'options': {'stacked': False}}
        """
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            raise ValueError(f"Query '{query_name}' not defined")

        q = self.queries[query_name]
        dims = q.get('dimensions', []) or []
        mets = (q.get('metrics', []) or []) + (q.get('computed_metrics', []) or [])
        d = len(dims)
        m = len(mets)

        suggestions: List[Dict[str, Any]] = []
        if d >= 1 and m >= 1:
            # One dimension, one or more metrics
            suggestions.append({'plot_type': 'bar', 'description': 'Bar chart', 'options': {}})
            suggestions.append({'plot_type': 'line', 'description': 'Line chart', 'options': {}})
            suggestions.append({'plot_type': 'area', 'description': 'Area chart', 'options': {}})
        if d >= 2 and m >= 1:
            # Two dimensions for grouping
            suggestions.append({'plot_type': 'bar', 'description': 'Grouped bars (2nd dimension as groups)', 'options': {'stacked': False}})
            suggestions.append({'plot_type': 'bar', 'description': 'Stacked bars (2nd dimension as stacks)', 'options': {'stacked': True}})

        return suggestions

    def plot(self, query_name: str, plot_name: Optional[str] = None, renderer: Optional[PlotRenderer] = None, **kwargs):
        """
        Plot the results of a query using a provided renderer.
        
        Args:
            query_name: Name of the query to visualize
            plot_name: Name of the plot configuration (default: use the default plot)
            renderer: PlotRenderer implementation (default: use the default renderer)
            **kwargs: Additional arguments to override plot configuration or pass to the renderer
            
        Returns:
            Whatever the renderer returns
            
        Raises:
            ValueError: If no renderer is provided and no default renderer is set
        """
        plot_df, config = self.prepare_plot_data(query_name, plot_name, **kwargs)
        if renderer is not None:
            return renderer.render(plot_df, config, **kwargs)
        elif self.plot_renderer is not None: #Use default renderer set to Hypercube
            return self.plot_renderer.render(plot_df, config, **kwargs)
        else:
            raise ValueError("No plot renderer provided. Use the 'renderer' parameter or set a default renderer with 'set_plot_renderer'.")

    def set_plot_renderer(self, renderer: PlotRenderer):
        """
        Set the plot renderer to be used for visualizations.

        Args:
            renderer: An instance of a PlotRenderer implementation
        """
        self.plot_renderer = renderer