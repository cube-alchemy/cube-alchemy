# Model Catalog

The Model Catalog makes working with your hypercube more efficient by persisting analytics and plotting definitions to external storage. This lets you separate configuration from code and work across sessions.

By default, Cube Alchemy uses YAML files to store your model definitions. You can:

- Define metrics, queries, and visualizations directly in YAML

- Load external definitions into a fresh hypercube session

- Save definitions you've created in code back to YAML

This approach separates your analytical definitions from your processing code, creating a cleaner, more maintainable workflow.

## What you can persist

**Analytics Components**

- Metrics and derived metrics

- Transformations

- Queries

**Visualization**

- Plot configurations

## How it works

- **Catalog**: A façade that coordinates Sources and Repository operations

- **Sources**: Backend connectors that read/write definitions (YAML is the default implementation)

- **Repository**: An in-memory store that holds normalized definitions during runtime.

This architecture potentially allows you combine multiple sources while maintaining a consistent interface for your hypercube.

## Basic usage

```python
# 1. Attach a YAML file to your hypercube
cube.set_yaml_model_catalog() # will set "model_catalog.yaml" on the working directory

# 2. Load existing definitions from YAML into your cube
cube.load_from_model_catalog()

# 3. Create or modify definitions using the hypercube API. This is useful when creating on-the-fly definitions...
cube.define_metric("revenue", expression="[sales] * [price]", aggregation="sum")
cube.define_query("sales_by_region", dimensions=["region"], metrics=["revenue"])

# ...and you want to persist them.
# 4. Save your definitions back to YAML
cube.save_to_model_catalog()

# 5. Inspect available definitions by accessing the model_catalog object directly.
metrics = cube.model_catalog.list("metrics")
queries = cube.model_catalog.list("queries")
# cube.model_catalog.get("metrics", "Amount Actual")
```
**Note:**

In API methods, “model catalog” refers to the Catalog Source/s for simplicity.

>The Repository is an internal layer working under the hood that normalizes data so Python can read and write from and to the source/s easily. When you access the model_catalog object directly and list or get from it, bear in mind you are doing it from the Repository, so depending on your where you are in your workflow it might need to be refreshed, either from the Source or the actual Hypercube object:

> - cube.model_catalog.refresh(kinds, reload_sources, clear_repo) # Same as load_from_model_catalog, but without applying the catalog to the cube

> - cube._model_catalog_pull_from_cube() # Same as save_to_model_catalog, but wihtout saving to the actual source.


## YAML structure

Simply mirrors the respective definition APIs. Plots and Transformers can be nested under their parent query (as shown below) or defined at the top level with a query reference.

```yaml
metrics:
  revenue:
    expression: "[Unit Price] * [Quantity]"
    aggregation: sum

derived_metrics:
  margin_pct:
    expression: "margin / revenue"

queries:
  Sales by Month Year :
    dimensions: [month_year]
    metrics: [revenue]
    transformers:
      moving_average:
        'on': revenue
        window: 3
        sort_by: revenue
        new_column: revenue_ma_3
    plots:
        default_bar:
          plot_type: line
          metrics: [revenue_ma_3]
```

