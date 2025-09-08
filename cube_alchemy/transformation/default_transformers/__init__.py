from __future__ import annotations

from typing import Dict

from .moving_average import MovingAverageTransformer
from .zscore import ZScoreTransformer

__all__ = [
	'DEFAULT_TRANSFORMERS',
	'MovingAverageTransformer',
	'ZScoreTransformer',
]


def DEFAULT_TRANSFORMERS() -> Dict[str, object]:
	"""Return the default transformer registry mapping name->instance.

	Keeping this as a function avoids import-time side effects and allows
	callers to selectively register transformers.
	"""
	return {
		'moving_average': MovingAverageTransformer(),
		'zscore': ZScoreTransformer(),
	}

