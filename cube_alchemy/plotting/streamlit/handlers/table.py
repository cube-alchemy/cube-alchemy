import pandas as pd
from typing import Optional, List, Dict, Union, Callable


def render_table(
    st, 
    df: pd.DataFrame,    
    dimensions: List[str] | None = None,
    metrics: List[str] | None = None,
    title: Optional[str] = None,
    use_container_width: bool = True,
    height: Optional[int] = None,
    formatter: Optional[Dict[str, str]] = None,
    hide_index: bool = True,
    row_color_condition: Optional[Union[str, Callable]] = None,
    row_colors: Optional[Dict[str, str]] = None,
    **kwargs
):
    """Render a simple table/dataframe visualization.
    
    Args:
        st: The Streamlit module
        df: DataFrame to display
        dimensions: List of dimension columns to include
        metrics: List of metric columns to include
        title: Optional title to display above the table
        use_container_width: Whether to expand table to container width
        height: Optional height for the table
        formatter: Optional dictionary mapping column names to format strings
        hide_index: Whether to hide the index column (default: False)
        row_color_condition: Column name or callable that returns a boolean mask for rows to color
        row_colors: Dictionary of condition values to color strings (e.g., {"True": "lightgreen", "False": "lightcoral"})
        **kwargs: Additional parameters passed to st.dataframe
    
    Returns:
        The result of st.dataframe
    """
    if title:
        st.write(title)
        
    # Function to apply formatting based on column names
    def format_value(val, col_name):
        # Only apply formatter if provided for this column
        if formatter and col_name in formatter:
            fmt_spec = formatter[col_name]
            try:
                return fmt_spec.format(val)
            except Exception:
                # If formatting fails, return the original value
                return val
        # Return the original value if no formatter
        return val
    
    # Create a copy of the dataframe to apply formatting
    display_df = df
    if hide_index:
        display_df = display_df.reset_index(drop=True)
    
    # Prepare the dataframe to display (filter columns if dimensions and metrics are specified)
    final_df = display_df[dimensions + metrics] if dimensions and metrics else display_df.copy()
    
    # Create a styled version of the dataframe for display
    styled_df = None
    
    # Apply row coloring if conditions are specified - THIS MUST HAPPEN BEFORE FORMATTING
    # so that numeric comparisons work correctly on the raw values
    if row_color_condition and row_colors:
        try:
            
            # The simplest styling approach: create a function that checks each row's
            # condition value and applies the appropriate background color
            def highlight_rows(row):
                if isinstance(row_color_condition, str) and row_color_condition in row:
                    val = row[row_color_condition]
                    str_val = str(val)
                    
                    # Handle boolean conditions for numeric values
                    if ('True' in row_colors or 'False' in row_colors) and isinstance(val, (int, float)):
                        bool_val = bool(val > 0)
                        str_val = str(bool_val)
                    
                    if str_val in row_colors:
                        color = row_colors[str_val]
                        return [f'background-color: {color}'] * len(row)
                return [''] * len(row)
            
            # Create a formatter dictionary for all metrics
            format_dict = {}
            if formatter or metrics:
                for col in (metrics or []):
                    if col in final_df.columns:
                        # Use a simple function that calls our format_value for each column
                        format_dict[col] = lambda x, col=col: format_value(x, col)
            
            # Apply both styling and formatting in the correct order
            styled_df = final_df.style
            
            # First, apply the styling (colors)
            styled_df = styled_df.apply(highlight_rows, axis=1)
            
            # Then apply the formatting (currency, percentages, etc.)
            if format_dict:
                styled_df = styled_df.format(format_dict)
            
            # Hide index if requested
            if hide_index:
                # Try different pandas versions' hide_index methods
                try:
                    # For newer pandas versions (1.3.0+)
                    styled_df = styled_df.hide_index()
                except AttributeError:
                    try:
                        # For pandas 1.0.0 to 1.3.0
                        styled_df = styled_df.hide(axis="index")
                    except AttributeError:
                        # Fallback for older pandas versions
                        pass
            
            # Use the basic st.dataframe with the styled dataframe
            return st.dataframe(
                styled_df,
                use_container_width=use_container_width,
                height=height,
                hide_index=hide_index,  # Explicitly pass hide_index to Streamlit
                **{k: v for k, v in kwargs.items() 
                  if k not in ['st', 'df', 'title', 'use_container_width', 'height', 'formatter', 'hide_index', 'row_color_condition', 'row_colors']}
            )
        except Exception as e:
            # If styling fails, fall back to basic dataframe without styling
            # Apply formatting to the metrics columns before display using pandas styling
            # This keeps the formatting consistent with the styled version
            try:
                # Try to use pandas styling for formatting without coloring
                styled_df = final_df.style
                
                # Apply formatting
                format_dict = {}
                if formatter or metrics:
                    for col in (metrics or []):
                        if col in final_df.columns:
                            format_dict[col] = lambda x, col=col: format_value(x, col)
                
                if format_dict:
                    styled_df = styled_df.format(format_dict)
                
                # Hide index if needed
                if hide_index:
                    try:
                        styled_df = styled_df.hide_index()
                    except AttributeError:
                        try:
                            styled_df = styled_df.hide(axis="index")
                        except AttributeError:
                            pass
                
                # Will use styled_df without colors but with formatting
            except Exception:
                # If that fails too, use direct column formatting as last resort
                if formatter or metrics:
                    for col in (metrics or []):
                        if col in final_df.columns:
                            final_df[col] = final_df[col].apply(lambda x: format_value(x, col))
                styled_df = None
            
            # Use styled_df for formatting if available, otherwise use final_df
            return st.dataframe(
                styled_df if styled_df is not None else final_df,
                use_container_width=use_container_width,
                height=height,
                hide_index=hide_index,
                **{k: v for k, v in kwargs.items() 
                   if k not in ['st', 'df', 'title', 'use_container_width', 'height', 'formatter', 'hide_index', 'row_color_condition', 'row_colors']}
            )
    else:
        # No styling needed, but still apply formatting using pandas Styler for consistency
        try:
            # Use pandas styling for consistent formatting without coloring
            styled_df = final_df.style
            
            # Apply formatting
            format_dict = {}
            if formatter or metrics:
                for col in (metrics or []):
                    if col in final_df.columns:
                        format_dict[col] = lambda x, col=col: format_value(x, col)
            
            if format_dict:
                styled_df = styled_df.format(format_dict)
            
            # Hide index if needed
            if hide_index:
                try:
                    styled_df = styled_df.hide_index()
                except AttributeError:
                    try:
                        styled_df = styled_df.hide(axis="index")
                    except AttributeError:
                        pass
            
            return st.dataframe(
                styled_df,
                use_container_width=use_container_width,
                height=height,
                hide_index=hide_index,
                **{k: v for k, v in kwargs.items() 
                   if k not in ['st', 'df', 'title', 'use_container_width', 'height', 'formatter', 'hide_index', 'row_color_condition', 'row_colors']}
            )
        except Exception:
            # Fallback to direct formatting if pandas styling fails
            if formatter or metrics:
                for col in (metrics or []):
                    if col in final_df.columns:
                        final_df[col] = final_df[col].apply(lambda x: format_value(x, col))
            
            return st.dataframe(
                final_df,
                use_container_width=use_container_width,
                height=height,
                hide_index=hide_index,
                **{k: v for k, v in kwargs.items() 
                   if k not in ['st', 'df', 'title', 'use_container_width', 'height', 'formatter', 'hide_index', 'row_color_condition', 'row_colors']}
            )