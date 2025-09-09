from typing import Dict

import pandas as pd
import pytest

from cube_alchemy import Hypercube
from cube_alchemy.core.schema_validator import SchemaValidator


@pytest.mark.integration
def test_pnl_dataset_cycle_detection(pnl_tables: Dict[str, pd.DataFrame]):
    """The PnL dataset is known to create circular references initially.
    SchemaValidator.validate should raise ValueError indicating the issue.
    """
    with pytest.raises(ValueError) as excinfo:
        SchemaValidator.validate(pnl_tables, show_graph=False)
    assert "Cyclic relationships" in str(excinfo.value)

