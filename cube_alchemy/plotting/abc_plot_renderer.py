"""
Abstract base class for plot renderers in Cube Alchemy.
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any


class PlotRenderer(ABC):
    """
    Abstract base class for plot renderers.
    
    Plot renderers are responsible for taking data and a plot configuration
    and rendering them using a specific visualization framework.
    """
    
    @abstractmethod
    def render(self, 
               data: pd.DataFrame, 
               plot_config: Dict[str, Any],
               **kwargs) -> Any:
        """
        Render the plot using the given data and configuration.
        
        Args:
            data: DataFrame containing the data to plot
            plot_config: Dictionary with plot configuration
            **kwargs: Additional keyword arguments for the renderer
            
        Returns:
            The rendered plot object (framework-specific)
        """
        pass

