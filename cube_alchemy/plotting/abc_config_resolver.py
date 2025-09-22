from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class PlotConfigResolver(ABC):
	"""Strategy interface to complete/normalize a plot config before rendering."""

	@abstractmethod
	def resolve(self, plot_config: Dict[str, Any], query_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Return a new config with inferred defaults applied (non-mutating)."""
		raise NotImplementedError


class DefaultPlotConfigResolver(PlotConfigResolver):
	"""
	Default resolver implementing simple rules based on counts of dimensions/metrics.

	Rules (priority order for suggestions):
	  (1, 1): bar, line, area
	  (2, 1): bar(grouped), bar(stacked)
	  (1, 2): combo, bar, line
	  (1, n>=2): bar, line
	  fallback: table
	"""

	def __init__(self, fallback_plot_type: str = "table") -> None:
		# Single source of truth for candidates
		self._rules: Dict[Tuple[int, int], List[Dict[str, Any]]] = {
			(1, 1): [
				{"plot_type": "bar"},
				{"plot_type": "line"},
				{"plot_type": "area"},
				{"plot_type": "pie"},
			],
			(2, 1): [
				{"plot_type": "bar"},
				{"plot_type": "line"},
				{"plot_type": "area"},
			],
			(1, 2): [
				{"plot_type": "combo"},
				{"plot_type": "bar"},
				{"plot_type": "line"},
			],
			# Sentinel handled via _get_candidates for (1, n>=2)
		}
		self._fallback_plot_type = fallback_plot_type

	# ---------- Public API ----------
	def resolve(self, plot_config: Dict[str, Any], query_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		cfg = dict(plot_config)  # shallow copy, keep caller immutable
		if cfg.get("plot_type"):
			return cfg

		dims = cfg.get("dimensions") or (query_meta.get("dimensions", []) if query_meta else [])
		mets = cfg.get("metrics") or (
			((query_meta.get("metrics", []) or []) + (query_meta.get("derived_metrics", []) or []))
			if query_meta else []
		)
		d, m = len(dims), len(mets)

		first = self._pick_first(d, m)
		if first is None:
			cfg.setdefault("plot_type", self._fallback_plot_type)
			return cfg

		cfg.setdefault("plot_type", first.get("plot_type"))
		if "stacked" in first:
			cfg.setdefault("stacked", first["stacked"])
		return cfg

	def suggest(self, dims_count: int, metrics_count: int) -> List[Dict[str, Any]]:
		"""Return ordered suggestions decorated with descriptions and options."""
		candidates = self._get_candidates(dims_count, metrics_count)
		if not candidates:
			return [{"plot_type": self._fallback_plot_type, "description": "Tabular data", "options": {}}]

		key = self._canonical_key(dims_count, metrics_count)
		return [
			{
				"plot_type": c["plot_type"],
				"description": self._describe(key, c),
				"options": ({"stacked": c["stacked"]} if "stacked" in c else {}),
			}
			for c in candidates
		]

	# ---------- Internals ----------
	def _canonical_key(self, d: int, m: int) -> Tuple[int, int]:
		if d == 1 and m >= 2:
			return (1, 2)  # canonicalize multi-metric 1D for descriptions
		return (d, m)

	def _get_candidates(self, d: int, m: int) -> List[Dict[str, Any]]:
		# Exact match
		if (d, m) in self._rules:
			return self._rules[(d, m)]
		# Sentinel: (1, n>=2)
		if d == 1 and m >= 2:
			return [
				{"plot_type": "bar"},
				{"plot_type": "line"},
			]
		return []

	def _pick_first(self, d: int, m: int) -> Optional[Dict[str, Any]]:
		c = self._get_candidates(d, m)
		return c[0] if c else None

	def _describe(self, key: Tuple[int, int], cand: Dict[str, Any]) -> str:
		pt = cand.get("plot_type")
		if key == (1, 1):
			return (
				"Bar chart (1D, 1M)" if pt == "bar" else
				"Line chart (1D, 1M)" if pt == "line" else
				"Area chart (1D, 1M)" if pt == "area" else
				"Suggested"
			)
		if key == (2, 1):
			if pt == "bar":
				return "Stacked bars (2D, 1M)" if cand.get("stacked") else "Grouped bars (2D, 1M)"
			return "Suggested"
		if key == (1, 2):
			return (
				"Combo chart (bar + line) (1D, 2M)" if pt == "combo" else
				"Multiple series bars (1D, 2M)" if pt == "bar" else
				"Multiple series lines (1D, 2M)" if pt == "line" else
				"Suggested"
			)
		# Fallback description for any other case
		return "Suggested"


__all__ = ["PlotConfigResolver", "DefaultPlotConfigResolver"]

