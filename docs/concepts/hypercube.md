# Understanding the Hypercube

The **hypercube** is a powerful abstraction for analyzing data from multiple perspectives. Think of a simple cube with three dimensions: length, width, and height. A hypercube extends this concept to an arbitrary number of dimensions, allowing you to model complex business scenarios.

Each axis of the hypercube represents a key **dimension** of your data, such as:

- **Time** (e.g., year, month, day)
- **Geography** (e.g., region, country, city)
- **Product** (e.g., category, brand, item)
- **Customer** (e.g., segment, demographics)

The hypercube enables you to calculate *metrics* (like sales, revenue, or user counts) across any combination of these dimensions, ensuring your calculations are always consistent and reusable. For example, you can analyze:

- *Revenue* by **Month**

- *Active users* by **Month** and **Product Category**

- *Margin* by **Month**, **Product Category**, and **Region**

---

## Data Model as a Graph

This is how Cube Alchemy Builds an Hypercube. The underlying structure is a **Connected Undirected Acyclic Graph** where:

- **Nodes**: Your DataFrames.
- **Edges**: The shared columns that link them.

> *It might not look like a tree, but under the hood, the hypercube is basically a tree in disguise — no loops, just clean branches connecting your data. See: [Tree (graph theory)](https://en.wikipedia.org/wiki/Tree_(graph_theory)).*

- **Effortless Queries:** The hypercube handles the relationships for you. When you request a metric across certain dimensions, the hypercube automatically **traverses** these connections to gather the necessary data.

- **Consistency:** Define your metrics and queries once; they will be stateful and can be used reliably across the entire analysis journey.

---

> **Important Note: Avoid Circular Dependencies**
>
> For the hypercube to function correctly, your data model must be a **Acyclic Graph**. This means you must avoid **cyclic relationships** (or circular references). Such cycles create ambiguous join paths that break the logic of data traversal and aggregations.

> With proper modeling (e.g., bridge tables, role-playing/conformed dimensions, etc) cycles can be addressed. Trees keep results consistent and avoid the ad‑hoc rules general graphs require.