import pandas as pd
import pytest

from cube_alchemy.core.metric import Metric, DerivedMetric
from cube_alchemy import Hypercube
from .utils import assert_df_equal_loose

import copy
@pytest.mark.unit
def test_metric_and_derived_metric_basic():
    # Basic construction sanity checks
    m = Metric(
        name="Revenue",
        expression="[price] * [qty]",
        aggregation="sum",
        metric_filters=None,
        row_condition_expression=None,
        context_state_name="Default",
        ignore_dimensions=False,
        ignore_context_filters=False,
        fillna=None,
        nested=None,
    )
    assert m.name == "Revenue"
    assert m.aggregation == "sum"

    dm = DerivedMetric(name="Margin", expression="[Revenue] - [Cost]", fillna=0)
    details = dm.get_derived_metric_details()
    assert m.columns == ["price", "qty"] or m.columns == ["qty", "price"]
    assert "expression" in details


@pytest.mark.unit
@pytest.mark.parametrize("normalized_core", [True, False])
def test_readme_example_end_to_end_query_and_filter(minimal_tables, normalized_core):
    """Build the Hypercube using the exact README example data, then:
    - Define metrics and a query.
    - Assert the unfiltered result matches the README output.
    - Apply a customer filter and assert the filtered result matches the README output.
    """
    # Use the README dataset provided by the shared fixture
    minimal_tables = copy.deepcopy(minimal_tables)
    cube = Hypercube(minimal_tables, validate=False, logger=False, normalized_core=normalized_core)

    # Define metrics exactly as in the README
    cube.define_metric(name='Revenue', expression='[qty] * [price]', aggregation='sum')
    cube.define_metric(name='Units', expression='[qty]', aggregation='sum')
    cube.define_metric(name='Margin', expression='([price] - [cost]) * [qty]', aggregation='sum')
    cube.define_metric(name='Number of Sales', expression='[sale_id]', aggregation='count')

    cube.define_query(
        name='sales analysis',
        dimensions=['region', 'category', 'promo_type'],
        metrics=['Revenue', 'Units', 'Margin', 'Number of Sales']
    )

    # Expected unfiltered result (README)
    expected_unfiltered = pd.DataFrame({
        'region': ['North', 'North', 'South', 'West'],
        'category': ['Electronics', 'Home', 'Other', 'Electronics'],
        'promo_type': ['Launch', 'Discount', 'No Promo', 'No Promo'],
        'Revenue': [2000.0, 225.0, 2400.0, 500.0],
        'Units': [4, 9, 3, 1],
        'Margin': [800.0, 90.0, 900.0, 200.0],
        'Number of Sales': [2, 2, 1, 1],
    })
    result_unfiltered = cube.query('sales analysis')
    assert_df_equal_loose(
        expected_unfiltered,
        result_unfiltered,
        index_cols=['region', 'category', 'promo_type'],
        float_cols=['Revenue', 'Margin'],
    )

    # Apply filter and assert filtered result (README)
    cube.filter({'customer_name': ['Initech']})
    result_filtered = cube.query('sales analysis')
    expected_filtered = pd.DataFrame({
        'region': ['North', 'North'],
        'category': ['Electronics', 'Home'],
        'promo_type': ['Launch', 'Discount'],
        'Revenue': [1000.0, 100.0],
        'Units': [2, 4],
        'Margin': [400.0, 40.0],
        'Number of Sales': [1, 1],
    })
    assert_df_equal_loose(
        expected_filtered,
        result_filtered,
        index_cols=['region', 'category', 'promo_type'],
        float_cols=['Revenue', 'Margin'],
    )