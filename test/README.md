# Tests for cube-alchemy

This suite is designed for robustness and clarity when working with data-heavy flows. It follows a layered approach:

- Unit tests (marked `@pytest.mark.unit`): Small, fast checks for pure functions and mixins’ behavior.
- Integration tests (marked `@pytest.mark.integration`): Build a `Hypercube` from small sample datasets, verify relationships, queries, and end-to-end behaviors.
- Slow tests (marked `@pytest.mark.slow`): Larger datasets or optional visual checks.

Conventions
- Tests live under `test/` with modules like `test_core_*.py` and `test_integration_*.py`.
- Shared fixtures live in `test/conftest.py`.
- Use deterministic seeds and minimal rows for speed unless testing performance.
- Prefer table factories/fixtures over ad-hoc CSV reads for reproducibility.

How to run
- All tests: `pytest`
- Just unit tests: `pytest -m unit`
- Just integration: `pytest -m integration`
- Include slow tests: `pytest -m slow`

Notes
- The PnL synthetic dataset in `cube-alchemy-examples/synthetic/pnl/data/` is used for an integration test. It’s small enough to run quickly, and it helps assert the circular-reference detection behavior via the `SchemaValidator` and `Hypercube`.
- If you modify file paths or dataset size, adjust the test fixtures accordingly.

## Comparing Hypercube outputs

Hypercube query results are pandas DataFrames. To compare deterministically:

- Choose stable keys (e.g., dimension columns) and set them as index.
- Sort rows deterministically (by index or explicit columns).
- Compare only the expected columns; ignore unexpected extras when not relevant.
- Use tolerances for floats to avoid brittle failures.

A helper `assert_df_equal_loose` in `test/utils.py` wraps these best practices.

Example:

```python
result = cube.query("revenue_by_category")
expected = pd.DataFrame({"category": ["A", "B"], "Revenue": [570.0, 240.0]})
assert_df_equal_loose(expected, result, index_cols=["category"], float_cols=["Revenue"])
```