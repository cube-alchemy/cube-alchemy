# Relationships in Cube Alchemy

Cube Alchemy uses implicit relationships, meaning DataFrames automatically connect to each other through shared column names.

These relationships enable you to work with your newly connected data declaratively. Cube Alchemy handles all the necessary data operations under the hood.

## Single Path

Cube Alchemy ensures there is exactly one bidirectional path between any two tables in your data model. This creates a clear, unambiguous way to traverse from one table to another.

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

- It does not enforce specific cardinality constraints like one-to-many or many-to-one; many-to-many is the default relationship.

- You should understand your data's natural cardinality to avoid unexpected results in your aggregations (e.g., due to row duplication).

**Fact and Dimension Tables**

As a data analyst you might be already familiar with dimensional modeling principles used in data warehousing and business intelligence. These typically involve:

- **Fact tables**: Contain quantitative data that represent events or transactions (sales, orders, shipments).

- **Dimension tables**: Provide descriptive context through attributes that answer the "who, what, where, when, why, and how" questions about your data (customers, products, locations, time periods).

Please bear in mind that Cube Alchemy's approach is flexible regarding relationships between your data rather than enforcing a specific modeling paradigm:

- Cube Alchemy does not explicitly enforce Fact and Dimension table distinctions.
- Every single column provided in the DataFrames you use to define a Hypercube will be available as a dimension, and can also be used to create metrics and filters.
- The framework is design-agnostic. It's up to you as the analyst to define which tables serve as Facts or Dimensions in your specific context.

## Visualization

When setting up your hypercube, it's a good idea to inspect the relationship graph to confirm how tables connect and where composite keys have been introduced. 
```python
# Default view shows renamed columns (column_name <table_name>)
cube.visualize_graph()

# For cleaner display without table name suffixes
cube.visualize_graph(full_column_names=False, w=16, h=12)
```
This visualization helps you understand the automatic transformations that Cube Alchemy has applied.

*Note: If the displayed graph doesn't look so good try a couple of times or adjust the size.*