```mermaid
flowchart LR
  A["Load Data"] --> B["Build Hypercube"]
  subgraph MS["Model Specification"]
    C["Define Metrics"] --> D["Define Queries"]
  end
  B --> C
  D --> P["Define Plots"]
  P --> E["Execute Queries"]
  E --> F["Display"]
  F --> G["Filter"]
  G --> E
```

Cube Alchemy's workflow: load your data, build a unified hypercube, specify your model (metrics and queries), define plots, then execute. The stateful architecture lets you iterate by applying filters and re-running queries and plots.