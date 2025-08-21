# The Hypercube Explained

A **hypercube** is a flexible way of organizing data for analysis. Instead of just three axes (like length, width, and height in a cube), a hypercube can have as **many axes** as you can imagine.

Each axis represents a **dimension** of your data—such as **time**, **region**, **product category**, or **customer type**.  

The hypercube lets you calculate **measures** (like sales, revenue, or counts) across these dimensions:

- Sales by **month**
- Sales by **month + product category** 
- Sales by **month + product category + region + wheather condition**

This works the same way no matter how many dimensions you add—the hypercube keeps the calculations **consistent and reusable**.  

---

**How it works in Cube Alchemy**

In Cube Alchemy, the hypercube doesn’t just come from one table. Instead, it brings together **multiple DataFrames** into a single, logical structure you can query consistently.  

You don’t have to manually join tables—the hypercube dynamically connects them.  

**At a glance**

- The data model is a **Directed Acyclic Graph (DAG)**:  

    - **Nodes** = your DataFrames  

    - **Edges** = the shared columns that connect them  

- **Queries**: your chosen dimensions and measures can **traverse these connections (multi-hop)** to combine all the data your analysis needs  

- **Consistency**: you define metrics and queries once, and they work everywhere in the model  

---

**Important Note**

To be able to multi-hop through the related tables, we need to **avoid cyclic relationships** (also called circular references), as this breaks the logic of data traversal and aggregation. So you need to make sure your model is a *directed acyclic graph (DAG)*.
