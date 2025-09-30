import pandas as pd
from typing import Optional, List, Dict


def render_table(
    st, 
    df: pd.DataFrame,    
    dimensions: List[str] | None = None,
    metrics: List[str] | None = None,
    title: Optional[str] = None,
    use_container_width: bool = True,
    height: Optional[int] = None,
    formatter: Optional[Dict[str, str]] = None,
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
        
    # Function to apply formatting based on column names
    def format_value(val, col_name):
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
                return val
                
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
    
    # Create a copy of the dataframe to apply formatting
    display_df = df.reset_index(drop=True).copy()
    
    # Apply formatting to the metrics columns
    if formatter or metrics:
        for col in (metrics or []):
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: format_value(x, col))
    
    return st.dataframe(
        display_df[dimensions + metrics] if dimensions and metrics else display_df,
        use_container_width=use_container_width,
        height=height,
        **{k: v for k, v in kwargs.items() 
           if k not in ['st', 'df', 'title', 'use_container_width', 'height', 'formatter']}
    )