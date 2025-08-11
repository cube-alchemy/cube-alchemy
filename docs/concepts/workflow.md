```mermaid
flowchart LR
  A["Load DataFrames"] --> B["Build Hypercube"]
  B --> C["Define Metrics"]
  C --> D["Define Queries"]
  D --> E["Execute Queries"]
  E --> F["Update Context State (Apply or Remove Filters)"]
  F --> E
```

Cube Alchemy's workflow is intuitive and powerful: load your data, build a unified hypercube structure, define your metrics, and create reusable queries. The stateful architecture allows you to execute queries and apply filters in an iterative process, maintaining context throughout your analysis journey.