# Relationships in Cube Alchemy

Cube Alchemy uses implicit relationships, meaning DataFrames automatically connect to each other through shared column names. This creates a unified data model without requiring you to write explicit joins.

These relationships enable you to:

- Traverse the entire data model seamlessly

- Query across multiple tables without complex join logic

- Select dimensions from any table in your schema

- Create metrics using columns from any connected table

Cube Alchemy handles all the necessary data operations under the hood, so you can use more of your time to focus on analysis.

## Single Path

Cube Alchemy ensures there is exactly one bidirectional path between any two tables in your data model. This creates a clear, unambiguous way to traverse from one table to another.

## Composite Key

When tables share multiple columns, Cube Alchemy automatically creates composite keys to properly connect them:

1. **Detection**: The system identifies sets of shared columns between tables
2. **Composite Key Creation**: A single, efficient key is generated from these shared columns
3. **Composite Tables**: New tables are created to store only the shared columns along with the generated keys
4. **Column Renaming**: The original shared columns in source tables are renamed with a format of `column_name <table_name>`
5. **Key Addition**: The newly created composite keys are added to the original tables

This process consolidates complex relationships into simple, efficient connections while preserving all the original data.

## Cardinality

Cube Alchemy takes a flexible approach:

- It does not enforce specific cardinality constraints like one-to-many or many-to-one; many-to-many is the default relationship.

- You should understand your data's natural cardinality to avoid unexpected results in your aggregations (e.g., due to row duplication).

## Visualization

When setting up your hypercube, inspect the relationship graph to confirm how tables connect and where composite keys have been introduced. 
```python
cube.visualize_graph()
```
This visualization helps you understand the automatic transformations that Cube Alchemy has applied to optimize your data model for analysis.