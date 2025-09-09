import os
from pathlib import Path
from typing import Dict

import pandas as pd
import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def minimal_tables() -> Dict[str, pd.DataFrame]:
    """Return the exact README example dataset for reuse in tests."""
    products = pd.DataFrame({
        'product_id': [1, 2, 3],
        'category': ['Electronics', 'Home', 'Other'],
        'cost': [300.0, 15.0, 500.0],
    })

    customers = pd.DataFrame({
        'customer_id': [100, 101, 102, 103],
        'customer_name': ['Acme Co', 'Globex', 'Initech', 'Umbrella'],
        'segment': ['SMB', 'Enterprise', 'SMB', 'Consumer'],
        'region_id': [7, 8, 7, 9],
    })

    regions = pd.DataFrame({
        'region_id': [7, 8, 9],
        'region': ['North', 'West', 'South'],
    })

    calendar = pd.DataFrame({
        'date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
        'month': ['2024-01', '2024-01', '2024-01', '2024-01', '2024-01'],
    })

    sales = pd.DataFrame({
        'sale_id': [10, 11, 12, 13, 14, 15],
        'product_id': [1, 1, 2, 3, 2, 1],
        'customer_id': [100, 101, 102, 103, 100, 102],
        'date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-03'],
        'promo_code': ['NEW10', 'NONE', 'DISC5', 'NONE', 'DISC5', 'NEW10'],
        'qty': [2, 1, 4, 3, 5, 2],
        'price': [500.0, 500.0, 25.0, 800.0, 25.0, 500.0],
    })

    promos = pd.DataFrame({
        'promo_code': ['NEW10', 'DISC5', 'NONE'],
        'promo_type': ['Launch', 'Discount', 'No Promo'],
    })

    return {
        'Product': products,
        'Customer': customers,
        'Region': regions,
        'Calendar': calendar,
        'Sales': sales,
        'Promos': promos,
    }


@pytest.fixture(scope="session")
def pnl_data_dir(project_root: Path) -> Path:
    return project_root / "cube-alchemy-examples" / "synthetic" / "pnl" / "data"


@pytest.fixture(scope="session")
def pnl_tables(pnl_data_dir: Path) -> Dict[str, pd.DataFrame]:
    # Load CSVs used by the PnL example; keys must match what notebooks expect
    files = {
        "accounts": "accounts.csv",
        "actuals": "actuals.csv",
        "budget": "budget.csv",
        "business_unit_dim": "business_unit_dim.csv",
        "calendar_dim": "calendar_dim.csv",
        "cost_center_dim": "cost_center_dim.csv",
        "location_dim": "location_dim.csv",
        "pnl_report_mapping": "pnl_report_mapping.csv",
        "project_dim": "project_dim.csv",
        "vendor_dim": "vendor_dim.csv",
    }
    tbls: Dict[str, pd.DataFrame] = {}
    for key, fname in files.items():
        csv_path = pnl_data_dir / fname
        if not csv_path.exists():
            pytest.skip(f"PnL dataset not available: {csv_path}")
        tbls[key] = pd.read_csv(csv_path)
    return tbls
