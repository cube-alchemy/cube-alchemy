import pandas as pd
from typing import Optional, List, Union, Any, Tuple


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
        except Exception as e1:
            st.warning(f"Simple pivot failed: {e1}")
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
        
        # If we have multi-index columns, flatten them for easier handling
        if has_multiindex:
            # Create column names by joining the levels
            pivot_df.columns = [
                '_'.join(str(i) for i in col).strip('_') 
                if isinstance(col, tuple) else col 
                for col in pivot_df.columns
            ]
        
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
        
        # 6. DISPLAY PIVOT TABLE
        return st.dataframe(
            pivot_df.reset_index(drop=True),  # Using the pivoted and sorted dataframe with sort-only columns removed
            use_container_width=use_container_width,
            height=height,
            **{k: v for k, v in kwargs.items() 
               if k not in ['st', 'df', 'pivot', 'dimensions', 'metrics', 'title', 
                          'sort_ascending', 'sort_by',
                          'use_container_width', 'height']}
        )
        
    except Exception as e:
        st.error(f"Error creating pivot table: {str(e)}")
        
        # Add debugging information
        debug = st.expander("Debug Information")
        debug.write(f"""
        **Error:** {str(e)}
        
        **Parameters:**
        - Pivot: {pivot}
        - Dimensions: {dimensions}
        - Metrics: {metrics}
        - Sort by: {sort_by}
        
        **DataFrame Info:**
        - Shape: {df.shape}
        - Columns: {list(df.columns)}
        """)
        
        # Show sample data
        st.expander("Sample Data").dataframe(df.head(5))
        
        # Fallback to regular table
        return st.dataframe(
            df,
            use_container_width=use_container_width,
            height=height
        )