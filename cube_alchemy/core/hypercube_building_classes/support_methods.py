
from collections import deque
import pandas as pd
from typing import Dict, List, Any, Optional

class SupportMethods:
    def find_path(
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

    def print_model(self) -> None:
        print('tables:\n')
        for table in self.tables:
            print(table, '->\n', self.tables[table], '\n\n')
        print('\nrelationships:\n ')
        for r in self.relationships:
            print(r, '-', self.relationships[r])

    def fetch_and_merge_columns(
        self,
        columns_to_fetch: List[str],
        keys_df: pd.DataFrame,
        drop_duplicates: bool = False 
    ) -> pd.DataFrame:
        table_columns_tuples = []
        table_columns = {}
        for column in columns_to_fetch:
            table_name = self.column_to_table.get(column)
            if not table_name:
                print(f"Warning: Column {column} not found in any table.")
                continue
            table_columns_tuples.append((table_name, column))
        # Group columns by table
        for table_name, column in table_columns_tuples:
            if table_name not in table_columns:
                table_columns[table_name] = []
            table_columns[table_name].append(column)
        # Now process each table's columns
        for table_name, columns in table_columns.items():
            keys_for_table = []
            for key in self.link_table_keys:
                if key in self.tables[table_name].columns:
                    keys_for_table.append(key)
            if not keys_for_table:
                print(f"Warning: No keys found for table {table_name}.")
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

    def apply_filters_to_dataframe(
        self,
        df: pd.DataFrame,
        criteria: Dict[str, List[Any]]
    ) -> pd.DataFrame:
        if criteria:
            dimensions = list(criteria.keys())
            columns_init = df.columns.tolist()  # Preserve original columns
            columns_to_fetch = [col for col in dimensions if col not in df.columns]
            if len(columns_to_fetch) > 0:
                # Fetch only columns that are not already in the DataFrame
                df = self.fetch_and_merge_columns(columns_to_fetch, df)
            # Apply filters based on the criteria
            for column, values in criteria.items():
                if column in df.columns:
                    df = df[df[column].isin(values)]
                else:
                    print(f"Warning: Column {column} not found in DataFrame.")
            return df[columns_init]  # Return DataFrame with original columns
        else:
            return df