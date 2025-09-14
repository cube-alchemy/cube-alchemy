import pandas as pd
import copy

from cube_alchemy.core.hypercube import Hypercube


def test_single_table_initialization_keyspace():
    # Single table with no shared columns
    sales = pd.DataFrame({
        'order_id': [1, 2, 3],
        'amount': [100.0, 200.0, 300.0],
    })

    cube = Hypercube({'Sales': sales})

    # The model should add an index column and create an 'Unfiltered' context
    idx_col = '_index_Sales'
    assert idx_col in cube.tables['Sales'].columns

    unfiltered = cube.context_states['Unfiltered']
    # For single-table, key-space should be just the table index (no link keys exist)
    assert idx_col in unfiltered.columns
    assert unfiltered[idx_col].is_unique
    assert len(unfiltered) == len(sales)


def test_multi_table_initialization_keyspace():
    # Two tables with a shared column that becomes a link key
    orders = pd.DataFrame({
        'order_id': [1, 2, 3, 4],
        'customer_id': [10, 10, 20, 30],
        'amount': [100.0, 200.0, 150.0, 50.0],
    })
    customers = pd.DataFrame({
        'customer_id': [10, 20, 40],
        'segment': ['A', 'B', 'C'],
    })

    cube = Hypercube(copy.deepcopy({'Orders': orders, 'Customers': customers}))

    # After link-table creation, both base tables share _key_customer_id
    idx_orders = '_index_Orders'
    idx_customers = '_index_Customers'

    # The Unfiltered key-space should include per-table indexes and the link key
    unfiltered = cube.context_states['Unfiltered']
    for col in (idx_orders, idx_customers):
        assert col in unfiltered.columns

    # No duplicate column labels
    assert unfiltered.columns.duplicated().sum() == 0

    # Rows should cover the outer-joined key-space across the relationship
    # At minimum, there must be at least as many unique Orders indices as in the Orders table
    assert unfiltered[idx_orders].nunique() <= len(orders)
    assert unfiltered[idx_customers].nunique() <= len(customers)


def test_single_table_basic_metric_and_query(minimal_tables):
    minimal_tables = copy.deepcopy(minimal_tables)
    # Use Sales only from the minimal dataset
    sales = minimal_tables['Sales'][['sale_id', 'qty', 'price']].copy()
    cube = Hypercube({'Sales': sales})

    cube.define_metric(name='Revenue', expression='[price] * [qty]', aggregation='sum')
    cube.define_query(name='Total Revenue', metrics=['Revenue'], dimensions=[])

    df = cube.query('Total Revenue')
    assert 'Revenue' in df.columns
    expected = float((sales['price'] * sales['qty']).sum())
    # Query without dimensions should aggregate to a single total
    assert float(df['Revenue'].sum()) == expected



def test_multi_table_basic_metric_by_dimension(minimal_tables):
    minimal_tables = copy.deepcopy(minimal_tables)

    # Expected via manual merge and groupby
    sales = copy.deepcopy(minimal_tables['Sales'])
    cust = copy.deepcopy(minimal_tables['Customer'])
    merged = sales.merge(cust[['customer_id', 'segment']], on='customer_id', how='left')
    expected = (
        merged.assign(Revenue=merged['price'] * merged['qty'])
              .groupby('segment', dropna=False)['Revenue']
              .sum()
              .reset_index()
    )


    # Build cube with all minimal tables
    cube = Hypercube(minimal_tables)

    cube.define_metric(name='Revenue', expression='[price] * [qty]', aggregation='sum')
    cube.define_query(name='Revenue by Segment', metrics=['Revenue'], dimensions=['segment'])

    result = cube.query('Revenue by Segment')
    
    assert set(['segment', 'Revenue']).issubset(result.columns)

    

    # Compare sums per segment
    exp_map = dict(zip(expected['segment'].astype(object), expected['Revenue'].astype(float)))
    res_map = dict(zip(result['segment'].astype(object), result['Revenue'].astype(float)))
    # Every expected segment should be present with the same total
    for seg, val in exp_map.items():
        assert seg in res_map
        assert abs(res_map[seg] - val) < 1e-9
    