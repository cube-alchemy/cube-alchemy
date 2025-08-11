Dimensions are the categorical columns from your DataFrames that you use to slice and group your data. Think of them as the "by what" in your analysis—region, product category, time period, customer segment, and so on.

In Cube Alchemy, any column from any table in your hypercube can serve as a dimension.

**How dimensions work:**

- **Available everywhere**: Once your DataFrames are connected in the hypercube, dimensions from any table can be used in any query
- **Auto-joining**: When you query dimensions from different tables, the hypercube automatically traverses the relationships to bring them together
- **Multi-hop**: You can combine dimensions that are several "hops" apart in your data model—like querying by both customer region and product category even if they're in completely separate tables

**Getting dimension values:**

You can fetch unique values for any dimension using `cube.query(['dimension_name'])`. This is useful for building filters, dropdowns in apps, or just exploring what values are available:

```python
# Get combinations of region and category
cube.dimensions(['region', 'category'])

# Or you can use the query method, but you first need to define the query without metrics
cube.define_query(
    query_name="dimension_combinations",
    dimensions=set(['region', 'category'])
)
cube.query('dimension_combinations')
```