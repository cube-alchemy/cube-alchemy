# The Hypercube

A hypercube is a multidimensional data structure that organizes information across multiple dimensions simultaneously. In data analysis, it extends beyond two-dimensional tables to create a unified view that connects related data across multiple attributes.

In Cube Alchemy, the Hypercube brings multiple DataFrames together into a single, logical structure you can query consistently. Instead of manually joining tables, it dynamically connects your data.

At a glance:

- Directed Acyclic Graph **(DAG)**

    - *Nodes* are your DataFrames.

    - *Edges* are the shared column names that connect them.

- **Queries'** *dimensions* and *metrics* can traverse these connections (multi-hop) to combine the pieces your analysis needs. You define the metrics and queries once, and they work consistently across your analysis using a *context state* managed with *filters*.

**Note**

To be able to multi-hop through the related tables, we need to **avoid cyclic relationships** (also called circular references), as this breaks the logic of data traversal and aggregation. So you need to make sure your model is a *directed acyclic graph (DAG)*.