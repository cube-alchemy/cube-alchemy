from __future__ import annotations

from typing import Dict

from .moving_average import MovingAverageEnricher
from .zscore import ZScoreEnricher

__all__ = [
	'DEFAULT_ENRICHERS',
	'MovingAverageEnricher',
	'ZScoreEnricher',
]


def DEFAULT_ENRICHERS() -> Dict[str, object]:
	"""Return the default enricher registry mapping name->instance.

	Keeping this as a function avoids import-time side effects and allows
	callers to selectively register enrichers.
	"""
	return {
		'moving_average': MovingAverageEnricher(),
		'zscore': ZScoreEnricher(),
	}

