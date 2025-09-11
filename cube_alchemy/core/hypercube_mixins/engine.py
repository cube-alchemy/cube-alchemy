import logging
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple, Protocol
from collections import deque

from .graph_visualizer import GraphVisualizer
from .filter import Filter
from .query import Query

class JoinStrategy(Protocol):
    """Strategy interface for joining keys and fetching columns.

    Implementations operate on the Engine context (self) and can leverage
    its tables, relationships, and metadata. Each strategy should assume
    the Engine instance has been fully initialized (link tables, mapping, etc.).
    """

    def join_trajectory_keys(self, trajectory: List[str]) -> pd.DataFrame:
        ...

    def fetch_and_merge_columns(
        self,
        columns_to_fetch: List[str],
        keys_and_indexes_df: pd.DataFrame,
        drop_duplicates: bool = False,
    ) -> pd.DataFrame:
        ...


class SingleTableJoinStrategy(JoinStrategy):
    """Join strategy for single-table models.

    Uses the base table index as the key space and performs lightweight fetches.
    """

    def __init__(self, engine: "Engine", base_table: str) -> None:
        self.engine = engine
        self.base_table = base_table

    def join_trajectory_keys(self, trajectory: List[str]) -> pd.DataFrame:
        # Delegate to existing, battle-tested helper
        return self.engine._join_trajectory_keys_single_table(trajectory)

    def fetch_and_merge_columns(
        self,
        columns_to_fetch: List[str],
        keys_and_indexes_df: pd.DataFrame,
        drop_duplicates: bool = False,
    ) -> pd.DataFrame:
        # Delegate to existing helper
        return self.engine._fetch_and_merge_columns_single_table(
            columns_to_fetch, keys_and_indexes_df, drop_duplicates
        )


class MultiTableJoinStrategy(JoinStrategy):
    """Join strategy for multi-table models.

    Walks the relationship graph and joins via link table keys.
    """

    def __init__(self, engine: "Engine") -> None:
        self.engine = engine

    def join_trajectory_keys(self, trajectory: List[str]) -> pd.DataFrame:
        return self.engine._join_trajectory_keys_multi_table(trajectory)

    def fetch_and_merge_columns(
        self,
        columns_to_fetch: List[str],
        keys_and_indexes_df: pd.DataFrame,
        drop_duplicates: bool = False,
    ) -> pd.DataFrame:
        return self.engine._fetch_and_merge_columns_multi_table(
            columns_to_fetch, keys_and_indexes_df, drop_duplicates
        )

class Engine(GraphVisualizer, Filter, Query):
    def __init__(self) -> None:
        # Initialize Query registries (metrics, derived_metrics, queries)
        Query.__init__(self)

    def _init_join_strategy(self) -> None:
        """Pick and configure the appropriate Join Strategy.

        Rules:
        - If no link keys and there is exactly one base table, use SingleTableJoinStrategy.
        - Otherwise, use MultiTableJoinStrategy.
        Side effects:
        - Sets self._single_table_mode and self._single_table_base accordingly.
        - Ensures link_table_keys contains the base index in single-table mode.
        - Installs wrappers self._join_trajectory_keys and self._fetch_and_merge_columns
          to delegate to the chosen strategy, preserving backward compatibility.
        """
        base_tables = [t for t in self.tables if t not in self.link_tables]
        if not getattr(self, "link_table_keys", None):
            self.link_table_keys = []

        if len(self.link_table_keys) == 0 and len(base_tables) == 1:
            base = base_tables[0]
            # Ensure the base index is available as a join key
            idx = f"_index_{base}"
            if idx not in self.link_table_keys:
                self.link_table_keys = [idx]

            self._single_table_mode = True
            self._single_table_base = base
            self._join_strategy: JoinStrategy = SingleTableJoinStrategy(self, base)
        else:
            self._single_table_mode = False
            self._single_table_base = None
            self._join_strategy: JoinStrategy = MultiTableJoinStrategy(self)

    # Delegating methods (stable names used by other mixins) — picklable
    def _join_trajectory_keys(self, trajectory: List[str]) -> pd.DataFrame:  # type: ignore[override]
        return self._join_strategy.join_trajectory_keys(trajectory)

    def _fetch_and_merge_columns(
        self,
        columns_to_fetch: List[str],
        keys_and_indexes_df: pd.DataFrame,
        drop_duplicates: bool = False,
    ) -> pd.DataFrame:  # type: ignore[override]
        return self._join_strategy.fetch_and_merge_columns(
            columns_to_fetch, keys_and_indexes_df, drop_duplicates
        )

    def _create_and_update_link_table(
        self,
        column: str,
        link_table_name: str,
        table_names: List[str]
    ) -> None:
        """Create a link table for the shared column and update the original tables with keys."""
        link_table = pd.DataFrame()
        for table_name in table_names:
            unique_values = self.tables[table_name][[column]].drop_duplicates()
            link_table = pd.concat([link_table, unique_values], ignore_index=True).drop_duplicates()
        link_table[f'_key_{column}'] = range(1, len(link_table) + 1)
        self.link_table_keys.append(f'_key_{column}')
        self.tables[link_table_name] = link_table
        self.link_tables[link_table_name] = link_table
        for table_name in table_names:
            self.tables[table_name] = pd.merge(
                self.tables[table_name],
                link_table,
                on=column,
                how='left'
            )
            #rename or drop the column to differentiate it from the original column
            if self.rename_original_shared_columns:
                self.tables[table_name].rename(columns={column: f'{column} <{table_name}>'}, inplace=True)
            else:
                self.tables[table_name].drop(columns=[column], inplace=True)

    def _add_auto_relationships(self) -> None:
        table_names = list(self.tables.keys())
        for i in range(len(table_names)):
            for j in range(i + 1, len(table_names)):
                table1 = table_names[i]
                table2 = table_names[j]
                common_columns = set(self.tables[table1].columns).intersection(set(self.tables[table2].columns))
                for column in common_columns:
                    self._add_relationship(table1, table2, column, column)

    def _add_table(
        self,
        table_name: str,
        table_data: pd.DataFrame
    ) -> None:
        self.tables[table_name] = table_data
    # I chose to leave it as a pair as, even currently the model's schema is assuming implicit relationships by column names, it could be adapted to use explicit (and even uni-directional? - need to think more about this -) relationships in the future.
    def _add_relationship(
        self,
        table1_name: str,
        table2_name: str,
        key1: str,
        key2: str
    ) -> Optional[bool]:
        if not self.link_tables:
            if key1 in [item for sublist in self.composite_keys.values() for item in sublist] and not (table2_name in self.composite_tables or table1_name in self.composite_tables):
                return True
            else:
                self.relationships[(table1_name, table2_name)] = (key1, key2)
                self.relationships[(table2_name, table1_name)] = (key2, key1)
        elif (table1_name in self.link_tables or table2_name in self.link_tables):
            self.relationships[(table1_name, table2_name)] = (key1, key2)
            self.relationships[(table2_name, table1_name)] = (key2, key1)
        return None

    def _build_column_to_table_mapping(self) -> None:
        for table_name, table in self.tables.items():
            for column in table.columns:
                self.column_to_table[column] = table_name

    def _create_link_tables(self) -> None:
        all_columns = {}
        for table_name, table_data in self.tables.items():
            for column in table_data.columns:
                if column not in all_columns:
                    all_columns[column] = []
                all_columns[column].append(table_name)
        for column, table_names in all_columns.items():
            if len(table_names) > 1:
                link_table_name = f'_link_table_{column}'
                self._create_and_update_link_table(column, link_table_name, table_names)

    def _find_complete_trajectory(
        self,
        target_tables: Dict[str, pd.DataFrame]
    ) -> List[str]:
        if not target_tables:
            return []
        target_table_list = list(target_tables.keys())
        start_table = target_table_list[0]
        trajectory = [start_table]
        for i in range(1, len(target_table_list)):
            next_table = target_table_list[i]
            path = self._find_path(start_table, next_table)
            if path:
                for step in path:
                    trajectory.append(step[0])
                    trajectory.append(step[1])
            else:
                for table in self.tables:
                    path_with_intermediate = self._find_path(start_table, table)
                    path_to_next = self._find_path(table, next_table)
                    if path_with_intermediate and path_to_next:
                        for step in path_with_intermediate + path_to_next:
                            trajectory.append(step[0])
                            trajectory.append(step[1])
                        break
            start_table = next_table
        final_trajectory = []
        for i in range(len(trajectory)):
            if i == 0 or trajectory[i] != trajectory[i - 1]:
                final_trajectory.append(trajectory[i])
        return final_trajectory

    def _join_trajectory_keys_single_table(self, trajectory: List[str]) -> Any:
        """Single-table key space: return the unique index column of the base table."""
        base = getattr(self, "_single_table_base", None)
        if base is None:
            # Not in single-table mode
            return pd.DataFrame()
        idx = f"_index_{base}"
        # Return just the index column as the key space if present
        if idx in self.tables.get(base, pd.DataFrame()).columns:
            return self.tables[base][[idx]].copy()
        return pd.DataFrame()

    def _join_trajectory_keys_multi_table(self, trajectory: List[str]) -> Any:
        """Multi-table key space: walk the trajectory via relationships and link keys."""
        if not trajectory:
            # No trajectory for multi-table implies no link connectivity
            return pd.DataFrame()
        current_table = trajectory[0]
        current_data = self.tables[current_table]
        visited_tables = [current_table]
        for i in range(len(trajectory) - 1):
            table1 = trajectory[i]
            table2 = trajectory[i + 1]
            if table2 in visited_tables:
                continue
            visited_tables.append(table2)
            key1, key2 = self.relationships.get((table1, table2), (None, None))
            if key1 is None or key2 is None:
                raise ValueError(f"No relationship found between {table1} and {table2}")
            next_table_data = self.tables[table2]
            columns_current = [col for col in current_data.columns if col in self.link_table_keys or col.startswith('_index_')]
            columns_next = [col for col in next_table_data.columns if col in self.link_table_keys or col.startswith('_index_')]
            current_data = pd.merge(
                current_data[columns_current],
                next_table_data[columns_next],
                left_on=key1,
                right_on=key2,
                how="outer"
            )
        # get only index columns
        #index_columns = [col for col in current_data.columns if col.startswith('_index_')]
        #current_data = current_data[index_columns].drop_duplicates()
        return current_data.drop_duplicates()

    def _has_cyclic_relationships(self) -> Tuple[bool, List[Any]]:
        def dfs(node: str, visited: set, path: List[str], parent: Optional[str]) -> List[str]:
            visited.add(node)
            path.append(node)
            
            # Get all connected tables (excluding the parent we came from)
            connected_tables = set(table2 for (table1, table2) in self.relationships.keys() 
                                if table1 == node and table2 != parent)
            
            for next_node in connected_tables:
                if next_node not in visited:
                    cycle = dfs(next_node, visited, path, node)
                    if cycle:
                        return cycle
                # If we find a visited node that's in our path and isn't our immediate parent
                elif next_node in path and next_node != parent:
                    # Found a cycle
                    cycle_start = path.index(next_node)
                    return path[cycle_start:]
            
            path.pop()
            return []

        visited = set()
        
        # Get unique table names (nodes)
        tables = set(table for pair in self.relationships.keys() for table in pair)
        
        # Check from each unvisited node
        for table in tables:
            if table not in visited:
                cycle = dfs(table, visited, [], None)
                if cycle:
                    return True, cycle

        return False, []   

    def _get_trajectory(self,tables_to_find):
        return self._find_complete_trajectory(tables_to_find)
    
    def _find_path(
        self,
        start_table: str,
        end_table: str
    ) -> Optional[List[Any]]:
        queue = deque([(start_table, [])])
        visited = {start_table}
        while queue:
            current_table, path = queue.popleft()
            if current_table == end_table:
                return path
            for (neighbor_table, (key1, key2)) in self.relationships.items():
                if neighbor_table[0] == current_table and neighbor_table[1] not in visited:
                    visited.add(neighbor_table[1])
                    queue.append((neighbor_table[1], path + [(neighbor_table[0], neighbor_table[1], key1, key2)]))
        return None

    def _fetch_and_merge_columns_multi_table(
        self,
        columns_to_fetch: List[str],
        keys_and_indexes_df: pd.DataFrame,
        drop_duplicates: bool = False
    ) -> pd.DataFrame:
        """Fast multi-table path: group by table and join on link keys."""
        table_columns_tuples: List[tuple] = []
        table_columns: Dict[str, List[str]] = {}
        for column in columns_to_fetch:
            table_name = self.column_to_table.get(column)
            if not table_name:
                self.log().warning("Warning: Column %s not found in any table.", column)
                continue
            table_columns_tuples.append((table_name, column))
        # Group columns by table
        for table_name, column in table_columns_tuples:
            if table_name not in table_columns:
                table_columns[table_name] = []
            table_columns[table_name].append(column)
        # Process each table's columns using link table keys and table index
        for table_name, columns in table_columns.items():
            keys_and_index_for_table: List[str] = []
            for column in self.tables[table_name].columns:
                if column.startswith('_index_') or column.startswith('_key_'):
                    keys_and_index_for_table.append(column)
            if not keys_and_index_for_table:
                self.log().warning("Warning: No keys or index found for table %s.", table_name)
                continue
            columns_to_join = keys_and_index_for_table + columns
            keys_and_indexes_df = pd.merge(
                keys_and_indexes_df,
                self.tables[table_name][columns_to_join],
                on=keys_and_index_for_table,
                how='left'
            )
            if drop_duplicates:
                keys_and_indexes_df = keys_and_indexes_df.drop_duplicates()
        return keys_and_indexes_df

    def _fetch_and_merge_columns_single_table(
        self,
        columns_to_fetch: List[str],
        keys_and_indexes_df: pd.DataFrame,
        drop_duplicates: bool = False
    ) -> pd.DataFrame:
        """Lightweight single-table fetch: join using the base table index only."""
        base_table = getattr(self, "_single_table_base", None)
        if base_table is None:
            return keys_and_indexes_df
        idx = f"_index_{base_table}"
        # Limit to columns from the single base table
        bring = [c for c in columns_to_fetch if self.column_to_table.get(c) == base_table and c in self.tables[base_table].columns]
        if not bring:
            return keys_and_indexes_df
        out = keys_and_indexes_df
        if out.empty:
            # Seed with index + requested columns
            cols = [idx] + bring if idx in self.tables[base_table].columns else bring
            out = self.tables[base_table][cols].copy()
            if drop_duplicates:
                out = out.drop_duplicates()
            return out
        # If index exists, merge directly
        if idx in out.columns and idx in self.tables[base_table].columns:
            right = self.tables[base_table][[idx] + bring].drop_duplicates()
            out = pd.merge(out, right, on=[idx], how='left')
            if drop_duplicates:
                out = out.drop_duplicates()
            return out
        # No safe join key available; return as-is
        return out

    def relationship_matrix(self, context_state_name: str = 'Unfiltered') -> pd.DataFrame:
        # The real relationship matrix is self.core, which hold the autonumbered keys
        # and the relationships between them. Here we reconstruct the original shared columns values.

        # Our shared columns are in the link tables and composite tables
        base_tables = self.link_tables.keys() | self.composite_tables.keys()
        shared_columns: List[str] = []
        for table in base_tables:
            for col in self.tables[table].columns:
                if not (col.startswith('_key_') or col.startswith('_composite_') or col.startswith('_index_')):
                    shared_columns.append(col)
        return self.dimensions(columns_to_fetch=shared_columns, retrieve_keys=False, context_state_name=context_state_name)

    def get_cardinalities(self, context_state_name = 'Unfiltered', include_inverse: bool = False) -> pd.DataFrame:
        """
        For every shared key, compute relationship cardinality between each pair of base tables,
        based on per-key row multiplicities in the intersection of keys. Does not mutate tables.

        Parameters
        - include_inverse: when True, also emits the inverse orientation (t2, t1) rows
          without recomputing; e.g., one-to-many <-> many-to-one. This is derived from
          the computed result for (t1, t2).
        """
        base_tables = [t for t in self.tables if t not in self.link_tables]
        shared_keys = list(self.core.columns)

        results: List[Dict[str, Any]] = []
        for key in shared_keys:
            tables_sharing_key = [t for t in base_tables if key in self.tables[t].columns]
            for i in range(len(tables_sharing_key)):
                for j in range(i + 1, len(tables_sharing_key)):
                    t1, t2 = tables_sharing_key[i], tables_sharing_key[j]

                    if context_state_name == 'Unfiltered': #simmplest case, no need to filter by context state and use all values
                        s1 = self.tables[t1][key].dropna()
                        s2 = self.tables[t2][key].dropna()
                    else:
                        #If I want to use the context state, I need to get the relevant values first.. I can use the indexes of the tables
                        idx1 = self.dimension(f'_index_{t1}', context_state_name=context_state_name)
                        idx2 = self.dimension(f'_index_{t2}', context_state_name=context_state_name)

                        #I need to first filter the tables by the context state indexes and then get the relevant key columns. idx1 and idx2 are pandas series with the relevant indexes

                        s1 = self.tables[t1][self.tables[t1][f'_index_{t1}'].isin(idx1)][key].dropna()
                        s2 = self.tables[t2][self.tables[t2][f'_index_{t2}'].isin(idx2)][key].dropna()

                    if s1.empty or s2.empty:
                        results.append({"table1": t1, "table2": t2, "shared_key": key, "cardinality": "no relationship"})
                        continue

                    c1 = s1.value_counts()
                    c2 = s2.value_counts()
                    inter = c1.index.intersection(c2.index)

                    if len(inter) == 0:
                        cardinality = "no relationship"
                        max1 = max2 = 0
                    else:
                        max1 = int(c1.loc[inter].max())
                        max2 = int(c2.loc[inter].max())
                        if max1 == 1 and max2 == 1:
                            cardinality = "one-to-one"
                        elif max1 == 1 and max2 > 1:
                            cardinality = "one-to-many"
                        elif max1 > 1 and max2 == 1:
                            cardinality = "many-to-one"
                        else:
                            cardinality = "many-to-many"

                    # shared column is the key without the _key_ prefix
                    shared_column = key[len("_key_"):]
                    if t1.startswith('_composite_'):
                        t1 = "Composite Table"
                    if t2.startswith('_composite_'):
                        t2 = "Composite Table"

                    results.append({
                        "table1": t1,
                        "table2": t2,
                        #"key": key,
                        "shared_column": shared_column,
                        "cardinality": cardinality,
                        "keys_in_t1": int(c1.size),
                        "keys_in_t2": int(c2.size),
                        "keys_in_both": int(len(inter)),
                        "max_rows_per_key_t1": int(max1),
                        "max_rows_per_key_t2": int(max2),
                    })

        df = pd.DataFrame(results)

        if not include_inverse or df.empty:
            return df

        # Build inverse orientation cheaply, without re-counting
        inverse_map = {
            "one-to-one": "one-to-one",
            "one-to-many": "many-to-one",
            "many-to-one": "one-to-many",
            "many-to-many": "many-to-many",
            "no relationship": "no relationship",
        }

        inv = df.copy()
        inv["table1"], inv["table2"] = df["table2"], df["table1"]
        inv["cardinality"] = df["cardinality"].map(inverse_map).fillna(df["cardinality"])  # safety
        inv["max_rows_per_key_t1"], inv["max_rows_per_key_t2"] = df["max_rows_per_key_t2"], df["max_rows_per_key_t1"]
        inv["keys_in_t1"], inv["keys_in_t2"] = df["keys_in_t2"], df["keys_in_t1"]

        # Concatenate and return; original rows are unique per unordered pair and key
        return pd.concat([df, inv], ignore_index=True)