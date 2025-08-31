import networkx as nx
import matplotlib.pyplot as plt
import re
from typing import Optional

class GraphVisualizer:    
    def visualize_graph(
        self,
        w: Optional[float] = None,
        h: Optional[float] = None,
        full_column_names: bool = False,
        seed: Optional[int] = None,  # seed for layout reproducibility
        show: bool = True,            # control plt.show()
        return_fig: bool = False      # return the Matplotlib Figure for programmatic use
    ):
        
        
        graph = nx.DiGraph()
        node_labels = {}

        for table_name, df in self.tables.items():
            # Use all columns but the internal use ones
            columns = [
                col.replace('_composite_key_', '_c_').replace('_key_','') for col in df.columns.to_list()
                if not col.startswith('_index_')
                and not col.startswith('_composite_key_')
            ]
            if not full_column_names:
                # When not showing full names, exclude columns that carry a table-suffix like ' <table>' entirely
                columns = [col for col in columns if not re.search(r' <.*>', col)]

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

        # Add edges and (optionally) set labels for them
        for (table1, table2), (key1, key2) in self.relationships.items():
            graph.add_edge(table1, table2, label=f"{key1} -> {key2}")

        pos = nx.spring_layout(graph, seed=seed)

        # Separate link tables vs normal tables (used for edge styling and nodes)
        link_nodes = set(self.link_tables)
        normal_nodes = [n for n in graph.nodes if n not in link_nodes]

        # Determine figure size: autosize only if user didn't pass w/h (None)
        def _autosize(n_nodes: int):
            base_w, base_h = 20.0, 14.0
            if n_nodes <= 6:
                return base_w, base_h
            s = (max(6, n_nodes) / 6.0) ** 0.6
            w_new = max(16.0, min(48.0, round(base_w * s, 1)))
            h_new = max(10.0, min(36.0, round(base_h * s, 1)))
            return w_new, h_new

        if w is None or h is None:
            aw, ah = _autosize(len(normal_nodes))
            if w is None:
                w = aw
            if h is None:
                h = ah

        fig, ax = plt.subplots(figsize=(w, h))

        # Draw edges first. For edges touching link-nodes, hide arrowheads to avoid
        # an arrow tip under the label (treat them like split points on a line).
        all_edges = list(graph.edges())
        link_edges = [(u, v) for (u, v) in all_edges if u in link_nodes or v in link_nodes]
        normal_edges = [(u, v) for (u, v) in all_edges if u not in link_nodes and v not in link_nodes]

        if normal_edges:
            nx.draw_networkx_edges(
                graph, pos, edgelist=normal_edges, ax=ax,
                arrows=True, arrowstyle='-|>', arrowsize=12, width=1.2
            )
        if link_edges:
            nx.draw_networkx_edges(
                graph, pos, edgelist=link_edges, ax=ax,
                arrows=False, width=1.2
            )
        

        # Draw link tables either as label-only split points (edge-like)
        # Hide their markers entirely but keep them in layout as split points
        nx.draw_networkx_nodes(
            graph, pos, nodelist=list(link_nodes), ax=ax,
            node_size=1, alpha=0
        )
        nx.draw_networkx_labels(
            graph, pos, labels={n: node_labels[n] for n in link_nodes},
            font_size=9, font_family="sans-serif", ax=ax,
            bbox=dict(boxstyle='round,pad=0.25', fc='lemonchiffon', ec='peru', lw=1.0)
        )

        # Draw normal tables as “boxed labels” (table-like)
        if normal_nodes:
            # Hide the circular markers by drawing transparent tiny nodes
            nx.draw_networkx_nodes(
                graph, pos, nodelist=normal_nodes, ax=ax,
                node_size=1, alpha=0
            )
            nx.draw_networkx_labels(
                graph, pos, labels={n: node_labels[n] for n in normal_nodes}, ax=ax,
                font_size=9, font_family="sans-serif",
                bbox=dict(boxstyle='round,pad=0.4', fc='white', ec='black', lw=1.1)
            )

        ax.set_title("Tables and Relationships")
        ax.set_axis_off()

        if show:
            plt.show()
        if return_fig:
            return fig