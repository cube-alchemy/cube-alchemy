# Streamlit Integration

Cube Alchemy integrates seamlessly with Streamlit to create interactive data applications. The new plotting system makes this integration even more powerful and flexible.

## Basic Integration

### 1. Set Up Your Streamlit App

Start by importing the necessary libraries and setting up your Streamlit app:

```python
import streamlit as st
import pandas as pd
import pickle
from cube_alchemy import Hypercube
from cube_alchemy.plot_renderer import PlotRenderer

# Set page config
st.set_page_config(
    page_title="Cube Alchemy Analytics",
    page_icon="📊",
    layout="wide"
)
```

### 2. Create a StreamlitRenderer

Create a custom renderer for Streamlit by implementing the PlotRenderer interface:

```python
class StreamlitRenderer(PlotRenderer):
    """Renderer for Streamlit visualizations"""
    
    def __init__(self, height=None, use_container_width=True):
        self.height = height
        self.use_container_width = use_container_width
    
    def render(self, data, plot_config, **kwargs):
        # Get configuration options
        plot_type = plot_config.get('plot_type', 'bar')
        x_column = plot_config.get('x_column')
        y_column = plot_config.get('y_column')
        title = plot_config.get('title')
        orientation = plot_config.get('orientation', 'vertical')
        
        # Display title if provided
        if title:
            st.subheader(title)
        
        # Handle different plot types
        if plot_type == 'bar':
            return st.bar_chart(
                data.set_index(x_column)[y_column],
                height=self.height,
                use_container_width=self.use_container_width
            )
        elif plot_type == 'line':
            return st.line_chart(
                data.set_index(x_column)[y_column],
                height=self.height,
                use_container_width=self.use_container_width
            )
        elif plot_type == 'area':
            return st.area_chart(
                data.set_index(x_column)[y_column],
                height=self.height,
                use_container_width=self.use_container_width
            )
        else:
            st.error(f"Plot type '{plot_type}' not supported")
            return None
```

### 3. Load Your Hypercube

Load your hypercube, typically from a pickle file for a Streamlit app:

```python
@st.cache_resource  # Cache the cube to improve performance
def load_cube():
    with open("path_to_your_cube.pkl", "rb") as f:
        cube = pickle.load(f)
    
    # Important: Set context state after loading
    cube.set_context_state('Default')
    
    # Restore any functions needed for derived metrics
    cube.registered_functions = {
        'pd': pd,
        'np': np
    }
    
    return cube

# Load the cube
cube = load_cube()
```

### 4. Create Interactive Controls

Add interactive controls to filter your data:

```python
# Add dimension filters in the sidebar
st.sidebar.header("Filters")

# Get all dimensions
all_dims = cube.dimensions.keys()
selected_dims = st.sidebar.multiselect("Filter by dimensions", options=all_dims)

# For each selected dimension, add a filter control
filters = {}
for dim in selected_dims:
    values = cube.dimensions([dim])[dim]
    options = values.dropna().unique().tolist()
    selected = st.sidebar.multiselect(f"Select {dim}", options=options)
    if selected:
        filters[dim] = selected

# Apply filters if any
if filters:
    cube.filter(filters)
```

### 5. Display Visualizations

Display visualizations using the renderer and plot configurations:

```python
# Create tabs for different views
tab_viz, tab_data = st.tabs(["Visualization", "Data"])

with tab_viz:
    st.header("Query Visualization")
    
    # Select which query to visualize
    queries = list(cube.queries.keys())
    selected_query = st.selectbox("Select Query", options=queries)
    
    # Get available plot names
    plot_names = cube.list_plots(selected_query)
    
    if plot_names:
        # Let user select a plot configuration
        selected_plot = st.selectbox(
            "Select Plot Configuration", 
            options=plot_names
        )
        
        # Create renderer
        renderer = StreamlitRenderer(height=400)
        
        # Plot using selected configuration
        cube.plot(selected_query, renderer=renderer, plot_name=selected_plot)
    else:
        st.warning(f"No plot configurations for query '{selected_query}'")
        
        # Show raw data as fallback
        result = cube.query(selected_query)
        st.dataframe(result)

with tab_data:
    st.header("Query Data")
    result = cube.query(selected_query)
    st.dataframe(result)
```

## Advanced Integration

### Interactive Plot Configuration

Allow users to customize plot configurations on the fly:

```python
with st.expander("Customize Plot"):
    # Get the current plot config
    plot_config = cube.get_plot_config(selected_query, selected_plot)
    
    # Allow customization
    col1, col2 = st.columns(2)
    
    with col1:
        plot_type = st.selectbox(
            "Plot Type",
            options=["bar", "line", "area"],
            index=["bar", "line", "area"].index(plot_config.get("plot_type", "bar"))
        )
        
        title = st.text_input("Title", value=plot_config.get("title", ""))
    
    with col2:
        # Allow selecting different metrics
        query_def = cube.get_query(selected_query)
        available_metrics = query_def["metrics"] + query_def["derived_metrics"]
        
        y_column = st.selectbox(
            "Y-Axis (Metric)",
            options=available_metrics,
            index=available_metrics.index(plot_config.get("y_column")) if plot_config.get("y_column") in available_metrics else 0
        )
        
        orientation = st.selectbox(
            "Orientation",
            options=["vertical", "horizontal"],
            index=["vertical", "horizontal"].index(plot_config.get("orientation", "vertical"))
        )

# Use customized configuration        
cube.plot(
    selected_query, 
    renderer=renderer,
    plot_type=plot_type,
    y_column=y_column,
    title=title,
    orientation=orientation
)
```

## Best Practices

1. **Cache your cube**: Use `@st.cache_resource` to prevent reloading the cube on every interaction.
2. **Reset context state**: Always set a context state after loading a pickled cube.
3. **Handle errors gracefully**: Check for missing plot configurations and provide fallbacks.
4. **Provide data transparency**: Always give users access to the raw data behind visualizations.
5. **Use multiple views**: Leverage the multiple plot configurations to offer different perspectives on the same data.
