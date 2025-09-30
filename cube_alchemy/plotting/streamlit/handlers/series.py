from __future__ import annotations
from typing import Optional, List, Dict, Any
import pandas as pd


def _category_and_group(
    df: pd.DataFrame,
    dimensions: List[str] | None,
    color_by: Optional[str] = None,
):
    """Return (category_field_name, group_field_name_or_None, prepared_df).

    - If there are 2 dimensions and no explicit color_by, use dim[1] as group.
    - Category uses only non-group dimensions to avoid embedding group into x labels.
    """
    dimensions = dimensions or []
    work = df.copy()

    auto_group = None
    if len(dimensions) >= 2 and (not color_by or color_by not in work.columns):
        if dimensions[1] in work.columns:
            auto_group = dimensions[1]
    group_key = color_by if (color_by and color_by in work.columns) else auto_group

    # Category from remaining dimensions (excluding group_key if present)
    cat_dims = [d for d in dimensions if d != group_key]
    if cat_dims:
        work["__category__"] = work[cat_dims].astype(str).agg(" | ".join, axis=1)
    else:
        work["__category__"] = "All"

    return "__category__", group_key, work


def _build_wide_dataframe(
    df: pd.DataFrame,
    dimensions: List[str] | None,
    metrics: List[str] | None,
    color_by: Optional[str] = None,
) -> pd.DataFrame:
    """Transform df into a wide format suitable for st.* charts.

    - If one metric: index=category, columns=color_by (optional)
    - If multiple metrics: index=category, columns=series built from metric (+ color_by)
    - Excludes the group dimension from the x-axis category label
    """
    dimensions = dimensions or []
    metrics = [m for m in (metrics or []) if m in df.columns]

    cat_field, group_key, work = _category_and_group(df, dimensions, color_by)

    if not metrics:
        return pd.DataFrame(index=work[cat_field])

    if len(metrics) == 1:
        metric = metrics[0]
        if group_key:
            wide = work.pivot_table(index=cat_field, columns=group_key, values=metric, aggfunc="first")
            # Keep NaN so line charts can break lines; bar charts may fill later
        else:
            wide = work.set_index(cat_field)[[metric]]
            wide.columns = [metric]
        return wide

    # Multi-metric: melt and pivot to series columns
    id_vars = [cat_field] + ([group_key] if group_key else [])
    long_df = work.melt(id_vars=id_vars, value_vars=metrics, var_name="__metric__", value_name="__value__")
    if group_key:
        long_df["__series__"] = long_df[group_key].astype(str) + "  " + long_df["__metric__"]
    else:
        long_df["__series__"] = long_df["__metric__"]
    wide = long_df.pivot_table(index=cat_field, columns="__series__", values="__value__", aggfunc="first")
    return wide


def render_bar(
    st, df: pd.DataFrame, *,
    dimensions: List[str] | None = None,
    metrics: List[str] | None = None,
    color_by: Optional[str] = None,
    orientation: str = "vertical",
    height: Optional[int] = 400,
    width: Optional[int] = None,
    use_container_width: bool = True,
    title: Optional[str] = None,
    show_title: bool = False,
    stacked: bool = False,
    legend_position: str = "right",
    formatter: Optional[Dict[str, str]] = None,
):
    """Bar chart with Altair, mirroring matplotlib grouping rules.

    - With two dimensions and one metric: first dim on x, second dim as color legend.
    - Y-axis title shows metric name.
    - Groups side-by-side when stacked is False; stacked when True.
    - Legend position can be set to "right", "left", "top", or "bottom"
    """
    import altair as alt

    if df is None or df.empty:
        return st.write("No metrics to plot.")

    metrics = metrics or []
    dimensions = dimensions or []

    # Determine category and group first (to respect existing grouping rules)
    cat_field, group_key, work = _category_and_group(df, dimensions, color_by)

    # Compute which metrics are available in the dataframe
    used_metrics = [m for m in metrics if m in work.columns]
    if not used_metrics:
        num_cols = work.select_dtypes(include=["number"]).columns.tolist()
        used_metrics = num_cols[:1]
    if not used_metrics:
        return st.write("No metrics to plot.")

    x_enc = alt.X(f"{cat_field}:N", sort=None, axis=alt.Axis(title=None, labelAngle=-45))

    # Function to apply formatting based on column names
    def format_value(val: Any, col_name: str) -> Any:
        import numpy as np
        
        # Handle already formatted strings
        if isinstance(val, str):
            return val
            
        # Apply formatter if provided for this column
        if formatter and col_name in formatter:
            fmt_spec = formatter[col_name]
            try:
                return fmt_spec.format(val)
            except Exception:
                # If formatting fails, return the original value
                pass
                
        # Special formatting for percentage columns if no explicit formatter
        if isinstance(col_name, str) and ('%' in col_name or 'percent' in col_name.lower() or 'margin' in col_name.lower()):
            if isinstance(val, (int, float, np.integer, np.floating)):
                # Multiply by 100 for proper percentage display
                return f"{val * 100:.2f}%"
        
        # Default to currency formatting for numbers
        if isinstance(val, (int, float, np.integer, np.floating)):
            return f"${val:,.0f}"
            
        # Return other values as-is
        return val
        
    # Special case: one dimension, multiple metrics, and no group/color_by 
    # show one color per metric, side-by-side using xOffset when not stacked.
    if len(dimensions) == 1 and not group_key and len(used_metrics) >= 2:
        long_df = work.melt(id_vars=[cat_field], value_vars=used_metrics,
                            var_name="__series__", value_name="__value__")
        
        # Create tooltip columns with formatted values if needed
        for metric in used_metrics:
            tooltip_col = f"{metric}_formatted"
            long_df[tooltip_col] = long_df.apply(
                lambda row: format_value(row["__value__"], row["__series__"]) 
                if row["__series__"] == metric else "", 
                axis=1
            )
        
        base = alt.Chart(long_df)
        y_enc_multi = alt.Y("__value__:Q", title="Value")
        color_enc_multi = alt.Color("__series__:N", title="Metric")
        # Create tooltip fields to include formatted values
        tooltip_fields = [cat_field]
        for metric in used_metrics:
            tooltip_col = f"{metric}_formatted"
            tooltip_fields.append(alt.Tooltip(f"{metric}_formatted:N", title=metric))
            
        if not stacked:
            chart = base.mark_bar().encode(
                x=x_enc,
                y=y_enc_multi,
                color=color_enc_multi,
                xOffset="__series__:N",
                tooltip=[cat_field, alt.Tooltip("__series__:N", title="Metric"), 
                         alt.Tooltip("__value__:Q", title="Value", format=",.0f"),
                         alt.Tooltip("__series___formatted:N", title="Formatted")]
            )
        else:
            chart = base.mark_bar().encode(
                x=x_enc,
                y=y_enc_multi,
                color=color_enc_multi,
                tooltip=[cat_field, alt.Tooltip("__series__:N", title="Metric"), 
                         alt.Tooltip("__value__:Q", title="Value", format=",.0f"),
                         alt.Tooltip("__series___formatted:N", title="Formatted")]
            )
    else:
        # Default behavior (preserve existing rendering): choose a single metric
        metric = used_metrics[0]
        y_enc = alt.Y(f"{metric}:Q", title=metric)
        base = alt.Chart(work)
        
        # Create formatted tooltip columns if needed
        tooltip_col = f"{metric}_formatted"
        if formatter and metric in formatter:
            work[tooltip_col] = work[metric].apply(lambda x: format_value(x, metric))
        else:
            work[tooltip_col] = work[metric].apply(lambda x: format_value(x, metric))

        if group_key:
            color_enc = alt.Color(f"{group_key}:N", title=group_key)
            tooltip_fields = [cat_field, alt.Tooltip(f"{metric}:Q", title=metric, format=",.0f"),
                             alt.Tooltip(f"{tooltip_col}:N", title=f"{metric} Formatted")]
            
            if not stacked:
                chart = base.mark_bar().encode(
                    x=x_enc,
                    y=y_enc,
                    color=color_enc,
                    xOffset=f"{group_key}:N",
                    tooltip=tooltip_fields + [group_key]
                )
            else:
                chart = base.mark_bar().encode(
                    x=x_enc,
                    y=y_enc,
                    color=color_enc,
                    tooltip=tooltip_fields + [group_key]
                )
        else:
            chart = base.mark_bar().encode(
                x=x_enc,
                y=y_enc,
                tooltip=[cat_field, alt.Tooltip(f"{metric}:Q", title=metric, format=",.0f"),
                         alt.Tooltip(f"{tooltip_col}:N", title=f"{metric} Formatted")]
            )

    if title:
        chart = chart.properties(title=title)
    if height:
        chart = chart.properties(height=height)
    if width:
        chart = chart.properties(width=width)
        
    # Configure legend position
    if legend_position:
        chart = chart.configure_legend(
            orient=legend_position
        )

    return st.altair_chart(chart, use_container_width=use_container_width)


def render_line(
    st, df: pd.DataFrame, *,
    dimensions: List[str] | None = None,
    metrics: List[str] | None = None,
    color_by: Optional[str] = None,
    height: Optional[int] = 400,
    width: Optional[int] = None,
    use_container_width: bool = True,
    title: Optional[str] = None,
    show_title: bool = False,
    legend_position: str = "right",
    formatter: Optional[Dict[str, str]] = None,
):
    """Line chart with Altair:

    - With two dimensions and one metric: color by second dim, legend shown.
    - Avoid plotting zeros for missing values (keep NaN, filter out).
    - Y-axis title shows metric name.
    - Legend position can be set to "right", "left", "top", or "bottom"
    """
    import altair as alt

    if df is None or df.empty:
        return st.write("No metrics to plot.")

    metrics = metrics or []
    dimensions = dimensions or []

    # Determine category and group
    cat_field, group_key, work = _category_and_group(df, dimensions, color_by)

    # Build long form for possibly multiple metrics
    used_metrics = [m for m in metrics if m in work.columns]
    if not used_metrics:
        num_cols = work.select_dtypes(include=["number"]).columns.tolist()
        used_metrics = num_cols[:1]
    if not used_metrics:
        return st.write("No metrics to plot.")

    if len(used_metrics) == 1:
        metric = used_metrics[0]
        base = alt.Chart(work)
        x_enc = alt.X(f"{cat_field}:N", sort=None, axis=alt.Axis(title=None, labelAngle=-45))
        y_enc = alt.Y(f"{metric}:Q", title=metric)
        if group_key:
            chart = base.transform_filter(
                f'isValid(datum["{metric}"]) && isFinite(datum["{metric}"])'
            ).mark_line(point=True).encode(
                x=x_enc,
                y=y_enc,
                color=alt.Color(f"{group_key}:N", title=group_key),
            )
        else:
            chart = base.transform_filter(
                f'isValid(datum["{metric}"]) && isFinite(datum["{metric}"])'
            ).mark_line(point=True).encode(
                x=x_enc,
                y=y_enc,
            )
    else:
        # Multiple metrics: melt to series and color by series
        long_df = work.melt(id_vars=[cat_field] + ([group_key] if group_key else []),
                            value_vars=used_metrics, var_name="__series__", value_name="__value__")
        base = alt.Chart(long_df)
        x_enc = alt.X(f"{cat_field}:N", sort=None, axis=alt.Axis(title=None, labelAngle=-45))
        y_enc = alt.Y("__value__:Q", title="Value")
        series_color = "__series__" if not group_key else "__series__"
        chart = base.transform_filter(
            'isValid(datum["__value__"]) && isFinite(datum["__value__"])'
        ).mark_line(point=True).encode(
            x=x_enc,
            y=y_enc,
            color=alt.Color(f"{series_color}:N", title="Series"),
        )

    if title:
        chart = chart.properties(title=title)
    if height:
        chart = chart.properties(height=height)
    if width:
        chart = chart.properties(width=width)
        
    # Configure legend position
    if legend_position:
        chart = chart.configure_legend(
            orient=legend_position
        )

    return st.altair_chart(chart, use_container_width=use_container_width)


def render_area(
    st, df: pd.DataFrame, *,
    dimensions: List[str] | None = None,
    metrics: List[str] | None = None,
    color_by: Optional[str] = None,
    height: Optional[int] = 400,
    width: Optional[int] = None,
    use_container_width: bool = True,
    title: Optional[str] = None,
    show_title: bool = False,
    legend_position: str = "right",
    formatter: Optional[Dict[str, str]] = None,
):
    """Area chart with Altair, mirroring line-chart grouping rules.

    - With two dimensions and one metric: color by second dim, legend shown.
    - Multiple metrics: color by metric series.
    - Areas are always stacked to avoid occlusion.
    - Legend position can be set to "right", "left", "top", or "bottom"
    """
    import altair as alt

    if df is None or df.empty:
        return st.write("No metrics to plot.")

    metrics = metrics or []
    dimensions = dimensions or []

    # Determine category and group
    cat_field, group_key, work = _category_and_group(df, dimensions, color_by)

    # Build long form for possibly multiple metrics
    used_metrics = [m for m in metrics if m in work.columns]
    if not used_metrics:
        num_cols = work.select_dtypes(include=["number"]).columns.tolist()
        used_metrics = num_cols[:1]
    if not used_metrics:
        return st.write("No metrics to plot.")

    if len(used_metrics) == 1:
        metric = used_metrics[0]
        base = alt.Chart(work)
        x_enc = alt.X(f"{cat_field}:N", sort=None, axis=alt.Axis(title=None, labelAngle=-45))
        y_enc = alt.Y(f"{metric}:Q", title=metric, stack="zero")
        if group_key:
            chart = base.transform_filter(
                f'isValid(datum["{metric}"]) && isFinite(datum["{metric}"])'
            ).mark_area().encode(
                x=x_enc,
                y=y_enc,
                color=alt.Color(f"{group_key}:N", title=group_key),
            )
        else:
            chart = base.transform_filter(
                f'isValid(datum["{metric}"]) && isFinite(datum["{metric}"])'
            ).mark_area().encode(
                x=x_enc,
                y=y_enc,
            )
    else:
        # Multiple metrics: melt to series and color by series
        long_df = work.melt(id_vars=[cat_field] + ([group_key] if group_key else []),
                            value_vars=used_metrics, var_name="__series__", value_name="__value__")
        base = alt.Chart(long_df)
        x_enc = alt.X(f"{cat_field}:N", sort=None, axis=alt.Axis(title=None, labelAngle=-45))
        y_enc = alt.Y("__value__:Q", title="Value", stack="zero")
        chart = base.transform_filter(
            'isValid(datum["__value__"]) && isFinite(datum["__value__"])'
        ).mark_area().encode(
            x=x_enc,
            y=y_enc,
            color=alt.Color("__series__:N", title="Series"),
        )

    if title:
        chart = chart.properties(title=title)
    if height:
        chart = chart.properties(height=height)
    if width:
        chart = chart.properties(width=width)
        
    # Configure legend position
    if legend_position:
        chart = chart.configure_legend(
            orient=legend_position
        )

    return st.altair_chart(chart, use_container_width=use_container_width)
