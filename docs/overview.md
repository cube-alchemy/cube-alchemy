# Overview

Cube Alchemy transforms your pandas DataFrames into a powerful **hypercube**, creating a unified semantic layer for multidimensional analysis. This allows you to move from disconnected tables to a coherent analytical model where you can explore data declaratively.

### Core Capabilities

- **Automatic Data Modeling:** Intelligently discovers relationships between your DataFrames by matching shared column names, building a connected graph model automatically.
- **Complex Relationship Handling:** Transparently manages composite keys and multi-hop relationships, so you can query across tables without writing the complex joins to connect them.
- **Reusable Analytics:** Define metrics and queries once and reuse them across your entire analysis, ensuring consistency and reducing boilerplate code.
- **Stateful Analysis:** Maintain a filtering context across queries to easily compare different scenarios.

### The Semantic Layer

Map your raw data into a clear and consistent set of analytical components that form your hypercube:

- **Dimensions**: The "by" of your analysis—the entities you use to slice and dice data (e.g., `Customer`, `Region`, `Product`).
- **Metrics**: The key performance indicators (KPIs) you measure (e.g., `Total Revenue`, `Conversion Rate`, `Average Order Value`).
- **Queries**: The questions you ask of your data, combining metrics and dimensions to produce insights (e.g., *Sales by Region over Time*).

### Why It Matters

Build faster, more reliable analytics with a fraction of the effort.

- **Accelerate Insights:** Go from raw data to deep analysis in minutes. Relationships are discovered automatically, not manually coded.
- **Simplify Complexity:** Replace messy, ad-hoc joins with clean, declarative queries that are easy to read and maintain.
- **Ensure Consistency:** Standardized metrics and a central data model guarantee that everyone gets reliable, consistent results.
- **Integrate Seamlessly:** Designed to work with Streamlit and other Python-based frameworks for building interactive data applications.