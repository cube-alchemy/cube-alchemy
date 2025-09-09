import pandas as pd
import pytest

from cube_alchemy import Hypercube


@pytest.mark.unit
def test_composite_tables_created_with_expected_columns_and_rows():
    # Create two tables that share two columns (A, B) so a composite table is generated
    t1 = pd.DataFrame({
        "A": [1, 2],
        "B": [10, 20],
        "v1": [100, 200],
    })
    t2 = pd.DataFrame({
        "A": [1, 3],
        "B": [10, 30],
        "v2": [300, 400],
    })
    # A third table that shouldn't participate in the composite (only one shared column)
    t3 = pd.DataFrame({
        "A": [99],
        "C": [999],
    })

    tables = {"t1": t1, "t2": t2, "t3": t3}

    # Build the Hypercube with composite processing enabled
    cube = Hypercube(tables)

    # There should be exactly one composite table: for participants t1+t2 by columns A and B
    assert cube.composite_tables, "Expected at least one composite table to be created"
    expected_name = "_composite_t1_t2__by__A_B"
    assert expected_name in cube.composite_tables, (
        f"Composite table name mismatch. Found: {list(cube.composite_tables.keys())}"
    )

    comp = cube.composite_tables[expected_name]

    # Composite table should contain the shared key columns plus the auto-numbered composite key column
    expected_columns = {"A", "B", "_composite_key_A_B"}
    assert set(comp.columns) >= expected_columns, (
        f"Composite table columns missing. Expected at least {expected_columns}, got {set(comp.columns)}"
    )

    # Its rows should be the union of unique (A,B) pairs from t1 and t2
    expected_pairs = {(1, 10), (2, 20), (3, 30)}
    actual_pairs = set(map(tuple, comp[["A", "B"]].to_numpy()))
    assert actual_pairs == expected_pairs

    # The composite key should be integer-typed after auto-numbering
    assert pd.api.types.is_integer_dtype(comp["_composite_key_A_B"])  

@pytest.mark.unit
def test_multiple_composite_tables_various_shared_combinations():
    # Construct a richer schema with several two-column shared combos, no circular refs needed
    orders = pd.DataFrame({
        "customer_id": ["C1", "C2"],
        "store_id": ["S1", "S2"],
        "order_date": ["2025-01-01", "2025-02-01"],
        "amount": [100.0, 200.0],
    })
    visits = pd.DataFrame({
        "customer_id": ["C1", "C2"],
        "store_id": ["S1", "S2"],
        "visit_date": ["2024-12-01", "2025-02-15"],
    })
    returns = pd.DataFrame({
        "customer_id": ["C1", "C3"],
        "store_id": ["S1", "S3"],
        "reason": ["damaged", "late"],
    })
    shipments = pd.DataFrame({
        "store_id": ["S1", "S3"],
        "order_date": ["2025-01-01", "2025-03-01"],
        "product_id": ["P10", "P11"],
    })
    inventory = pd.DataFrame({
        "store_id": ["S1", "S2"],
        "product_id": ["P10", "P12"],
        "on_hand": [5, 7],
    })
    stores = pd.DataFrame({
        "store_id": ["S1", "S2", "S3"],
        "store_name": ["Alpha", "Beta", "Gamma"],
    })

    tables = {
        "orders": orders,
        "visits": visits,
        "returns": returns,
        "shipments": shipments,
        "inventory": inventory,
        "stores": stores,  # single shared col only; should not form composite
    }

    cube = Hypercube(
        tables,
        validate=False,
        apply_composite=True,
        rename_original_shared_columns=True,
        logger=False,
    )

    # Expected composite tables derived from combos:
    # - (customer_id, store_id) across orders, visits, returns
    # - (order_date, store_id) across orders, shipments
    # - (product_id, store_id) across inventory, shipments
    expected_tables = {
        "_composite_orders_returns_visits__by__customer_id_store_id": {
            "cols": {"customer_id", "store_id", "_composite_key_customer_id_store_id"},
            "pairs": {
                ("C1", "S1"),  # from orders/visits/returns
                ("C2", "S2"),  # from orders/visits
                ("C3", "S3"),  # from returns
            },
            "pair_cols": ["customer_id", "store_id"],
        },
        "_composite_orders_shipments__by__order_date_store_id": {
            "cols": {"order_date", "store_id", "_composite_key_order_date_store_id"},
            "pairs": {
                ("2025-01-01", "S1"),
                ("2025-02-01", "S2"),
                ("2025-03-01", "S3"),
            },
            "pair_cols": ["order_date", "store_id"],
        },
        "_composite_inventory_shipments__by__product_id_store_id": {
            "cols": {"product_id", "store_id", "_composite_key_product_id_store_id"},
            "pairs": {
                ("P10", "S1"),
                ("P11", "S3"),
                ("P12", "S2"),
            },
            "pair_cols": ["product_id", "store_id"],
        },
    }

    # Validate presence, schema, and content for each expected composite table
    assert cube.composite_tables, "No composite tables were created"
    for name, meta in expected_tables.items():
        assert name in cube.composite_tables, (
            f"Missing expected composite table '{name}'. Found: {list(cube.composite_tables.keys())}"
        )
        comp = cube.composite_tables[name]
        # Columns should include keys and its composite key; an index column will be present too
        assert set(comp.columns) >= meta["cols"], (
            f"Columns for {name} missing required set {meta['cols']}. Got: {set(comp.columns)}"
        )
        # Union-of-pairs should match expected
        actual_pairs = set(map(tuple, comp[meta["pair_cols"]].to_numpy()))
        assert actual_pairs == meta["pairs"], (
            f"Row pairs mismatch for {name}. Expected {meta['pairs']}, got {actual_pairs}"
        )
        # Composite key must be integer-typed
        comp_key_col = next(c for c in comp.columns if c.startswith("_composite_key_") and all(p in c for p in meta["pair_cols"]))
        assert pd.api.types.is_integer_dtype(comp[comp_key_col])

