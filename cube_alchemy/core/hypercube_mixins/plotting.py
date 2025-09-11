from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
from cube_alchemy.plotting import PlotRenderer, MatplotlibRenderer, PlotConfigResolver, DefaultPlotConfigResolver
import copy

import time

class Plotting:
    """Component for managing plot configurations for queries."""
    def __init__(self):
        # Consolidated plotting state per query:
        # plotting_components = {
        #   query_name: { 'default': <plot_name or None>, 'plots': { <plot_name>: <plot_config> } }
        # }
        if not hasattr(self, 'plotting_components'):
            self.plotting_components: Dict[str, Dict[str, Any]] = {}
        # Default renderer
        self.plot_renderer: PlotRenderer = MatplotlibRenderer()
        # Default config resolver
        self._config_resolver: PlotConfigResolver = DefaultPlotConfigResolver()

    def define_plot(
        self,
        query_name: str,
        plot_name: Optional[str] = None,
        plot_type: Optional[str] = None,
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
    ):
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
        # include both metrics and derived metrics
        if metrics is None or len(metrics) == 0:
            mets = (qdef.get('metrics', []) or []) + (qdef.get('derived_metrics', []) or [])
        else:
            mets = metrics

        # Decide plot type: use provided one, otherwise pick the first suggestion (fallback to 'table').
        if plot_type is None:
            suggestions = self.suggest_plot_types(query_name)
            chosen_plot_type = suggestions[0]['plot_type']
        else:
            chosen_plot_type = plot_type
        
        plot_name_is_null = False
        if plot_name is None:
            plot_name = f'{chosen_plot_type} plot'
            plot_name_is_null = True

        # Create plot configuration (new schema)
        plot_config = {
            'plot_type': chosen_plot_type,
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
            'formatter': formatter,
            'annotations': annotations,
            'custom_options': (custom_options or {}),
            '_input_dimensions': dimensions, #store original user input to refresh in case of query changes after plot definition
            '_input_metrics': metrics,
        }
        
        # Ensure container for this query
        qstate = self.plotting_components.setdefault(query_name, {'default': None, 'plots': {}})
        # Store the plot configuration
        qstate['plots'][plot_name] = plot_config
        # Set as default if requested or if it's the first plot for this query
        if set_as_default or not qstate['default']:
            qstate['default'] = plot_name
        
        if plot_name_is_null:
            self.log().info("Generated plot config: %s", plot_name)

        # Register dependency: query_name -> plot
        try:
            if hasattr(self, '_dep_index') and self._dep_index is not None:
                self._dep_index.add(query_name, 'plot', plot_name)
        except Exception:
            pass

    def get_plots(self, query_name: str) -> Dict[str, Dict[str, Any]]:
        """Get all plot configurations for a query.

        Args:
            query_name: Name of the query
        """
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            self.log().warning("Query '%s' is not defined. Define it with define_query().", query_name)

        qstate = self.plotting_components.get(query_name)
        if not qstate:
            return {}
        return qstate.get('plots', {})

    def get_plot_config(self, query_name: str, plot_name: Optional[str] = None) -> Dict[str, Any]:
        """Get the plot configuration for a specific plot in a query.

        Args:
            query_name: Name of the query
            plot_name: Name of the plot (if None, get the default plot)

        Returns:
            Plot configuration dictionary
        """
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            raise ValueError(f"Query '{query_name}' is not defined.")

        qstate = self.plotting_components.get(query_name)
        if not qstate or not qstate.get('plots'):
            raise ValueError(f"Query '{query_name}' has no plot configurations.")

        if plot_name is None:
            plot_name = qstate['default']

        return qstate['plots'].get(plot_name)

    def set_default_plot(self, query_name: str, plot_name: str):
        """Set the default plot for a query.

        Args:
            query_name: Name of the query
            plot_name: Name of the plot to set as default
        """
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            self.log().warning("Query '%s' is not defined. Define it with define_query().", query_name)

        qstate = self.plotting_components.get(query_name)
        if not qstate:
            return
        qstate['default'] = plot_name

    def get_default_plot(self, query_name: str) -> Optional[str]:
        """Get the default plot for a query.

        Args:
            query_name: Name of the query            
        Returns:
            Plot configuration dictionary
        """
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            raise ValueError(f"Query '{query_name}' not defined")
        
        qstate = self.plotting_components.get(query_name)
        if not qstate or not qstate.get('plots'):
            raise ValueError(f"Query '{query_name}' has no plot configurations")

        return qstate['default']
    
    def list_plots(self, query_name: str) -> List[str]:
        """List all available plot configurations for a query.
        
        Args:
            query_name: Name of the query
            
        Returns:
            List of plot names for the query
        """
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            return []
        
        qstate = self.plotting_components.get(query_name)
        if not qstate:
            return []
        return list(qstate.get('plots', {}).keys())
    
    def _prepare_plot_data(
            self, 
            query_name: Optional[str] = None, 
            query_options: Optional[Dict[str, Any]] = None,
            plot_name: Optional[Union[str, List[str]]] = None,
            plot_type: Optional[str] = None,
            _persisted_shared_df: Optional[pd.DataFrame] = None,
            **kwargs) -> Tuple[pd.DataFrame, Union[Dict[str, Any], List[Dict[str, Any]]]]:
        
        if query_options is None and (not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {})):
            raise ValueError(f"Query '{query_name}' not defined")

        # If caller provided multiple plot names, reuse a single query result and return list of configs
        if isinstance(plot_name, list):
            # Enforce using an existing query definition (no ad-hoc options)
            if query_options is not None:
                raise ValueError("When passing a list of plot names, query_options must be None to reuse the existing query.")
            if not query_name:
                raise ValueError("When passing a list of plot names, 'query_name' must be provided.")
            if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
                raise ValueError(f"Query '{query_name}' not defined")

            # Get or reuse the DataFrame once
            if _persisted_shared_df is None:
                _, shared_df = self.query(query_name=query_name, options=None, _retrieve_query_name=True)
            else:
                shared_df = _persisted_shared_df

            configs: List[Dict[str, Any]] = []
            for pn in plot_name:
                # Reuse single-plot path for each plot name and collect configs
                _, cfg = self._prepare_plot_data(
                    query_name=query_name,
                    query_options=None,
                    plot_name=pn,
                    plot_type=plot_type,
                    _persisted_shared_df=shared_df,
                    **kwargs
                )
                configs.append(cfg)
            return shared_df, configs
        
        # Single plot: get or reuse DataFrame
        if _persisted_shared_df is None:
            query_name, plot_df = self.query(query_name=query_name, options=query_options, _retrieve_query_name=True)
        else:
            plot_df = _persisted_shared_df

        # Get plot configuration (or create a default one if not exists). We get a deep copy as it might need to change for this specific plot.
        try:
            config = self.get_plot_config(query_name, plot_name)
            config = copy.deepcopy(config) #deep copy to avoid modifying the stored default config
            # Override plot type if passed
            if plot_type is not None:
                config['plot_type'] = plot_type
        except ValueError:
            # Decide plot type: prefer explicit, else choose the first suggestion or 'table'
            if plot_type is None:
                suggestions = self.suggest_plot_types(query_name)
                chosen_plot_type = suggestions[0]['plot_type']
            else:
                chosen_plot_type = plot_type

            # No suitable config found. Auto-create one (Default or the provided name)
            if plot_name is None:
                auto_plot_name = f'Default {chosen_plot_type} < system generated >'
            else:
                auto_plot_name = f'{plot_name} {chosen_plot_type} < system generated >'

            self.define_plot(
                query_name,
                plot_name=auto_plot_name,
                plot_type=chosen_plot_type
            )
            self.log().info("Auto-generated %s plot config: %s for query %s", chosen_plot_type, auto_plot_name, query_name)
            # Now get the newly defined plot config
            config = self.get_plot_config(query_name, plot_name=auto_plot_name)
            config = copy.deepcopy(config) 

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
        mets = (q.get('metrics', []) or []) + (q.get('derived_metrics', []) or [])
        d = len(dims)
        m = len(mets)

        return self._config_resolver.suggest(d, m)

    def plot(
        self, 
        query_name: Optional[str] = None,
        query_options: Optional[Dict[str, Any]] = None,
        plot_name: Optional[Union[str, List[str]]] = None,
        plot_type: Optional[str] = None,
        renderer: Optional[PlotRenderer] = None, 
        **kwargs):
        """        
        Args:
            query_name: Name of the query to visualize
            plot_name: Name of the plot configuration (default: use the default plot)
            renderer: PlotRenderer implementation (default: use the default renderer)
            **kwargs: Additional arguments to override plot configuration or pass to the renderer.
                     Recognized: show (bool, default True) to display the figure in notebooks.
        """
        self.log().info(f"Starting plot rendering for query: {query_name}")
        t1 = time.time()
        plot_df, config_or_configs = self._prepare_plot_data(query_name, query_options, plot_name, plot_type, **kwargs)
        t2 = time.time()
        #self.log().info(f"Plot data prepared in seconds {t2 - t1}")
        rend = renderer or self.plot_renderer
        if rend is None:
            raise ValueError("Plot Rendered failed. set a default renderer with 'set_plot_renderer'.")

        # Multi-plot render: render each config with the same DataFrame
        if isinstance(config_or_configs, list):
            outputs = []
            for cfg in config_or_configs:
                outputs.append(rend.render(plot_df, cfg, **kwargs))
            return outputs

        # Single plot render
        rendered = rend.render(plot_df, config_or_configs, **kwargs)
        t3 = time.time()
        #self.log().info(f"Plot rendered in seconds {t3 - t2}")
        t_total = t3 - t1
        self.log().info(f"Plot rendering completed in seconds {t_total}")
        self.log().info(f"Proportion of time in data prep: {100 * (t2 - t1) / (t3 - t1) if (t3 - t1) > 0 else 0}")
        return rendered

    def set_plot_renderer(self, renderer: PlotRenderer):
        # Delegate to the property setter for validation
        self.plot_renderer = renderer

    def set_config_resolver(self, resolver: PlotConfigResolver):
        # Optional helper to change resolver with validation
        self._config_resolver = resolver

    def delete_plot(self, query_name: str, plot_name: str) -> None:
        """Remove a plot configuration and its dependency edge."""
        qstate = self.plotting_components.get(query_name)
        if not qstate:
            return
        if plot_name in qstate.get('plots', {}):
            qstate['plots'].pop(plot_name, None)
            if qstate.get('default') == plot_name:
                # pick another default if available
                remaining = list(qstate.get('plots', {}).keys())
                qstate['default'] = remaining[0] if remaining else None
        try:
            if hasattr(self, '_dep_index') and self._dep_index is not None:
                self._dep_index.remove_plot(plot_name)
        except Exception:
            pass