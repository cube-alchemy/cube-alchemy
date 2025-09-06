import logging
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from collections import deque

class Engine:
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
        base_tables = [t for t in self.tables if t not in self.link_tables]
        if len(base_tables) == 1:
            t = base_tables[0]
            idx = f"_index_{t}"
            # Return just the index column as the key space
            return self.tables[t][[idx]].copy()
        # If somehow not a single-table setup, return empty frame
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
            key_columns_current = [col for col in current_data.columns if col in self.link_table_keys]
            key_columns_next = [col for col in next_table_data.columns if col in self.link_table_keys]
            current_data = pd.merge(
                current_data[key_columns_current],
                next_table_data[key_columns_next],
                left_on=key1,
                right_on=key2,
                how="outer"
            )
        return current_data

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
        keys_df: pd.DataFrame,
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
        # Process each table's columns using link table keys
        for table_name, columns in table_columns.items():
            keys_for_table: List[str] = []
            for key in self.link_table_keys:
                if key in self.tables[table_name].columns:
                    keys_for_table.append(key)
            if not keys_for_table:
                self.log().warning("Warning: No keys found for table %s.", table_name)
                continue
            columns_to_join = keys_for_table + columns
            keys_df = pd.merge(
                keys_df,
                self.tables[table_name][columns_to_join],
                on=keys_for_table,
                how='left'
            )
            if drop_duplicates:
                keys_df = keys_df.drop_duplicates()
        return keys_df

    def _fetch_and_merge_columns_single_table(
        self,
        columns_to_fetch: List[str],
        keys_df: pd.DataFrame,
        drop_duplicates: bool = False
    ) -> pd.DataFrame:
        """Lightweight single-table fetch: join using the base table index only."""
        base_table = getattr(self, "_single_table_base", None)
        if base_table is None:
            return keys_df
        idx = f"_index_{base_table}"
        # Limit to columns from the single base table
        bring = [c for c in columns_to_fetch if self.column_to_table.get(c) == base_table and c in self.tables[base_table].columns]
        if not bring:
            return keys_df
        out = keys_df
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
