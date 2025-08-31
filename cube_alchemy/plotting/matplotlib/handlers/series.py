import pandas as pd
from typing import List, Optional


def _category_labels(df: pd.DataFrame, dims: List[str]) -> pd.Series:
    if dims:
        return df[dims].astype(str).agg(' | '.join, axis=1)
    return pd.Series(['All'] * len(df), index=df.index)


def render_series(ax, df: pd.DataFrame, dims: List[str], mets: List[str], color_by: Optional[str], plot_type: str, orientation: str = 'vertical', stacked: bool = False) -> None:
    import numpy as np

    labels = _category_labels(df, dims)

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


def render_bar(ax, df: pd.DataFrame, dims: List[str], mets: List[str], color_by: Optional[str], orientation: str = 'vertical', stacked: bool = False) -> None:
    import numpy as np
    # Special handling: (2,1) -> split by second dimension into colors (stacked or grouped)
    if isinstance(dims, list) and len(dims) >= 2 and isinstance(mets, list) and len(mets) >= 1:
        dim_cat, dim_group = dims[0], dims[1]
        metric = mets[0]
        if dim_cat in df.columns and dim_group in df.columns and metric in df.columns:
            # Pivot: rows=dim_cat, cols=dim_group, values=metric
            pivot_df = df.pivot_table(index=dim_cat, columns=dim_group, values=metric, aggfunc='sum').fillna(0)
            cats = pivot_df.index.astype(str).tolist()
            groups = pivot_df.columns.astype(str).tolist()
            idx = np.arange(len(cats))
            if stacked:
                # One bar per category, stacked by group
                bottom = None
                for g in groups:
                    vals = pivot_df[g].values
                    if orientation == 'horizontal':
                        ax.barh(idx, vals, left=bottom if bottom is not None else 0, label=g)
                    else:
                        ax.bar(idx, vals, bottom=bottom if bottom is not None else 0, label=g)
                    bottom = (vals if bottom is None else bottom + vals)
                ax.legend()
            else:
                # Grouped bars side-by-side
                n = len(groups)
                width = 0.8 / max(n, 1)
                for i, g in enumerate(groups):
                    vals = pivot_df[g].values
                    if orientation == 'horizontal':
                        ax.barh(idx + (i - (n-1)/2)*width, vals, height=width, label=g)
                    else:
                        ax.bar(idx + (i - (n-1)/2)*width, vals, width=width, label=g)
                ax.legend()
            # Axes labels
            if orientation == 'horizontal':
                ax.set_yticks(idx)
                ax.set_yticklabels(cats)
            else:
                ax.set_xticks(idx)
                ax.set_xticklabels(cats, rotation=45, ha='right')
            return
    # Default behavior covers (1,n) and other cases
    return render_series(ax, df, dims, mets, color_by, 'bar', orientation, stacked)


def render_line(ax, df: pd.DataFrame, dims: List[str], mets: List[str], color_by: Optional[str], orientation: str = 'vertical', stacked: bool = False) -> None:
    import numpy as np
    # Special handling: (2,1) -> split by second dimension into colored lines
    if isinstance(dims, list) and len(dims) >= 2 and isinstance(mets, list) and len(mets) >= 1:
        dim_cat, dim_group = dims[0], dims[1]
        metric = mets[0]
        if dim_cat in df.columns and dim_group in df.columns and metric in df.columns:
            pivot_df = df.pivot_table(index=dim_cat, columns=dim_group, values=metric, aggfunc='sum').fillna(0)
            cats = pivot_df.index.astype(str).tolist()
            idx = np.arange(len(cats))
            for g in pivot_df.columns.astype(str).tolist():
                vals = pivot_df[g].values
                ax.plot(idx, vals, marker='o', label=g)
            ax.legend()
            ax.set_xticks(idx)
            ax.set_xticklabels(cats, rotation=45, ha='right')
            return
    # Default behavior covers (1,n)
    return render_series(ax, df, dims, mets, color_by, 'line', orientation, stacked)


def render_area(ax, df: pd.DataFrame, dims: List[str], mets: List[str], color_by: Optional[str], orientation: str = 'vertical', stacked: bool = False) -> None:
    return render_series(ax, df, dims, mets, color_by, 'area', orientation, stacked)
