import pandas as pd
from typing import Optional, List, Union, Any, Tuple, Dict,Callable


def render_pivot(
    st, 
    df: pd.DataFrame,
    pivot: Union[str, List[str]],
    dimensions: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
    title: Optional[str] = None,
    sort_ascending: Union[bool, List[bool]] = True,
    sort_by: Optional[Union[str, List[str], Tuple[str, ...], List[Tuple[str, ...]]]] = None,
    use_container_width: bool = True,
    height: Optional[int] = None,
    formatter: Optional[Dict[str, str]] = None,
    row_color_condition: Optional[Union[str, Callable]] = None,
    row_colors: Optional[Dict[str, str]] = None,
    **kwargs
):
    """Render a pivot table visualization.
    
    Args:
        st: The Streamlit module
        df: DataFrame to display
        pivot: Column(s) to use for pivoting the table
        dimensions: Columns to use as index in the pivot table
        metrics: Values to aggregate in the pivot table
        title: Optional title to display above the table
        sort_ascending: Sort order (True for ascending, False for descending).
                      Can be a list of booleans for multi-column sorting, e.g., [True, False]
        sort_by: Column name(s) to sort by. Can be:
                - A string: single column name
                - A list of strings: multiple column names
                - A tuple: for multi-level columns like ("Sales", "Product A")
                - A list of tuples: for multiple multi-level columns
        use_container_width: Whether to expand table to container width
        height: Optional height for the table
        formatter: Optional dictionary mapping column names to format strings
        row_color_condition: Column name or callable that returns a boolean mask for rows to color
        row_colors: Dictionary of condition values to color strings (e.g., {"True": "lightgreen", "False": "lightcoral"})
        **kwargs: Additional parameters passed to st.dataframe
    
    Returns:
        The result of st.dataframe with the pivoted data
    """
    try:
        # Display title if provided
        if title:
            st.write(title)
        
        
        # 1. PREPARE PARAMETERS
        # Ensure pivot is a list
        pivot_cols = [pivot] if isinstance(pivot, str) else list(pivot)
        
        # Use first dimension as index
        index = dimensions[0] if dimensions and len(dimensions) > 0 else None
        
        # Prepare sort columns
        sort_cols = []
        if sort_by:
            if isinstance(sort_by, (str, tuple)):
                sort_cols = [sort_by]
            else:
                sort_cols = list(sort_by)
        
        # 2. CREATE PIVOT TABLE
        # Set up index for pivot
        pivot_index = [index] if index else None
        
        # Create pivot table - pivot by month_year with Amount Actual as values
        try:
            # First try with a simpler pivot table approach that's more likely to work
            # with multi-level columns
            pivot_df = pd.pivot_table(
                df,
                index=pivot_index,
                columns=pivot_cols,
                values=metrics[0] if isinstance(metrics, list) and metrics else metrics,
                aggfunc='first'  # Use first value when multiple values exist
            )
        except Exception:
            # Try with more explicit parameters
            pivot_df = pd.pivot_table(
                df,
                index=pivot_index,
                columns=pivot_cols,
                values=metrics,
                aggfunc='first'  # Use first value when multiple values exist
            )
        
        # Reset index for easier display
        if pivot_index:
            pivot_df = pivot_df.reset_index()
        
        # 3. HANDLE MULTI-INDEX COLUMNS IF PRESENT
        has_multiindex = isinstance(pivot_df.columns, pd.MultiIndex)
        
        # Store original column structure before flattening
        original_columns = pivot_df.columns.tolist()
        column_mapping = {}
        
        # If we have multi-index columns, flatten them for easier handling
        if has_multiindex:
            # Create column names by joining the levels
            flattened_columns = [
                '_'.join(str(i) for i in col).strip('_') 
                if isinstance(col, tuple) else col 
                for col in pivot_df.columns
            ]
            
            # Create mapping between flattened and original columns
            column_mapping = {
                flattened: original for flattened, original in zip(flattened_columns, original_columns)
            }
            
            # Set the flattened column names
            pivot_df.columns = flattened_columns
        
        # Add sort columns directly from original DataFrame
        for sort_col in sort_cols:
            if sort_col not in pivot_df.columns and sort_col in df.columns:
                # For most cases, the sort column is constant per index value
                if index and index in pivot_df.columns:
                    # Add directly from original dataframe by joining on index
                    index_values = pivot_df[index].unique()
                    
                    # Create a temporary dataframe with just index and sort column
                    temp_df = df[[index, sort_col]].drop_duplicates(subset=[index])
                    
                    # Merge the sort column into the pivot table
                    pivot_df = pivot_df.merge(temp_df, on=index, how='left')
        
        # 4. SORT THE PIVOTED DATAFRAME
        if sort_cols:
            # Get valid sort columns that exist in pivot_df
            valid_sort_cols = [col for col in sort_cols if col in pivot_df.columns]
            
            # Handle sort direction
            if isinstance(sort_ascending, bool):
                sort_order = [sort_ascending] * len(valid_sort_cols)
            elif isinstance(sort_ascending, list):
                sort_order = sort_ascending[:len(valid_sort_cols)]
                # Extend if needed
                while len(sort_order) < len(valid_sort_cols):
                    sort_order.append(sort_order[-1] if sort_order else True)
            else:
                sort_order = [True] * len(valid_sort_cols)
            
            # Apply sorting if valid columns exist
            if valid_sort_cols:
                pivot_df = pivot_df.sort_values(
                    by=valid_sort_cols, 
                    ascending=sort_order
                )
                
                # Show sort information
                sort_info = []
                for i, col in enumerate(valid_sort_cols):
                    direction = "ascending" if sort_order[i] else "descending"
                    sort_info.append(f"{col} ({direction})")
                #st.caption(f"Sorted by: {', '.join(sort_info)}")
        
        # 5. REMOVE SORT-ONLY COLUMNS
        # Get list of columns that should always be kept
        keep_columns = []
        
        # Keep index/dimension columns
        if dimensions:
            for dim in dimensions:
                if dim in pivot_df.columns:
                    keep_columns.append(dim)
                    
        # Keep all columns that contain metric values
        if metrics:
            metric_cols = []
            for col in pivot_df.columns:
                # For original column names with values from pivot operation
                if any(metric in str(col) for metric in metrics):
                    metric_cols.append(col)
            keep_columns.extend(metric_cols)
                    
        # Drop sort-only columns
        drop_cols = []
        for col in pivot_df.columns:
            if col in sort_cols and col not in keep_columns:
                drop_cols.append(col)
        
        # Remove sort-only columns
        if drop_cols:
            pivot_df = pivot_df.drop(columns=drop_cols)
            
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
            
        # Apply formatting to numeric columns that are not dimensions
        format_columns = metric_cols if metrics else []
        
        # Process each column in the pivoted dataframe for formatting
        for col in pivot_df.columns:
            # Skip dimension columns
            if dimensions and col in dimensions:
                continue
                
            # Determine the metric part of this column
            metric_name = None
            
            # If we have column mapping from multi-index, use it
            if col in column_mapping:
                original_col = column_mapping[col]
                if isinstance(original_col, tuple) and len(original_col) > 0:
                    # Last part of the tuple is typically the metric name in pivot tables
                    metric_name = original_col[-1]
            
            # If no mapping or metric name not found, try to extract from column name
            if not metric_name:
                # Try to find which metric this column is derived from
                for m in metrics or []:
                    if isinstance(m, str) and isinstance(col, str) and m in col:
                        metric_name = m
                        break
            
            # Apply formatting if we found a metric match
            if metric_name and formatter and metric_name in formatter:
                fmt_spec = formatter[metric_name]
                try:
                    # Format using the metric name's formatter
                    pivot_df[col] = pivot_df[col].apply(
                        lambda x: fmt_spec.format(x) if pd.notna(x) and not isinstance(x, str) else x
                    )
                except Exception:
                    # If formatting fails, silently continue
                    pass
            else:
                # Fall back to standard formatting logic
                try:
                    pivot_df[col] = pivot_df[col].apply(
                        lambda x: format_value(x, metric_name if metric_name else col) 
                        if pd.notna(x) and not isinstance(x, str) else x
                    )
                except Exception:
                    # If formatting fails, silently continue
                    pass
        
        # 6. DISPLAY PIVOT TABLE WITH STYLING
        formatted_df = pivot_df.reset_index(drop=True)
        
        # Apply row coloring if conditions are specified
        if row_color_condition and row_colors:
            try:
                # Create a styled version of the dataframe
                styled_df = formatted_df.style
                
                # Define the styling function for row coloring
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
                
                # Create a formatter dictionary for metrics
                format_dict = {}
                if formatter:
                    for col in formatted_df.columns:
                        # Look for the metric name in the column
                        for metric_name in formatter:
                            if metric_name in str(col):
                                fmt_spec = formatter[metric_name]
                                format_dict[col] = lambda x, fmt=fmt_spec: fmt.format(x) if pd.notna(x) and not isinstance(x, str) else x
                
                # First, apply the row styling (colors)
                styled_df = styled_df.apply(highlight_rows, axis=1)
                
                # Then apply the formatting (currency, percentages, etc.) if needed
                if format_dict:
                    styled_df = styled_df.format(format_dict)
                
                return st.dataframe(
                    styled_df,  # Using the styled dataframe with both formatting and colors
                    use_container_width=use_container_width,
                    height=height,
                    hide_index=True,
                    **{k: v for k, v in kwargs.items() 
                       if k not in ['st', 'df', 'pivot', 'dimensions', 'metrics', 'title', 
                                   'sort_ascending', 'sort_by', 'formatter',
                                   'row_color_condition', 'row_colors',
                                   'use_container_width', 'height']}
                )
            except Exception as e:
                # If styling fails, fall back to unstyled dataframe
                st.warning(f"Row coloring could not be applied: {str(e)}")
                return st.dataframe(
                    formatted_df,
                    use_container_width=use_container_width,
                    height=height,
                    hide_index=True,
                    **{k: v for k, v in kwargs.items() 
                       if k not in ['st', 'df', 'pivot', 'dimensions', 'metrics', 'title', 
                                   'sort_ascending', 'sort_by', 'formatter',
                                   'row_color_condition', 'row_colors',
                                   'use_container_width', 'height']}
                )
        else:
            # No styling needed
            return st.dataframe(
                formatted_df,
                use_container_width=use_container_width,
                height=height,
                hide_index=True,
                **{k: v for k, v in kwargs.items() 
                   if k not in ['st', 'df', 'pivot', 'dimensions', 'metrics', 'title', 
                              'sort_ascending', 'sort_by', 'formatter',
                              'row_color_condition', 'row_colors',
                              'use_container_width', 'height']}
            )
        
    except Exception as e:
        st.error(f"Error creating pivot table: {str(e)}")
        
        # Fallback to regular table
        return st.dataframe(
            df,
            use_container_width=use_container_width,
            height=height,
            hide_index=True,
            **{k: v for k, v in kwargs.items() 
               if k not in ['st', 'df', 'pivot', 'dimensions', 'metrics', 'title', 
                          'sort_ascending', 'sort_by', 'formatter',
                          'row_color_condition', 'row_colors',
                          'use_container_width', 'height']}
        )