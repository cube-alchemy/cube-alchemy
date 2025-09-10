from __future__ import annotations
from typing import Optional, List
import pandas as pd


def _build_wide_dataframe(
    df: pd.DataFrame,
    dimensions: List[str] | None,
    metrics: List[str] | None,
    color_by: Optional[str] = None,
) -> pd.DataFrame:
    """Transform df into a wide format suitable for st.*_chart.

    - If one metric: index=category, columns=color_by (optional)
    - If multiple metrics: index=category, columns=series built from metric (+ color_by)
    """
    dimensions = dimensions or []
    metrics = [m for m in (metrics or []) if m in df.columns]

    # Category label from all dimensions
    if dimensions:
        cat_series = df[dimensions].astype(str).agg(' | '.join, axis=1)
    else:
        cat_series = pd.Series(['All'] * len(df), index=df.index)

    work = df.copy()
    work['__category__'] = cat_series

    # Auto-color/group by second dimension if present and no explicit color_by
    auto_group = None
    if len(dimensions) >= 2 and (color_by is None or color_by not in work.columns):
        if dimensions[1] in work.columns:
            auto_group = dimensions[1]
    group_key = color_by if (color_by and color_by in work.columns) else auto_group

    if not metrics:
        # No metrics to plot; return empty
        return pd.DataFrame(index=work['__category__'])

    if len(metrics) == 1:
        metric = metrics[0]
        if group_key:
            wide = (
                work.pivot_table(index='__category__', columns=group_key, values=metric, aggfunc='first')
                .fillna(0)
            )
        else:
            wide = work.set_index('__category__')[[metric]]
            wide.columns = [metric]
        return wide

    # Multi-metric: melt and pivot to series columns
    id_vars = ['__category__'] + ([group_key] if group_key else [])
    long_df = work.melt(id_vars=id_vars, value_vars=metrics, var_name='__metric__', value_name='__value__')
    if group_key:
        long_df['__series__'] = long_df[group_key].astype(str) + ' • ' + long_df['__metric__']
    else:
        long_df['__series__'] = long_df['__metric__']
    wide = long_df.pivot_table(index='__category__', columns='__series__', values='__value__', aggfunc='first').fillna(0)
    return wide


def render_bar(
    st, df: pd.DataFrame, *,
    dimensions: List[str] | None = None,
    metrics: List[str] | None = None,
    color_by: Optional[str] = None,
    orientation: str = 'vertical',
    height: Optional[int] = 400,
    use_container_width: bool = True,
    title: Optional[str] = None,
    show_title: bool = False,
    stacked: bool = False,
):
    """Streamlit-native bar chart handler.

    Note: Streamlit's native bar_chart doesn't support horizontal orientation or stacked bars.
    Orientation and stacked are accepted for API compatibility; you can enhance later.
    """
    if title and show_title:
        st.caption(title)
    wide = _build_wide_dataframe(df, dimensions, metrics, color_by)
    if wide.empty:
        return st.write('No metrics to plot.')
    # Ignoring orientation/stacked in this basic handler
    return st.bar_chart(wide, height=height, use_container_width=use_container_width)


def render_line(
    st, df: pd.DataFrame, *,
    dimensions: List[str] | None = None,
    metrics: List[str] | None = None,
    color_by: Optional[str] = None,
    height: Optional[int] = 400,
    use_container_width: bool = True,
    title: Optional[str] = None,
    show_title: bool = False,
):
    """Streamlit-native line chart handler."""
    if title and show_title:
        st.caption(title)
    wide = _build_wide_dataframe(df, dimensions, metrics, color_by)
    if wide.empty:
        return st.write('No metrics to plot.')
    return st.line_chart(wide, height=height, use_container_width=use_container_width)
