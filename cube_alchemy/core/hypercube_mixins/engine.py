import logging
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from collections import deque

from .graph_visualizer import GraphVisualizer
from .filter import Filter
from .query import Query

class Engine(GraphVisualizer, Filter, Query):
    def __init__(self) -> None:
        # Initialize Query registries (metrics, derived_metrics, queries)
        Query.__init__(self)

    # Unified methods (stable names used by other mixins)
    def _join_trajectory_keys(self, trajectory: List[str]) -> pd.DataFrame:
        """Build the key space from a trajectory using per-table indexes and link keys.

        - If trajectory is empty but there's a single table, return that table's key/index columns.
        - Otherwise, walk the trajectory and outer-join on relationship keys, keeping only
          columns that are indexes or link keys to define the key space.
        """
        def key_cols(df: pd.DataFrame) -> List[str]:
            return [c for c in df.columns if c.startswith('_index_') or c.startswith('_key_')]

        if not trajectory:
            # No path: treat single-table as a degenerate case, otherwise empty
            base_tables = list(self.tables.keys())
            if len(base_tables) == 1:
                t = base_tables[0]
                cols = key_cols(self.tables[t])
                return self.tables[t][cols].drop_duplicates() if cols else pd.DataFrame()
            return pd.DataFrame()

        current_table = trajectory[0]
        current_data = self.tables[current_table][key_cols(self.tables[current_table])].drop_duplicates()
        visited = {current_table}
        for i in range(len(trajectory) - 1):
            t1 = trajectory[i]
            t2 = trajectory[i + 1]
            if t2 in visited:
                continue
            visited.add(t2)
            key1, key2 = self.relationships.get((t1, t2), (None, None))
            if key1 is None or key2 is None:
                raise ValueError(f"No relationship found between {t1} and {t2}")
            next_data = self.tables[t2][key_cols(self.tables[t2])].drop_duplicates()

            if key1 in current_data.columns and key2 in next_data.columns:
                current_data = pd.merge(current_data, next_data, left_on=key1, right_on=key2, how='outer')
            else:
                shared = [c for c in current_data.columns if c in next_data.columns]
                if shared:
                    current_data = pd.merge(current_data, next_data, on=shared, how='outer')
                else:
                    # Expand key-space safely without data columns
                    current_data['_tmp_1'] = 1
                    next_data['_tmp_1'] = 1
                    current_data = pd.merge(current_data, next_data, on=['_tmp_1'], how='outer').drop(columns=['_tmp_1'])

            current_data = current_data.drop_duplicates()

        return current_data

    def _create_table_join_column_mapping(self) -> Dict[str, str]:
        """
        Create a mapping of each table to its primary join column (index or key).
        It's a bit more efficient to precompute this once and reuse it.
        """
        table_join_map: Dict[str, str] = {}
        for table_name, table in self.tables.items():
            idx_cols = [c for c in table.columns if c.startswith('_index_')]
            key_cols = [c for c in table.columns if c.startswith('_key_')]
            if idx_cols:
                table_join_map[table_name] = idx_cols[0]
            elif key_cols:
                table_join_map[table_name] = key_cols[0]
            else:
                logging.warning(f"No index or key column found for table {table_name}.")
        
        # Store for further use
        self._table_join_column_map = table_join_map
    
    def _fetch_and_merge_columns(
        self,
        columns_to_fetch: List[str],
        keys_and_indexes_df: pd.DataFrame
    ) -> pd.DataFrame:  
        """Bring requested columns into the current index-key space.
        - Groups requested columns by their source table.
        - Joins on that table's index if present, otherwise on its link key(s).
        """
        # Group columns by table (we can join once per table)
        by_table: Dict[str, List[str]] = {}
        for col in columns_to_fetch:
            t = self.column_to_table.get(col)
            if not t:
                self.log().warning("Warning: Column %s not found in any table.", col)
                continue
            by_table.setdefault(t, []).append(col)

        out = keys_and_indexes_df
        for table_name, cols in by_table.items():
            table_df = self.tables[table_name]
            join_column = self._table_join_column_map.get(table_name)
            if not join_column:
                self.log().warning("Warning: No index or key found for table %s.", table_name)
                continue

            # Select join columns plus requested columns (requested columns don't include join cols)
            select_cols = [join_column] + cols
            right = table_df[select_cols]

            out = pd.merge(out, right, on=join_column, how='left')

        return out

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
        # Assign link keys as nullable integers to safely handle joins that introduce NAs
        link_table[f'_key_{column}'] = pd.Series(
            range(1, len(link_table) + 1), dtype='Int64'
        )
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

    def relationship_matrix(self, context_state_name: str = 'Unfiltered', core = False) -> pd.DataFrame:
        if core:
            stateful_core = self.context_states[context_state_name]
            return stateful_core[sorted(stateful_core.columns)]

        # Here we reconstruct the original shared columns values.
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
    

