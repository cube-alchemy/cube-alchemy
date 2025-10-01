# Relationships in Cube Alchemy

Cube Alchemy uses implicit relationships, meaning DataFrames automatically connect to each other through shared column names.

These relationships enable declarative work with newly connected data. The library handles the necessary data operations under the hood.

At a high level, Cube Alchemy scans tables for shared columns, creates link/composite tables with auto keys when needed, and stores a relationship map plus join keys. Downstream operations (dimensions, metrics, queries) traverse this map to fetch only the columns required.

## Single Path

Cube Alchemy ensures there is exactly one bidirectional path between any two tables in the data model. This creates a clear, unambiguous way to traverse from one table to another.

## Composite Key

When tables share multiple columns, Cube Alchemy automatically creates bridges to connect them:

1. **Detection**: It identifies sets of shared columns between tables

2. **Composite Key Creation**: A single key is generated from these shared columns, autonumbered to improve performance on the upcoming operations.

3. **Composite Tables**: New tables are created to store only the shared columns along with the generated keys

4. **Column Renaming**: The original shared columns in source tables are renamed with a format of `column_name <table_name>`

5. **Key Addition**: The newly created composite keys are added to the original tables

This process consolidates complex relationships into simple, efficient connections while preserving all the original data.

## Cardinality

Cube Alchemy takes a flexible approach:

- It does not enforce specific cardinality constraints like one-to-many or many-to-one.

- Understanding the natural cardinality of the data helps avoid unexpected results in aggregations (e.g., due to row duplication).

**Fact and Dimension Tables**

Data analysts are often familiar with dimensional modeling principles used in data warehousing and business intelligence. These typically involve:

- **Fact tables**: Contain quantitative data that represent events or transactions (sales, orders, shipments).

- **Dimension tables**: Provide descriptive context through attributes that answer the "who, what, where, when, why, and how" questions about the data (customers, products, locations, time periods).

Note that the library is flexible regarding relationships between data rather than enforcing a specific modeling paradigm:

- Cube Alchemy does not explicitly enforce Fact and Dimension table distinctions.

- Every column provided in the DataFrames used to define a Hypercube is available as a dimension and can also be used to create metrics and filters.

- The framework is design-agnostic. The analyst defines which tables serve as facts or dimensions in a given context.



```python
# After initiating the hypercube, inspect how the connected tables relate
cube.get_cardinalities()

# Or inspect the relationships
cube.get_relationship_matrix()  
```


## Visualization

When setting up a hypercube, it can be useful to inspect the relationship graph to confirm how tables connect and where composite keys have been introduced. 
```python
# Default view shows renamed columns (column_name <table_name>)
cube.visualize_graph()

# For cleaner display without table name suffixes
cube.visualize_graph(full_column_names=False)
```
This visualization helps illustrate the automatic transformations applied by Cube Alchemy.

*Note: If the displayed graph doesn't render well, try again or adjust the size.*