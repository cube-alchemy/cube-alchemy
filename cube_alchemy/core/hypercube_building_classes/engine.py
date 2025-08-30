import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from itertools import combinations
import time

# for the visualize_graph method:
import networkx as nx
import matplotlib.pyplot as plt
import re

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
            #rename the column to differentiate it from the original column
            self.tables[table_name].rename(columns={column: f'{column} <{table_name}>'}, inplace=True)

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
    
    def visualize_graph(
        self,
        layout_type: str = 'spring',
        w: int = 20,
        h: int = 14,
        full_column_names: bool = True 
    ) -> None:
        graph = nx.DiGraph()
        node_labels = {}
        for table_name, df in self.tables.items():
            # Use all columns but the internal use ones
            columns = [col for col in df.columns if not col.startswith('_key_') and not col.startswith('_index_') and not col.startswith('_composite_key_')]
            if table_name.startswith('_composite_') or not full_column_names:
                columns = [re.sub(r' <.*>', '', col) for col in columns]         
            columns_str = "\n".join(columns)  
            if table_name in self.link_tables:
                label = table_name.replace('_link_table_', '').replace('_composite_key_', '_c_')
            else:
                if table_name.startswith('_composite_'):
                    _len_ct = len('Composite Table')
                    label = f"Composite Table\n{'-' * _len_ct}\n{columns_str}"
                else:
                    label = f"{table_name}\n{'-' * len(table_name)}\n{columns_str}"
            graph.add_node(table_name)
            node_labels[table_name] = label
        for (table1, table2), (key1, key2) in self.relationships.items():
            graph.add_edge(table1, table2)
        if layout_type == 'spring':
            pos = nx.spring_layout(graph)
        elif layout_type == 'circular':
            pos = nx.circular_layout(graph)
        elif layout_type == 'shell':
            pos = nx.shell_layout(graph)
        elif layout_type == 'random':
            pos = nx.random_layout(graph)
        elif layout_type == 'kamada_kawai':
            pos = nx.kamada_kawai_layout(graph)
        elif layout_type == 'spectral':
            pos = nx.spectral_layout(graph)
        elif layout_type == 'planar':
            pos = nx.planar_layout(graph)
        elif layout_type == 'spiral':
            pos = nx.spiral_layout(graph)
        else:
            raise ValueError(f"Unknown layout type: {layout_type}")
        plt.figure(figsize=(w, h))
        nx.draw(graph, pos, with_labels=False, node_size=4000, node_color='white', font_size=8, arrows=True)
        nx.draw_networkx_labels(graph, pos, labels=node_labels, font_size=9, font_family="sans-serif")
        edge_labels = nx.get_edge_attributes(graph, 'label')
        nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_color='red')
        plt.title("Tables and Relationships")
        plt.show()

    def set_context_state(
        self,
        context_state_name: str,
        base_context_state_name: str = 'Unfiltered'
    ) -> bool:
        if context_state_name == 'Unfiltered':
            raise ValueError("Cannot use 'Unfiltered' state name. Please use a different state name.")
        try:
            self.context_states[context_state_name] = self.context_states[base_context_state_name].copy()
            self.applied_filters[context_state_name]  =  [] 
            self.filter_pointer[context_state_name]  = 0 
            return True
        except Exception as e:
            print(f"Error setting state '{context_state_name}': {e}")
            return False
