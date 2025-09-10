from __future__ import annotations
from typing import List, Optional
import pandas as pd


def render_combo(
    st,
    df: pd.DataFrame,
    *,
    dimensions: List[str] | None,
    metrics: List[str] | None,
    color_by: Optional[str] = None,
    orientation: str = 'vertical',
    height: int | None = None,
    use_container_width: bool = True,
    title: Optional[str] = None,
    show_title: bool = False,
):
    """Combo chart: first metric as bars, second metric as line.

    - Requires at least 1 dimension and 2 metrics.
    - Implemented using altair via st.altair_chart to get dual-encoding.
    """
    import altair as alt

    dimensions = dimensions or []
    metrics = metrics or []
    if len(dimensions) < 1 or len(metrics) < 2:
        return st.write('Combo requires at least 1 dimension and 2 metrics')

    dim = dimensions[0]
    m1, m2 = metrics[0], metrics[1]
    if dim not in df.columns or m1 not in df.columns or m2 not in df.columns:
        return st.write('Missing required columns for combo chart')

    # Base encodings
    x_enc = alt.X(f'{dim}:N', sort=None, axis=alt.Axis(labelAngle= -45))

    bar = alt.Chart(df).mark_bar(opacity=0.8).encode(
        x=x_enc if orientation == 'vertical' else alt.Y(f'{dim}:N', sort=None),
        y=alt.Y(f'{m1}:Q', title=m1) if orientation == 'vertical' else alt.X(f'{m1}:Q', title=m1),
        color=alt.value('#4C78A8'),
    )

    line = alt.Chart(df).mark_line(point=True, color='#E45756').encode(
        x=x_enc if orientation == 'vertical' else alt.Y(f'{dim}:N', sort=None),
        y=alt.Y(f'{m2}:Q', title=m2) if orientation == 'vertical' else alt.X(f'{m2}:Q', title=m2),
    )

    chart = alt.layer(bar, line).resolve_scale(
        y='independent' if orientation == 'vertical' else 'independent',
        x='shared' if orientation == 'vertical' else 'independent',
    )

    if title and show_title:
        chart = chart.properties(title=title)
    if height:
        chart = chart.properties(height=height)
    if use_container_width:
        return st.altair_chart(chart, use_container_width=True)
    return st.altair_chart(chart)
