# Transformation

Transformations are designed to add analytical features to a query DataFrame. Think of it as post-query augmentation: you define metrics and queries as usual, then apply transformers to compute things like moving averages, z-scores, Pareto flags, ranks, forecasts, or k-means clusters on the returned table.

We apply a **transformation** to the DataFrame, which (ideally) enriches it by adding one or more new analytical features. After the transformation, the original DataFrame might be different from what it was before the transformation (e.g., it has a new column or a column was updated).

## When to use it

- You want quick analytical features derived from the queried data. Applying them through *Derived Metrics* is infeasible or difficult to implement.

- You want pluggable, composable transformations that can be reused across queries.

## Interface design

Designed for extensibility as a small registry-based interface:

- Registry: register transformers by name using `register_transformer(name, transformer)`.

- Definition: attach a transformer to a query via `define_transformation(query_name, transformer, params)`.

- Execution: apply at runtime with `transform(df, transformer, **params)` or use stored configs to transform a query result.

- Configuration: store/retrieve per-query transformation configs with `list_transformations`, `get_transformation_config`, and `delete_transformation`.

A transformer can be either:

- An object implementing `Transformer` class (ABC) with a method `transform(df: pd.DataFrame, **params) -> pd.DataFrame`.

- A plain callable `fn(df: pd.DataFrame, **params) -> pd.DataFrame`.

## Default transformers

Cube Alchemy ships with a few defaults that are auto-registered:

- moving_average

- cumulative

- rank

- zscore

- pareto

- linear_regression

- kmeans

You can inspect these under `cube_alchemy/transformation/default_transformers`. You can use them directly, or register your own custom functions.

## Examples

Register a custom transformer and attach it to a query:

```python
def add_simple_rank(df, by: str, ascending: bool = False, col: str = 'Simple Rank'):
    df = df
    df[col] = df[by].rank(ascending=ascending, method='dense').astype(int)
    return df

cube.register_transformer('rank', add_simple_rank)
cube.define_transformation('Sales by Country and Category', transformer='rank', params={'by': 'Revenue'})

# Later during execution, the newly generated column will be available
cube.query('Sales by Country and Category')

# This is a very simple case which can also be achieved using expressions
cube.define_derived_metric(
    name="Revenue Rank",
    expression='@pd.Series([Revenue]).rank(ascending=True, method="dense")'
)

# But they operate in a different way and also on different steps on the query execution pipeline.

# Derived Metrics create a new column on the DataFrame based on Dimensions and Metrics. Transformers transform the DataFrame using an arbitrary transformation function (it can delete rows, rename columns, add columns, change order, fetch external data through an api and merge it, etcetc.).
```

Notes:

- Each query can configure at most one instance of the same transformer.

- When designing custom transformers, bear in mind that they may modify the query result, use with discretion.