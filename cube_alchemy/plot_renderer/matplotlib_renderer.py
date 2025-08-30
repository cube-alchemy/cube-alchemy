import pandas as pd
from typing import Dict, Any
from .abc import PlotRenderer


class MatplotlibRenderer(PlotRenderer):
    """
    Matplotlib implementation of the PlotRenderer interface.

    Honors dimensions/metrics as provided; no implicit axis normalization.
    """

    def render(self, data: pd.DataFrame, plot_config: Dict[str, Any], **kwargs):
        import matplotlib.pyplot as plt

        plot_type = (plot_config.get('plot_type') or 'bar').lower()
        dims = plot_config.get('dimensions') or []
        mets = plot_config.get('metrics') or []
        color_by = plot_config.get('color_by')
        title = plot_config.get('title') or ''
        figsize = plot_config.get('figsize', (10, 6))
        orientation = plot_config.get('orientation', 'vertical')
        sort_values = plot_config.get('sort_values', False)
        sort_ascending = plot_config.get('sort_ascending', True)
        limit = plot_config.get('limit')

        df = data.copy()

        # Sort if requested (single-metric convenience only)
        if sort_values and isinstance(mets, list) and len(mets) == 1 and mets[0] in df.columns:
            df = df.sort_values(by=mets[0], ascending=sort_ascending)

        # Limit rows if requested
        if limit is not None:
            df = df.head(limit)

        fig, ax = plt.subplots(figsize=figsize)

        if plot_type in ('bar', 'line', 'area'):
            self._render_series(ax, df, dims, mets, color_by, plot_type, orientation)
        elif plot_type == 'scatter':
            self._render_scatter(ax, df, dims, mets, color_by)
        elif plot_type == 'pie':
            self._render_pie(ax, df, dims, mets)
        elif plot_type == 'heatmap':
            self._render_heatmap(ax, df, dims, mets)
        else:
            ax.text(0.5, 0.5, f"Unsupported plot type: {plot_type}", ha='center')

        ax.set_title(title)
        fig.tight_layout()
        return fig

    def _category_labels(self, df: pd.DataFrame, dims: list) -> pd.Series:
        if dims:
            return df[dims].astype(str).agg(' | '.join, axis=1)
        return pd.Series(['All'] * len(df), index=df.index)

    def _render_series(self, ax, df, dims, mets, color_by, plot_type, orientation):
        import numpy as np
        labels = self._category_labels(df, dims)

        # Single metric fast-path
        if isinstance(mets, list) and len(mets) == 1 and mets[0] in df.columns and not color_by:
            metric = mets[0]
            values = df[metric].values
            idx = np.arange(len(labels))
            if plot_type == 'bar':
                if orientation == 'horizontal':
                    ax.barh(idx, values)
                    ax.set_yticks(idx)
                    ax.set_yticklabels(labels)
                    ax.set_xlabel(metric)
                else:
                    ax.bar(idx, values)
                    ax.set_xticks(idx)
                    ax.set_xticklabels(labels, rotation=45, ha='right')
                    ax.set_ylabel(metric)
            elif plot_type == 'line':
                ax.plot(idx, values, marker='o')
                ax.set_xticks(idx)
                ax.set_xticklabels(labels, rotation=45, ha='right')
                ax.set_ylabel(metric)
            elif plot_type == 'area':
                ax.fill_between(idx, values, step='pre', alpha=0.5)
                ax.set_xticks(idx)
                ax.set_xticklabels(labels, rotation=45, ha='right')
                ax.set_ylabel(metric)
            return

        # Multi-series: derive series from color_by and/or multiple metrics
        # Build series dictionary: name -> values
        series = {}
        idx = np.arange(len(labels))
        if color_by and color_by in df.columns and isinstance(mets, list) and len(mets) == 1:
            metric = mets[0]
            for name, group in df.groupby(color_by):
                series[str(name)] = group[metric].values
        else:
            for m in mets:
                if m in df.columns:
                    series[m] = df[m].values

        n = len(series)
        if n == 0:
            ax.text(0.5, 0.5, 'No metrics to plot', ha='center')
            return

        if plot_type == 'bar':
            width = 0.8 / n
            for i, (name, vals) in enumerate(series.items()):
                if orientation == 'horizontal':
                    ax.barh(idx + (i - (n-1)/2)*width, vals, height=width, label=name)
                else:
                    ax.bar(idx + (i - (n-1)/2)*width, vals, width=width, label=name)
            ax.legend()
            if orientation == 'horizontal':
                ax.set_yticks(idx)
                ax.set_yticklabels(labels)
            else:
                ax.set_xticks(idx)
                ax.set_xticklabels(labels, rotation=45, ha='right')
        elif plot_type == 'line':
            for name, vals in series.items():
                ax.plot(idx, vals, marker='o', label=name)
            ax.legend()
            ax.set_xticks(idx)
            ax.set_xticklabels(labels, rotation=45, ha='right')
        elif plot_type == 'area':
            bottom = None
            for name, vals in series.items():
                if bottom is None:
                    ax.fill_between(idx, vals, step='pre', alpha=0.5, label=name)
                    bottom = vals
                else:
                    ax.fill_between(idx, bottom, bottom + vals, step='pre', alpha=0.5, label=name)
                    bottom = bottom + vals
            ax.legend()
            ax.set_xticks(idx)
            ax.set_xticklabels(labels, rotation=45, ha='right')

    def _render_scatter(self, ax, df, dims, mets, color_by):
        # Prefer two metrics; else dimension+metric
        if len(mets) >= 2 and mets[0] in df.columns and mets[1] in df.columns:
            x_col, y_col = mets[0], mets[1]
        elif len(mets) >= 1 and len(dims) >= 1 and mets[0] in df.columns and dims[0] in df.columns:
            x_col, y_col = dims[0], mets[0]
        else:
            ax.text(0.5, 0.5, 'Scatter requires two numeric columns', ha='center')
            return

        if color_by and color_by in df.columns:
            for name, group in df.groupby(color_by):
                ax.scatter(group[x_col], group[y_col], label=str(name), alpha=0.7)
            ax.legend()
        else:
            ax.scatter(df[x_col], df[y_col])

    def _render_pie(self, ax, df, dims, mets):
        labels = df[dims].astype(str).agg(' | '.join, axis=1) if dims else df.index.astype(str)
        if len(mets) >= 1 and mets[0] in df.columns:
            ax.pie(df[mets[0]], labels=labels, autopct='%1.1f%%')
        else:
            ax.text(0.5, 0.5, 'Pie requires one metric', ha='center')

    def _render_heatmap(self, ax, df, dims, mets):
        if len(dims) >= 2 and len(mets) >= 1 and dims[0] in df.columns and dims[1] in df.columns and mets[0] in df.columns:
            pivot_df = df.pivot_table(index=dims[0], columns=dims[1], values=mets[0], aggfunc='first').fillna(0)
            im = ax.imshow(pivot_df)
            ax.set_xticks(range(len(pivot_df.columns)))
            ax.set_yticks(range(len(pivot_df.index)))
            ax.set_xticklabels(pivot_df.columns, rotation=45, ha='right')
            ax.set_yticklabels(pivot_df.index)
            import matplotlib.pyplot as plt
            plt.colorbar(im, ax=ax)
        else:
            ax.text(0.5, 0.5, 'Heatmap requires two dimensions and one metric', ha='center')
