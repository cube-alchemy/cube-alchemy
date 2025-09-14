import logging
import pandas as pd
from typing import Dict, Any, Optional, Type, Union
from pathlib import Path
import pickle

# hypercube mixins
from .hypercube_mixins.engine import Engine
from .hypercube_mixins.logger import Logger
from .hypercube_mixins.analytics_specs import AnalyticsSpecs
from .hypercube_mixins.model_catalog import ModelCatalog

# supporting components
from .schema_validator import SchemaValidator
from .composite_bridge_generator import CompositeBridgeGenerator
from .dependency_index import DependencyIndex

class Hypercube(Logger, Engine, AnalyticsSpecs, ModelCatalog):
    def __init__(
        self,
        tables: Optional[Dict[str, pd.DataFrame]] = None,
        rename_original_shared_columns: bool = True,
        apply_composite: bool = True,
        validate: bool = True,
        to_be_stored: bool = False,
        logger: Optional[Union[logging.Logger, bool]] = None,
        # Simple DI hooks for testability/extensibility
        validator_cls: Optional[Type[SchemaValidator]] = None,
        bridge_factory_cls: Optional[Type[CompositeBridgeGenerator]] = None,
        function_registry: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Initialize Logger mixins
        Logger.__init__(self, logger=logger)
        Engine.__init__(self)
        ModelCatalog.__init__(self)

        # Bind supporting components
        self._dep_index = DependencyIndex()  # Modular dependency index for queries/metrics/plots
        self._validator = validator_cls or SchemaValidator
        self._bridge_factory = bridge_factory_cls or CompositeBridgeGenerator

        # Initialize function registry (owned by Query mixin); allow extra defaults
        if function_registry:
            # Query.__init__ sets defaults; merge any provided extras
            self.function_registry.update(function_registry)

        self.rename_original_shared_columns = rename_original_shared_columns

        if tables is not None:
            self.load_data(
                tables,
                rename_original_shared_columns=rename_original_shared_columns,
                apply_composite=apply_composite,
                validate=validate,
                to_be_stored=to_be_stored,
                reset_specs=True,
            )

    def load_data(        
        self,
        tables: Dict[str, pd.DataFrame],
        rename_original_shared_columns: bool = True,
        apply_composite: bool = True,
        validate: bool = True,
        to_be_stored: bool = False,
        reset_specs: bool = False
    ) -> None:
        if reset_specs:
            self.reset_specs()
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
                    self.tables[table][index_col] = self.tables[table].index.astype('Int64')  # nullable int
            
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

            self._create_table_join_column_mapping()

            # Set the initial state to the unfiltered version of the joined trajectory keys across all the connections
            tables_trajectory = self._find_complete_trajectory(self.tables)
            self.context_states['Unfiltered'] = self._join_trajectory_keys(tables_trajectory)

            self.core = self.context_states['Unfiltered']

            # from now on, all the data will be contained in the core
            for table in self.tables:
                self.tables[table] = pd.DataFrame(columns=self.tables[table].columns)

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
    
    def save_as_pickle(
        self,
        path: Optional[Union[str, "Path"]] = None,
        *,
        relative_path: bool = True,
        pickle_name: str = "cube.pkl",
    ) -> "Path":
        """Persist the hypercube to a pickle file.

        - Uses the current working directory by default (cube.pkl).
        - Temporarily removes the logger to ensure safe pickling.
        - Function registry is pickled via import specs and rehydrated on load.
        """
        # Determine target path. If a full file path is provided, honor it.
        # Otherwise, treat `path` as a directory (relative to CWD if relative_path=True)
        # and write to `<dir>/<pickle_name>`.
        if path is None:
            base_dir = Path.cwd()
            target = base_dir / pickle_name
        else:
            p = Path(path)
            if p.suffix:  # looks like a file path
                target = p
            else:
                base_dir = (Path.cwd() / p) if relative_path else p
                target = base_dir / pickle_name
        old_log = getattr(self, "_log", None)
        try:
            if old_log is not None:
                self._log = None
            with open(target, "wb") as f:
                pickle.dump(self, f)
        finally:
            if old_log is not None:
                self._log = old_log
        return target

    @staticmethod
    def load_pickle(
        path: Optional[Union[str, "Path"]] = None,
        *,
        relative_path: bool = True,
        pickle_name: str = "cube.pkl",
    ) -> "Hypercube":
        """Load a previously saved hypercube from a pickle file.

        If `path` is a file path (has a suffix), it is used directly. Otherwise,
        it is treated as a directory (relative to CWD if `relative_path` is True),
        and `pickle_name` is appended.
        """
        if path is None:
            target = Path.cwd() / pickle_name
        else:
            p = Path(path)
            if p.suffix:
                target = p
            else:
                base_dir = (Path.cwd() / p) if relative_path else p
                target = base_dir / pickle_name
        with open(target, "rb") as f:
            return pickle.load(f)