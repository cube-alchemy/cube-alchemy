import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Type

# hypercube mixins
from .hypercube_mixins.engine import Engine
from .hypercube_mixins.graph_visualizer import GraphVisualizer
from .hypercube_mixins.model_catalog import ModelCatalog
from .hypercube_mixins.analytics_specs import AnalyticsSpecs
from .hypercube_mixins.filter import Filter
from .hypercube_mixins.query import Query
from .hypercube_mixins.plotting import Plotting
from .hypercube_mixins.enrichment import Enrichment
from .hypercube_mixins.logger import Logger

# supporting components
from .schema_validator import SchemaValidator
from .composite_bridge_generator import CompositeBridgeGenerator
from .dependency_index import DependencyIndex

class Hypercube(Logger, Engine, GraphVisualizer, ModelCatalog, AnalyticsSpecs, Filter, Query, Plotting, Enrichment):
    def __init__(
        self,
        tables: Optional[Dict[str, pd.DataFrame]] = None,
        rename_original_shared_columns: bool = True,
        apply_composite: bool = True,
        validate: bool = True,
        to_be_stored: bool = False,
        logger: Optional[logging.Logger] = None,
        # Simple DI hooks for testability/extensibility
        validator_cls: Optional[Type[SchemaValidator]] = None,
        bridge_factory_cls: Optional[Type[CompositeBridgeGenerator]] = None,
    ) -> None:
        # Initialize the Plotting class
        Plotting.__init__(self)
        # Initialize the Enrichment class
        Enrichment.__init__(self)
        # Initialize the ModelCatalog component
        ModelCatalog.__init__(self)

        # Logger (optional)
        self._log = logger or logging.getLogger(__name__)

        # Bind supporting components
        self._dep_index = DependencyIndex()  # Modular dependency index for queries/metrics/plots
        self._validator = validator_cls or SchemaValidator
        self._bridge_factory = bridge_factory_cls or CompositeBridgeGenerator

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
            # Clear dependency graph when resetting model
            if hasattr(self, '_dep_index'):
                self._dep_index.clear()
        try:
            # clean data if existing
            self.tables: Dict[str, pd.DataFrame] = {}
            self.composite_tables: Optional[Dict[str, pd.DataFrame]] = {}
            self.composite_keys: Optional[Dict[str, Any]] = {}
            self.input_tables_columns = {}

            if validate:
                list_of_tables = list(tables.keys())
                self._log.info("Initializing DataModel with provided tables: %s", list_of_tables)
                # 1. Validate schema structure using sample data
                self._validator.validate(tables)

                self._log.info("Hypercube schema validated successfully. Loading full data..")

            # Store input table columns for reference
            reduced_input_tables, _ = self._validator._create_sample_tables(tables)
            for table_name in reduced_input_tables:
                self.input_tables_columns[table_name] = reduced_input_tables[table_name].columns.to_list()

            # Schema is valid, build the actual model with full data
            bridge_generator = None
            if apply_composite:
                bridge_generator = self._bridge_factory(tables=tables, rename_original_shared_columns=rename_original_shared_columns)
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

            # Pick the appropriate join strategy (Single vs Multi) and expose wrappers
            self._init_join_strategy()

            self.is_cyclic = self._has_cyclic_relationships()
            if self.is_cyclic[0]:
                return None #no need to continue, there are cycle relationships

            self.context_states = {}

            # Set the initial state to the unfiltered version of the joined trajectory keys across all the connections
            link_tables_trajectory = self._find_complete_trajectory(self.link_tables)
            self.context_states['Unfiltered'] = self._join_trajectory_keys(link_tables_trajectory)

            self.core = self.context_states['Unfiltered']

            self.applied_filters = {}   # List of applied filters
            self.filter_pointer = {}    # Pointer to the current filter state

            if not to_be_stored: # If the model is intended to be stored in the disk initialize the context state "Default" after loading in memory
                self.set_context_state('Default')
            
            if validate:
                if getattr(self, 'composite_keys', None):
                    if len(self.composite_keys) > 0:
                        self._log.info("Hypercube loaded successfully with composite keys.")
                    else:
                        self._log.info("Hypercube loaded successfully")
                else:
                    self._log.info("Hypercube loaded successfully")

        except ValueError as e:
            # Re-raise ValueError exceptions to be caught by calling code
            self._log.error("DataModel initialization failed: %s", str(e))
            raise
        except Exception as e:
            # Catch other exceptions, log them, and re-raise with a clear message
            self._log.exception("An error occurred during DataModel initialization: %s", str(e))
            raise ValueError(f"DataModel initialization failed: {str(e)}")