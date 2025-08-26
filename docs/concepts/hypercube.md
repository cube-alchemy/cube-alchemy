# Understanding the Hypercube

A **hypercube** is a powerful data structure for organizing and analyzing data from multiple perspectives. Think of a simple cube with three dimensions: length, width, and height. A hypercube extends this concept to an unlimited number of dimensions, allowing you to model complex business scenarios.

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

### How Cube Alchemy Builds the Hypercube

In Cube Alchemy, the hypercube is not limited to a single table. It combines **multiple DataFrames** into a unified, logical model that you can query seamlessly. You don't need to write the complex joins to connect them; the hypercube handles the relationships for you.

**Key Concepts:**

- **Data Model as a Graph:** The underlying structure is a **Directed Acyclic Graph (DAG)**.
    - **Nodes**: Your DataFrames.
    - **Edges**: The shared columns that link them.

- **Effortless Queries:** When you request a metric across certain dimensions, the hypercube automatically **traverses** these connections (even across multiple "hops") to gather the necessary data.

- **Consistency:** Define your metrics and dimensions once, and they can be reliably used across the entire data model.

---

> **Important Note: Avoid Circular Dependencies**
>
> For the hypercube to function correctly, your data model must be a **Directed Acyclic Graph (DAG)**. This means you must avoid **cyclic relationships** (or circular references). Such cycles break the logic of data traversal and can lead to incorrect or infinite aggregations.
