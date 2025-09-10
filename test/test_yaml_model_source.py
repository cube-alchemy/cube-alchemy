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
@pytest.mark.parametrize("prefer_plots, prefer_transformers", [(True, True), (True, False), (False, True)])
def test_save_renests_known_queries(tmp_path: Path, prefer_plots: bool, prefer_transformers: bool) -> None:
    # initial YAML with top-level plots/transformers; some reference a known query, others don't
    ypath = tmp_path / "model.yaml"
    write_yaml(ypath, {
        "queries": {
            "q1": {"dimensions": ["a"]},
        },
        "plots": {
            "p1": {"type": "bar", "query": "q1"},  # should nest under q1 if prefer_plots
            "p2": {"type": "line"},                   # stays top-level
        },
        "transformers": {
            "t1": {"paramA": 1, "query": "q1"},     # should nest under q1 if prefer_transformers
            "t2": {"paramB": 2},                       # stays top-level
        },
    })

    src = ModelYAMLSource(ypath, prefer_nested_plots=prefer_plots, prefer_nested_transformers=prefer_transformers)

    # Save round-trip to trigger _preprocess_to_save behavior
    data = src._load()  # normalized with kind/name
    src.save(data)

    out = read_yaml(ypath)

    # queries.q1 should exist and preserve base fields
    assert "queries" in out and "q1" in out["queries"]
    q1 = out["queries"]["q1"]

    # Plots: p1 nested only when prefer_plots
    if prefer_plots:
        assert "plots" in q1 and "p1" in q1["plots"]
        assert out.get("plots", {}).get("p1") is None  # not top-level anymore
    else:
        # when not preferring nesting, p1 remains top-level and not nested
        assert "plots" not in q1 or "p1" not in q1.get("plots", {})
        assert out.get("plots", {}).get("p1") is not None

    # p2 never had a query; must remain top-level
    assert "p2" in out.get("plots", {})

    # Transformers: t1 nested only when prefer_transformers
    if prefer_transformers:
        assert "transformers" in q1 and "t1" in q1["transformers"]
        assert out.get("transformers", {}).get("t1") is None
    else:
        assert "transformers" not in q1 or "t1" not in q1.get("transformers", {})
        assert out.get("transformers", {}).get("t1") is not None

    # t2 never had a query; must remain top-level
    assert "t2" in out.get("transformers", {})


@pytest.mark.unit
def test_save_clears_top_level_when_all_nested(tmp_path: Path) -> None:
    ypath = tmp_path / "model.yaml"
    write_yaml(ypath, {
        "queries": {
            "q1": {"dimensions": ["a"]},
        },
        "plots": {
            "p1": {"type": "bar", "query": "q1"},
        },
        "transformers": {
            "t1": {"paramA": 1, "query": "q1"},
        },
    })
    src = ModelYAMLSource(ypath, prefer_nested_plots=True, prefer_nested_transformers=True)
    data = src._load()
    src.save(data)
    out = read_yaml(ypath)

    # Everything should be under queries.q1; no top-level sections remain
    q1 = out["queries"]["q1"]
    assert "plots" in q1 and "p1" in q1["plots"]
    assert "transformers" in q1 and "t1" in q1["transformers"]
    assert out.get("plots") is None
    assert out.get("transformers") is None


@pytest.mark.unit
def test_load_lifts_nested_sections_to_top_level_with_query(tmp_path: Path) -> None:
    ypath = tmp_path / "model.yaml"
    write_yaml(ypath, {
        "queries": {
            "q1": {
                "dimensions": ["a"],
                "plots": {"p1": {"type": "bar"}},
                "transformers": {"t1": {"paramA": 1}},
            },
        },
        "plots": {"p2": {"type": "line"}},
        "transformers": {"t2": {"paramB": 2}},
    })
    src = ModelYAMLSource(ypath)
    data = src._load()

    # lifted to top-level with query annotation
    assert "p1" in data.get("plots", {})
    assert data["plots"]["p1"].get("query") == "q1"
    assert "t1" in data.get("transformers", {})
    assert data["transformers"]["t1"].get("query") == "q1"

    # original top-level remain
    assert "p2" in data.get("plots", {})
    assert "t2" in data.get("transformers", {})

    # queries.q1 no longer contains nested sections after lift
    q1 = data["queries"]["q1"]
    assert "plots" not in q1
    assert "transformers" not in q1

    # kind/name should be present in normalized specs
    assert data["plots"]["p1"]["kind"] == "plots"
    assert data["plots"]["p1"]["name"] == "p1"
    assert data["transformers"]["t1"]["kind"] == "transformers"
    assert data["transformers"]["t1"]["name"] == "t1"
