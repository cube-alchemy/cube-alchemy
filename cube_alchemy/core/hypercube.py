import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

# hypercube building classes
from .hypercube_building_classes.engine import Engine
from .hypercube_building_classes.graph_visualizer import GraphVisualizer
from .hypercube_building_classes.analytics_components import AnalyticsComponents
from .hypercube_building_classes.support_methods import SupportMethods
from .hypercube_building_classes.query_methods import QueryMethods
from .hypercube_building_classes.filter_methods import FilterMethods
from .hypercube_building_classes.plotting_components import PlottingComponents

# hypercube supporting classes
from .schema_validator import SchemaValidator
from .composite_bridge_generator import CompositeBridgeGenerator

class Hypercube(Engine, GraphVisualizer, AnalyticsComponents, QueryMethods, FilterMethods, SupportMethods, PlottingComponents):
    def __init__(
        self,
        tables: Optional[Dict[str, pd.DataFrame]] = None,
        rename_original_shared_columns: bool = True,
        apply_composite=True,
        validate: bool = True,
        to_be_stored: bool = False,
    ) -> None:
        # Initialize the PlottingComponents class
        PlottingComponents.__init__(self)
        
        self.metrics = {}
        self.computed_metrics = {}
        self.queries = {}
        self.registered_functions = {'pd': pd, 'np': np}
        self.rename_original_shared_columns = rename_original_shared_columns
        if tables is not None:
            self.load_data(
                tables,
                rename_original_shared_columns=rename_original_shared_columns,
                apply_composite=apply_composite,
                validate=validate,
                to_be_stored=to_be_stored,
                reset_all=True,
            )

    def load_data(        
        self,
        tables: Dict[str, pd.DataFrame],
        rename_original_shared_columns: bool = True,
        apply_composite: bool = True,
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
                list_of_tables = list(tables.keys())
                print("Initializing DataModel with provided tables:", list_of_tables)
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
                bridge_generator = CompositeBridgeGenerator(tables=tables, rename_original_shared_columns=rename_original_shared_columns)
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
                    # Make a fresh, guaranteed-unique surrogate key
                    self.tables[table].reset_index(drop=True, inplace=True)
                    self.tables[table][index_col] = self.tables[table].index.astype('int64')
            
            # Create link tables for shared columns and update the original tables
            self._create_link_tables()  # Link tables are used to join tables on shared columns

            # Build the column-to-table mapping
            self._build_column_to_table_mapping()  # Map each column to its source table

            # Automatically add relationships based on shared column names
            self._add_auto_relationships()  # Add relationships for columns with the same name

            # If there are no link keys and exactly one base table, declare the table index as the key space. This way it's easy to use and keep the hypercube functionality intact.
            base_tables = [t for t in self.tables if t not in self.link_tables]
            if not self.link_table_keys and len(base_tables) == 1:
                self.link_table_keys = [f"_index_{base_tables[0]}"]
                # Enable light single-table mode 
                self._single_table_mode = True
                self._single_table_base = base_tables[0]
                # Register single-table fetcher
                self._fetch_and_merge_columns = self._fetch_and_merge_columns_single_table
                # Register single-table trajectory joiner
                self._join_trajectory_keys = self._join_trajectory_keys_single_table
            else:
                self._single_table_mode = False
                self._single_table_base = None
                # Register multi-table fetcher
                self._fetch_and_merge_columns = self._fetch_and_merge_columns_multi_table
                # Register multi-table trajectory joiner
                self._join_trajectory_keys = self._join_trajectory_keys_multi_table

            self.is_cyclic = self._has_cyclic_relationships()
            if self.is_cyclic[0]:
                return None #no need to continue, there are cycle relationships

            self.context_states = {}

            # Set the initial state to the unfiltered version of the joined trajectory keys across all the connections
            link_tables_trajectory = self._find_complete_trajectory(self.link_tables)
            self.context_states['Unfiltered'] = self._join_trajectory_keys(link_tables_trajectory)

            self.applied_filters = {}   # List of applied filters
            self.filter_pointer = {}    # Pointer to the current filter state

            if not to_be_stored: # If the model is intended to be stored in the disk initialize the context state "Default" after loading in memory
                self.set_context_state('Default')
            
            if validate:
                if getattr(self, 'composite_keys', None):
                    if len(self.composite_keys) > 0:
                        print("Hypercube loaded successfully with composite keys.")
                    else:
                        print("Hypercube loaded successfully")
                else:
                    print("Hypercube loaded successfully")

        except ValueError as e:
            # Re-raise ValueError exceptions to be caught by calling code
            print(f"DataModel initialization failed: {str(e)}")
            raise
        except Exception as e:
            # Catch other exceptions, log them, and re-raise with a clear message
            print(f"An error occurred during DataModel initialization: {str(e)}")
            raise ValueError(f"DataModel initialization failed: {str(e)}")