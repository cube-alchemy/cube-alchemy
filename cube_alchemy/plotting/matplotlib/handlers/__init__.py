from .series import render_bar, render_line, render_area
from .combo import render_combo
from .scatter import render_scatter
from .pie import render_pie
from .heatmap import render_heatmap

# Registry mapping plot types to handler callables with a common signature
# handler(ax, df, dims, mets, color_by, orientation)
PLOT_HANDLERS = {
    'bar': render_bar,
    'line': render_line,
    'area': render_area,
    'scatter': render_scatter,
    'pie': render_pie,
    'heatmap': render_heatmap,
    'combo': render_combo,
}

__all__ = ['PLOT_HANDLERS']
