from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from cube_alchemy.core.hypercube import Hypercube
import sys
import types


# Top-level importable function for registry persistence tests
def double(x):
    return x * 2


def test_function_registry_persists_importable_function(tmp_path: Path, minimal_tables):
    sales = minimal_tables['Sales'][['qty']].copy()
    cube = Hypercube({'Sales': sales}, validate=False, logger=False)

    cube.add_functions(double=double)
    cube.define_metric(name='DoubleQty', expression='@double([qty])', aggregation='sum')
    cube.define_query(name='double_sum', metrics=['DoubleQty'], dimensions=[])

    # Sanity check before persisting
    before = cube.query('double_sum')
    assert isinstance(before, pd.DataFrame)
    assert 'DoubleQty' in before.columns

    # Save and load
    pkl = cube.save_as_pickle(tmp_path / 'cube.pkl')
    cube2 = Hypercube.load_pickle(pkl)

    # Function should be restored (importable by module:qualname)
    assert 'double' in cube2.function_registry

    after = cube2.query('double_sum')
    assert isinstance(after, pd.DataFrame)
    assert 'DoubleQty' in after.columns

    # Value should match expected 2 * sum(qty)
    expected = float((sales['qty'] * 2).sum())
    assert float(after['DoubleQty'].sum()) == expected


def test_function_registry_skips_lambdas_on_unpickle(tmp_path: Path, minimal_tables):
    sales = minimal_tables['Sales'][['qty']].copy()
    cube = Hypercube({'Sales': sales}, validate=False, logger=False)

    cube.add_functions(tmp=lambda x: x * 3)  # non-importable; will not persist
    cube.define_metric(name='TripleQty', expression='@tmp([qty])', aggregation='sum')
    cube.define_query(name='triple_sum', metrics=['TripleQty'], dimensions=[])

    # Works before saving
    before = cube.query('triple_sum')
    assert isinstance(before, pd.DataFrame)

    pkl = cube.save_as_pickle(tmp_path / 'cube_lambda.pkl')
    cube2 = Hypercube.load_pickle(pkl)

    # Lambda is dropped on restore
    assert 'tmp' not in cube2.function_registry

    # Query should raise because the referenced function is missing after load
    with pytest.raises(Exception):
        cube2.query('triple_sum')


def test_importable_function_missing_on_load_raises(tmp_path: Path, minimal_tables, monkeypatch):
    # Dynamically create a temporary module 'tmp_udfs' with a top-level function
    mod_name = 'tmp_udfs'
    mod = types.ModuleType(mod_name)
    exec('def double(x):\n    return x * 2\n', mod.__dict__)
    sys.modules[mod_name] = mod

    # Build cube and register function from the temp module
    sales = minimal_tables['Sales'][['qty']].copy()
    cube = Hypercube({'Sales': sales}, validate=False, logger=False)
    cube.add_functions(double=getattr(sys.modules[mod_name], 'double'))
    cube.define_metric(name='DoubleQty', expression='@double([qty])', aggregation='sum')
    cube.define_query(name='double_sum', metrics=['DoubleQty'], dimensions=[])

    # Sanity: it runs before save
    assert 'DoubleQty' in cube.query('double_sum').columns

    # Save cube, then simulate environment without the module on load
    pkl = cube.save_as_pickle(tmp_path / 'cube_missing_module.pkl')
    del sys.modules[mod_name]

    cube2 = Hypercube.load_pickle(pkl)
    # The function spec points to tmp_udfs.double which is not importable now
    assert 'double' not in cube2.function_registry

    # Executing a query that references the missing function should raise
    with pytest.raises(Exception):
        cube2.query('double_sum')
