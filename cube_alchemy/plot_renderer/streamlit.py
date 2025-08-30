import pandas as pd
from typing import Dict, Any
from .abc import PlotRenderer

# Define StreamlitRenderer
class StreamlitRenderer(PlotRenderer):
    """
    Streamlit implementation of the PlotRenderer interface.
    
    This renderer uses Streamlit's native chart components when possible,
    and falls back to matplotlib when needed.
    """
    
    def render(self, data: pd.DataFrame, plot_config: Dict[str, Any], **kwargs):
        """
        Render a plot using Streamlit's native chart components.

        Args:
            data: DataFrame containing the data to plot
            plot_config: Dictionary with plot configuration including:
                - plot_type: Type of plot (bar, line, scatter, etc.)
                - dimensions: List[str]
                - metrics: List[str]
                - color_by: Column to group/color by (optional)
                - title: Plot title
                - orientation: "vertical" or "horizontal" (for bar charts)
                - sort_values: Whether to sort values
                - sort_ascending: Sort order
                - limit: Limit number of items
            **kwargs: Additional options like:
                - use_container_width: Whether to use container width
                - height: Height of the plot

        Returns:
            None (Streamlit displays the plot directly)
        """
        import streamlit as st
        import matplotlib.pyplot as plt

        # Get options with defaults
        plot_type = plot_config.get('plot_type', 'bar').lower()
        # Use schema: dimensions/metrics
        dims = plot_config.get('dimensions') or []
        mets = plot_config.get('metrics') or []
        color_by = plot_config.get('color_by')
        title = plot_config.get('title')
        orientation = plot_config.get('orientation', 'vertical')
        sort_values = plot_config.get('sort_values', False)
        sort_ascending = plot_config.get('sort_ascending', True)
        limit = plot_config.get('limit')
        use_container_width = kwargs.get('use_container_width', True)
        height = kwargs.get('height', 400)

        # Prepare data
        plot_df = data.copy()

        # Sort if requested (only when a single metric is present)
        if sort_values and isinstance(mets, list) and len(mets) == 1 and mets[0] in plot_df.columns:
            plot_df = plot_df.sort_values(by=mets[0], ascending=sort_ascending)

        # Limit rows if requested
        if limit is not None:
            plot_df = plot_df.head(limit)

        # Display title if provided
        if title:
            st.subheader(title)

        # Render based on plot type
        if plot_type == 'bar':
            self._render_bar_chart(plot_df, dims, mets, color_by,
                                   orientation, height, use_container_width)
        elif plot_type == 'line':
            self._render_line_chart(plot_df, dims, mets, color_by,
                                    height, use_container_width)
        elif plot_type == 'area':
            self._render_area_chart(plot_df, dims, mets, color_by,
                                    height, use_container_width)
        else:
            # For other types, use matplotlib through st.pyplot
            self._render_matplotlib_fallback(plot_df, plot_config)
    
    def _render_bar_chart(self, df, dims, mets, color_by, 
                         orientation, height, use_container_width):
        """Render a bar chart using Streamlit's bar_chart respecting dimensions/metrics lists."""
        import streamlit as st
        import pandas as pd
        
        # Build a category label from all dimensions to avoid implicit axis choices
        if dims:
            cat_series = df[dims].astype(str).agg(' | '.join, axis=1)
        else:
            # Single bucket
            cat_series = pd.Series(['All'] * len(df), index=df.index)
        df = df.copy()
        df['__category__'] = cat_series
        
        # Orientation handling: horizontal may require matplotlib
        horizontal = orientation == 'horizontal'

        # Single metric fast-path
        if isinstance(mets, list) and len(mets) == 1 and mets[0] in df.columns and not horizontal:
            metric = mets[0]
            if color_by and color_by in df.columns:
                pivot_df = df.pivot_table(index='__category__', columns=color_by, values=metric, aggfunc='first').fillna(0)
                st.bar_chart(pivot_df, height=height, use_container_width=use_container_width)
            else:
                st.bar_chart(df.set_index('__category__')[metric], height=height, use_container_width=use_container_width)
            return

        # Multi-metric or horizontal: melt and pivot to series columns
        value_vars = [m for m in mets if m in df.columns]
        if not value_vars:
            st.write('No metrics to plot.')
            return
        long_df = df.melt(id_vars=['__category__'] + ([color_by] if color_by and color_by in df.columns else []),
                          value_vars=value_vars, var_name='__metric__', value_name='__value__')
        if color_by and color_by in df.columns:
            long_df['__series__'] = long_df[color_by].astype(str) + ' • ' + long_df['__metric__']
        else:
            long_df['__series__'] = long_df['__metric__']
        pivot_df = long_df.pivot_table(index='__category__', columns='__series__', values='__value__', aggfunc='first').fillna(0)
        if horizontal:
            # For horizontal bars, use matplotlib for correct orientation
            self._render_horizontal_grouped_bars_from_pivot(pivot_df)
        else:
            st.bar_chart(pivot_df, height=height, use_container_width=use_container_width)
    
    def _render_line_chart(self, df, dims, mets, color_by, height, use_container_width):
        """Render a line chart using Streamlit's line_chart respecting dimensions/metrics lists."""
        import streamlit as st
        import pandas as pd
        # Build category label from all dimensions
        if dims:
            cat_series = df[dims].astype(str).agg(' | '.join, axis=1)
        else:
            cat_series = pd.Series(['All'] * len(df), index=df.index)
        df = df.copy()
        df['__category__'] = cat_series

        # Single metric fast-path
        if isinstance(mets, list) and len(mets) == 1 and mets[0] in df.columns:
            metric = mets[0]
            if color_by and color_by in df.columns:
                pivot_df = df.pivot_table(index='__category__', columns=color_by, values=metric, aggfunc='first').fillna(0)
                st.line_chart(pivot_df, height=height, use_container_width=use_container_width)
            else:
                st.line_chart(df.set_index('__category__')[metric], height=height, use_container_width=use_container_width)
            return

        # Multi-metric: melt and pivot to series columns
        value_vars = [m for m in mets if m in df.columns]
        if not value_vars:
            st.write('No metrics to plot.')
            return
        long_df = df.melt(id_vars=['__category__'] + ([color_by] if color_by and color_by in df.columns else []),
                          value_vars=value_vars, var_name='__metric__', value_name='__value__')
        if color_by and color_by in df.columns:
            long_df['__series__'] = long_df[color_by].astype(str) + ' • ' + long_df['__metric__']
        else:
            long_df['__series__'] = long_df['__metric__']
        pivot_df = long_df.pivot_table(index='__category__', columns='__series__', values='__value__', aggfunc='first').fillna(0)
        st.line_chart(pivot_df, height=height, use_container_width=use_container_width)
    
    def _render_area_chart(self, df, dims, mets, color_by, height, use_container_width):
        """Render an area chart using Streamlit's area_chart respecting dimensions/metrics lists."""
        import streamlit as st
        import pandas as pd
        # Build category label from all dimensions
        if dims:
            cat_series = df[dims].astype(str).agg(' | '.join, axis=1)
        else:
            cat_series = pd.Series(['All'] * len(df), index=df.index)
        df = df.copy()
        df['__category__'] = cat_series

        # Single metric fast-path
        if isinstance(mets, list) and len(mets) == 1 and mets[0] in df.columns:
            metric = mets[0]
            if color_by and color_by in df.columns:
                pivot_df = df.pivot_table(index='__category__', columns=color_by, values=metric, aggfunc='first').fillna(0)
                st.area_chart(pivot_df, height=height, use_container_width=use_container_width)
            else:
                st.area_chart(df.set_index('__category__')[metric], height=height, use_container_width=use_container_width)
            return

        # Multi-metric: melt and pivot to series columns
        value_vars = [m for m in mets if m in df.columns]
        if not value_vars:
            st.write('No metrics to plot.')
            return
        long_df = df.melt(id_vars=['__category__'] + ([color_by] if color_by and color_by in df.columns else []),
                          value_vars=value_vars, var_name='__metric__', value_name='__value__')
        if color_by and color_by in df.columns:
            long_df['__series__'] = long_df[color_by].astype(str) + ' • ' + long_df['__metric__']
        else:
            long_df['__series__'] = long_df['__metric__']
        pivot_df = long_df.pivot_table(index='__category__', columns='__series__', values='__value__', aggfunc='first').fillna(0)
        st.area_chart(pivot_df, height=height, use_container_width=use_container_width)
    
    def _render_horizontal_grouped_bars_from_pivot(self, pivot_df):
        """Render horizontal grouped bar chart using matplotlib from a pivoted DataFrame."""
        import streamlit as st
        import matplotlib.pyplot as plt
        import numpy as np
        
        # Create matplotlib figure and axes
        fig, ax = plt.subplots(figsize=(10, len(pivot_df) * 0.5 + 2))
        
        # Get dimensions for plotting
        categories = pivot_df.index.tolist()
        group_names = pivot_df.columns.tolist()
        values = pivot_df.values
        
        # Set up positions for bars
        y_pos = np.arange(len(categories))
        bar_height = 0.8 / len(group_names)
        
        # Plot each group
        for i, group in enumerate(group_names):
            pos = y_pos - 0.4 + (i + 0.5) * bar_height
            ax.barh(pos, pivot_df[group], height=bar_height, label=group)
        
        # Set labels and legend
        ax.set_yticks(y_pos)
        ax.set_yticklabels(categories)
        ax.legend()
        
        st.pyplot(fig)
    
    def _render_matplotlib_fallback(self, df, plot_config):
        """Fallback to matplotlib for plot types not supported by Streamlit."""
        import streamlit as st
        import matplotlib.pyplot as plt

        # Get configuration options
        plot_type = plot_config.get('plot_type', 'bar').lower()
        dims = plot_config.get('dimensions') or []
        mets = plot_config.get('metrics') or []
        color_by = plot_config.get('color_by')
        title = plot_config.get('title')
        figsize = plot_config.get('figsize', (10, 6))

        # Create figure
        fig, ax = plt.subplots(figsize=figsize)
        
        # Render based on plot type
        if plot_type == 'scatter':
            # Use two metrics if available; else fall back to first dimension + first metric
            if len(mets) >= 2 and mets[0] in df.columns and mets[1] in df.columns:
                x_col, y_col = mets[0], mets[1]
            elif len(mets) >= 1 and len(dims) >= 1 and mets[0] in df.columns and dims[0] in df.columns:
                x_col, y_col = dims[0], mets[0]
            else:
                st.write('Scatter plot requires at least two numeric columns.')
                st.pyplot(fig)
                return
            if color_by and color_by in df.columns:
                for name, group in df.groupby(color_by):
                    ax.scatter(group[x_col], group[y_col], label=name, alpha=0.7)
                ax.legend(title=color_by)
            else:
                ax.scatter(df[x_col], df[y_col])
                
        elif plot_type == 'pie':
            # Combine all dimensions as labels; require a single metric
            import pandas as pd
            labels = df[dims].astype(str).agg(' | '.join, axis=1) if dims else df.index.astype(str)
            if len(mets) >= 1 and mets[0] in df.columns:
                ax.pie(df[mets[0]], labels=labels, autopct='%1.1f%%')
            else:
                st.write('Pie chart requires one metric.')
            
        elif plot_type == 'heatmap':
            # Create pivot table for heatmap: need at least 2 dimensions and 1 metric
            if len(dims) >= 2 and len(mets) >= 1 and dims[0] in df.columns and dims[1] in df.columns and mets[0] in df.columns:
                pivot_df = df.pivot_table(index=dims[0], columns=dims[1], values=mets[0], aggfunc='first').fillna(0)
            else:
                st.write('Heatmap requires at least two dimensions and one metric.')
                st.pyplot(fig)
                return
            
            # Plot heatmap
            im = ax.imshow(pivot_df)
            ax.set_xticks(range(len(pivot_df.columns)))
            ax.set_yticks(range(len(pivot_df.index)))
            ax.set_xticklabels(pivot_df.columns, rotation=45, ha='right')
            ax.set_yticklabels(pivot_df.index)
            plt.colorbar(im, ax=ax)
            
        # Set title
        ax.set_title(title or '')
        
        # Show plot in Streamlit
        st.pyplot(fig)
