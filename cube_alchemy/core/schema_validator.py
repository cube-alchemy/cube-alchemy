import logging
from typing import Dict, Tuple, TYPE_CHECKING
import pandas as pd
import copy # I need a deep copy to ensure complete isolation of the sample tables from the original data
import re
  
logger = logging.getLogger(__name__)
  

class SchemaValidator:
    """Validates the schema structure for a Hypercube model."""
    
    @staticmethod
    def _create_sample_tables(tables: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        # Create reduced tables for validation       
        reduced_tables_1 = {}
        for table_name, table in tables.items():
            reduced_tables_1[table_name] = copy.deepcopy(table.head(10)) 

        reduced_tables_2 = {}
        for table_name, table in reduced_tables_1.items():
            reduced_tables_2[table_name] = copy.deepcopy(table)

        return reduced_tables_1,reduced_tables_2
    
    @staticmethod
    def validate(tables: Dict[str, pd.DataFrame]) -> bool:
        from .hypercube import Hypercube
        # Create sample tables for validation
        reduced_tables_1, reduced_tables_2 = SchemaValidator._create_sample_tables(tables)
        
        # Validate reserved prefix 
        for table_name, table in reduced_tables_1.items():
            if table_name.startswith('_link_table_') or table_name.startswith('_composite_'):
                raise ValueError(f"Table name '{table_name}' uses reserved prefix '_link_table_' or '_composite_'. This prefix is reserved for internal use.")
            for column in table.columns:
                if column.startswith('_key_') or column.startswith('_index_') or column.startswith('_composite_key_'):
                    raise ValueError(f"Column '{column}' in table '{table_name}' uses reserved prefix '_key_' or '_index_' or '_composite_key_'. These prefixes are reserved for internal use.")
                # Check that column name do not use '<*>' syntax
                if re.search(r'<.*>', column):
                    raise ValueError(f"Column '{column}' in table '{table_name}' uses invalid brackets '<*>' syntax. These are reserved for internal use.")

        # Initialize hypercube with generated structures
        hypercube = Hypercube(reduced_tables_1, validate = False)
        
        # Check for cyclic relationships
        is_valid = not hypercube.is_cyclic[0]
        
        if not is_valid:
            logger.error("Hypercube initialization failed due to cyclic relationships or other issues.")

            # Create hypercube directly with original tables for visualization
            diagnostic_cube = Hypercube(reduced_tables_2, validate = False, apply_composite=False)
            logger.info("Visualizing the original tables graph...")
            diagnostic_cube.visualize_graph(full_column_names=False)

            logger.info("Relationships after initialization with composite tables:")
            cyclic_tables = [table for table in diagnostic_cube.is_cyclic[1] if not table.startswith('_link_table_')]
            logger.error("Cyclic relationships detected in the hypercube: %s", ' -> '.join(cyclic_tables))

            error_msg = "Cyclic relationships detected in the hypercube"
            raise ValueError(error_msg)
        
        return True