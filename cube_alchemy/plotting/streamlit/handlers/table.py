import pandas as pd
from typing import Optional, List


def render_table(
    st, 
    df: pd.DataFrame,    
    dimensions: List[str] | None = None,
    metrics: List[str] | None = None,
    title: Optional[str] = None,
    use_container_width: bool = True,
    height: Optional[int] = None,
    **kwargs
):
    """Render a simple table/dataframe visualization.
    
    Args:
        st: The Streamlit module
        df: DataFrame to display
        title: Optional title to display above the table
        use_container_width: Whether to expand table to container width
        height: Optional height for the table
        **kwargs: Additional parameters passed to st.dataframe
    
    Returns:
        The result of st.dataframe
    """
    if title:
        st.write(title)
    
    return st.dataframe(
        df.reset_index(drop=True)[dimensions + metrics],
        use_container_width=use_container_width,
        height=height,
        **{k: v for k, v in kwargs.items() 
           if k not in ['st', 'df', 'title', 'use_container_width', 'height']}
    )