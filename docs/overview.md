# Overview

Cube Alchemy transforms your pandas DataFrames into a powerful **hypercube**, creating a unified semantic layer for multidimensional analysis. This allows you to move from disconnected tables to a coherent analytical model where you can explore data simply and declaratively.

### Core Capabilities

- **Automatic Relationships:**  Discovers relationships between your DataFrames by matching shared column names.
    - *Complex Relationship Handling:* Handles composite keys and complex relationships transparently.
- **Multidimensional Analytics:** Slice, dice, and aggregate your data across any dimension with consistent, reusable metrics and queries that reduce boilerplate code.
- **Stateful Analysis:** Maintain a filtering context across queries to easily compare different scenarios.
- **Interactive & Scalable:** Works seamlessly in notebook and data apps (Streamlit/Panel).

### The Semantic Layer

Map your data into a clear and consistent set of analytical assets to work with your hypercube:

- **Dimensions**: The "by" of your analysis—the entities you use to slice and dice data (e.g., `Customer`, `Region`, `Product`).
- **Metrics**: The key performance indicators (KPIs) you measure (e.g., `Total Revenue`, `Conversion Rate`, `Average Order Value`).
- **Queries**: The questions you ask of your data, combining metrics and dimensions to produce insights (e.g., *Revenue by Region over Time*).

### Why It Matters

Build faster, reliable analytics with a fraction of the effort.

- **Accelerate Insights:** Get into deep analysis in minutes. Relationships are discovered automatically, not manually coded.
- **Simplify Complexity:** Replace ad-hoc joins and messy code with clean, declarative queries that are easy to read and maintain.
- **Ensure Consistency:** Standardized metrics and a central data model guarantee that everyone gets reliable, consistent results.
- **Integrate Seamlessly:** Designed to work with Streamlit and other Python-based frameworks for building interactive data applications.