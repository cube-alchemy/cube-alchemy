import yaml
from pathlib import Path
from typing import Dict, Any

import pytest

from cube_alchemy.catalogs.sources.yaml_model import ModelYAMLSource


def write_yaml(p: Path, data: Dict[str, Dict[str, Any]]) -> None:
    p.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False, indent=2), encoding='utf-8')


def read_yaml(p: Path) -> Dict[str, Dict[str, Any]]:
    return yaml.safe_load(p.read_text(encoding='utf-8')) or {}


@pytest.mark.unit
def test_transformers_canonical_shape_on_load_and_save(tmp_path: Path) -> None:
    ypath = tmp_path / "model.yaml"
    # Mix of shapes; loader should normalize to {name: params} with query meta at top-level view
    write_yaml(ypath, {
        "queries": {
            "q1": {
                "transformers": {
                    "t_nested": {"params": {"alpha": 1}},
                }
            },
        },
        "transformers": {
            "t_top": {"params": {"beta": 2}},
        }
    })

    src = ModelYAMLSource(ypath)
    data = src._load()

    # Lifted and canonicalized: params under 'params', plus query marker in the normalized in-memory view
    # Note: transformers are still using the original keys (not composite keys like plots)
    assert data["transformers"]["t_nested"]["params"]["alpha"] == 1
    assert data["transformers"]["t_nested"]["query"] == "q1"
    assert data["transformers"]["t_top"]["params"]["beta"] == 2

    # When saving with prefer nesting, they should end under queries in canonical {name: params}
    src = ModelYAMLSource(ypath, prefer_nested_plots=True, prefer_nested_transformers=True)
    src.save(data)
    out = read_yaml(ypath)

    # q1.transformers should be params-only mapping
    assert out["queries"]["q1"]["transformers"]["t_nested"] == {"alpha": 1}
    # top-level transformer remains params-only
    assert out["transformers"]["t_top"] == {"beta": 2}


@pytest.mark.unit
def test_shared_renest_logic_plots_and_transformers(tmp_path: Path) -> None:
    ypath = tmp_path / "model.yaml"
    write_yaml(ypath, {
        "queries": {"q1": {"dimensions": ["a"]}},
        "plots": {"p1": {"type": "bar", "query": "q1"}},
        "transformers": {"t1": {"alpha": 1, "query": "q1"}},
    })

    src = ModelYAMLSource(ypath, prefer_nested_plots=True, prefer_nested_transformers=True)
    data = src._load()
    src.save(data)
    out = read_yaml(ypath)

    # Both sections nested, and top-level sections removed when empty
    q1 = out["queries"]["q1"]
    assert "p1" in q1.get("plots", {})
    assert "t1" in q1.get("transformers", {})
    assert out.get("plots") is None
    assert out.get("transformers") is None
