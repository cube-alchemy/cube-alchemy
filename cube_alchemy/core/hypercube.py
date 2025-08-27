import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

# hypercube building classes
from .hypercube_building_classes.engine import Engine
from .hypercube_building_classes.analytics_components import AnalyticsComponents
from .hypercube_building_classes.support_methods import SupportMethods
from .hypercube_building_classes.query_methods import QueryMethods
from .hypercube_building_classes.filter_methods import FilterMethods

# hypercube supporting classes
from .schema_validator import SchemaValidator
from .composite_bridge_generator import CompositeBridgeGenerator

class Hypercube(Engine, AnalyticsComponents, QueryMethods, FilterMethods, SupportMethods):
    def __init__(
        self,
        tables: Optional[Dict[str, pd.DataFrame]] = None,
        apply_composite=True,
        validate: bool = True,
        to_be_stored: bool = False,
    ) -> None:
        self.metrics = {}
        self.computed_metrics = {}
        self.queries = {}
        self.registered_functions = {'pd': pd, 'np': np}
        if tables is not None:
            self.load_data(
                tables,
                apply_composite=apply_composite,
                validate=validate,
                to_be_stored=to_be_stored,
                reset_all=True,
            )

    def load_data(        
        self,
        tables: Dict[str, pd.DataFrame],
        apply_composite = True,
        validate: bool = True,
        to_be_stored: bool = False,
        reset_all: bool = False
    ) -> None:
        if reset_all:
            self.metrics = {}
            self.computed_metrics = {}
            self.queries = {}
            self.registered_functions = {'pd': pd,'np': np}
        try:
            # clean data if existing
            self.tables: Dict[str, pd.DataFrame] = {}
            self.composite_tables: Optional[Dict[str, pd.DataFrame]] = {}
            self.composite_keys: Optional[Dict[str, Any]] = {}
            self.input_tables_columns = {}

            if validate:

                print("Initializing DataModel with provided tables...")
                # 1. Validate schema structure using sample data
                SchemaValidator.validate(tables)

                print("Hypercube schema validated successfully. Loading full data..")

            # Store input table columns for reference
            reduced_input_tables, _ = SchemaValidator._create_sample_tables(tables)
            for table_name in reduced_input_tables:
                self.input_tables_columns[table_name] = reduced_input_tables[table_name].columns.to_list()

            # Schema is valid, build the actual model with full data
            bridge_generator = None
            if apply_composite:
                bridge_generator = CompositeBridgeGenerator(tables)
                self.tables: Dict[str, pd.DataFrame] = bridge_generator.tables
                self.composite_tables: Optional[Dict[str, pd.DataFrame]] = bridge_generator.composite_tables
                self.composite_keys: Optional[Dict[str, Any]] = bridge_generator.composite_keys
            else:
                self.tables: Dict[str, pd.DataFrame] = tables
                self.composite_tables: Optional[Dict[str, pd.DataFrame]] = {}
                self.composite_keys: Optional[Dict[str, Any]] = {}

            self.relationships: Dict[Any, Any] = {}
            self.link_tables: Dict[str, pd.DataFrame] = {}
            self.link_table_keys: list = []
            self.column_to_table: Dict[str, str] = {}

            self._add_auto_relationships()
                
            self.relationships_raw = self.relationships.copy()  # Keep a raw copy of initial relationships
            self.relationships = {}

            # Add index columns to each table if not present
            for table in self.tables:
                index_col = f'_index_{table}'
                if index_col not in self.tables[table].columns:
                    self.tables[table].reset_index(drop=False, inplace=True)
                    self.tables[table].rename(columns={'index': index_col}, inplace=True)
            
            # Create link tables for shared columns and update the original tables
            self._create_link_tables()  # Link tables are used to join tables on shared columns

            # Build the column-to-table mapping
            self._build_column_to_table_mapping()  # Map each column to its source table
            
            # Automatically add relationships based on shared column names
            self._add_auto_relationships()  # Add relationships for columns with the same name

            self.is_cyclic = self._has_cyclic_relationships()
            if self.is_cyclic[0]:
                return None #no need to continue, there are cycle relationships

            self.context_states = {}
            self.trajectory_cache = {}

            if validate:
                self._compute_and_cache_trajectories()
                link_tables_trajectories = self._get_trajectory(self.link_tables.keys())
            else:
                link_tables_trajectories = self._find_complete_trajectory(self.link_tables)
            
            # Set the initial state to the unfiltered version of the joined trajectory keys
            self.context_states['Unfiltered'] = self._join_trajectory_keys(link_tables_trajectories)
            
            self.applied_filters = {}   # List of applied filters
            self.filter_pointer = {}    # Pointer to the current filter state

            if not to_be_stored: # If the model is intended to be stored in the disk initialize the context state "Default" after loading in memory
                self.set_context_state('Default')
            
            if not bridge_generator.composite_keys and validate:
                print("Hypercube loaded successfully")
            elif bridge_generator.composite_keys and validate:
                print("Hypercube loaded successfully with composite keys.")

        except ValueError as e:
            # Re-raise ValueError exceptions to be caught by calling code
            print(f"DataModel initialization failed: {str(e)}")
            raise
        except Exception as e:
            # Catch other exceptions, log them, and re-raise with a clear message
            print(f"An error occurred during DataModel initialization: {str(e)}")
            raise ValueError(f"DataModel initialization failed: {str(e)}")