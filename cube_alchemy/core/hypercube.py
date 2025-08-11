import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

# hypercube building classes
from .hypercube_building_classes.engine import Engine
from .hypercube_building_classes.support_methods import SupportMethods
from .hypercube_building_classes.query_methods import QueryMethods
from .hypercube_building_classes.filter_methods import FilterMethods

# hypercube supporting classes
from .schema_validator import SchemaValidator
from .composite_bridge_generator import CompositeBridgeGenerator
from .metric import Metric

class Hypercube(Engine, QueryMethods, FilterMethods, SupportMethods):
    def __init__(
        self,
        tables: Dict[str, pd.DataFrame],
        apply_composite = True,
        validate: bool = True,
        to_be_stored: bool = False
    ) -> None:
        try:
            if validate:

                print("Initializing DataModel with provided tables...")
                # 1. Validate schema structure using sample data
                SchemaValidator.validate(tables)

                print("Hypercube schema validated successfully. Loading full data..")
            
                self.reduced_input_tables = SchemaValidator._create_sample_tables(tables)
            
            # 2. Schema is valid, build the actual model with full data
            bridge_generator = None
            if apply_composite:
                bridge_generator = CompositeBridgeGenerator(tables)
                tables = bridge_generator.tables
                composite_tables = bridge_generator.link_tables
                composite_keys = bridge_generator.composite_keys
            else:
                composite_tables = {}
                composite_keys = {}
            
            self.tables: Dict[str, pd.DataFrame] = tables
            self.relationships: Dict[Any, Any] = {}
            self.link_tables: Dict[str, pd.DataFrame] = {}
            self.composite_tables: Optional[Dict[str, pd.DataFrame]] = composite_tables
            self.composite_keys: Optional[Dict[str, Any]] = composite_keys
            self.link_table_keys: list = []
            self.column_to_table: Dict[str, str] = {}

            self.add_auto_relationships()
                
            self.relationships_raw = self.relationships.copy()  # Keep a raw copy of initial relationships
            self.relationships = {}

            # Add index columns to each table if not present
            for table in self.tables:
                index_col = f'_index_{table}'
                if index_col not in self.tables[table].columns:
                    self.tables[table].reset_index(drop=False, inplace=True)
                    self.tables[table].rename(columns={'index': index_col}, inplace=True)
            
            # Create link tables for shared columns and update the original tables
            self.create_link_tables()  # Link tables are used to join tables on shared columns

            # Build the column-to-table mapping
            self.build_column_to_table_mapping()  # Map each column to its source table
            
            # Automatically add relationships based on shared column names
            self.add_auto_relationships()  # Add relationships for columns with the same name

            self.is_cyclic = self.has_cyclic_relationships()
            if self.is_cyclic[0]:
                return None #no need to continue, there are cycle relationships

            self.context_states = {}
            self.trajectory_cache = {}

            if validate:
                self.compute_and_cache_trajectories()
                link_tables_trajectories = self.get_trajectory(self.link_tables.keys())
            else:
                link_tables_trajectories = self.find_complete_trajectory(self.link_tables)
            
            # Set the initial state to the unfiltered version of the joined trajectory keys
            self.context_states['Unfiltered'] = self.join_trajectory_keys(link_tables_trajectories)
            
            self.applied_filters = {}   # List of applied filters
            self.filter_pointer = {}    # Pointer to the current filter state
            self.registered_functions = {'pd': pd,'np': np}
            self.metrics = {}
            self.queries = {}

            if not to_be_stored: # If the model is intended to be stored in the disk initialize the context state "Default" after loading in memory
                self.set_context_state('Default')
            
            if not bridge_generator.composite_keys and validate:
                print("Hypercube initialized successfully")
            elif bridge_generator.composite_keys and validate:
                print("Hypercube initialized successfully with composite keys.")

        except ValueError as e:
            # Re-raise ValueError exceptions to be caught by calling code
            print(f"DataModel initialization failed: {str(e)}")
            raise
        except Exception as e:
            # Catch other exceptions, log them, and re-raise with a clear message
            print(f"An error occurred during DataModel initialization: {str(e)}")
            raise ValueError(f"DataModel initialization failed: {str(e)}")