"""Model Definitions: pluggable specs loading via ABCs.

Public API:
- Source: ABC for reading model specs.
- Repository: ABC for storing/serving normalized specs.
- YAMLSource: default source that reads a single YAML file.
- InMemoryRepository: simple repository implementation.
- Catalog: facade to load/refresh and query definitions.
"""

from .abc import Source, Repository, Spec, Key
from .repository.in_memory import InMemoryRepository
from .sources.yaml_single_file import YAMLSource
from .sources.yaml_model import ModelYAMLSource
from .service import Catalog

__all__ = [
	"Source",
	"Repository",
	"Spec",
	"Key",
	"InMemoryRepository",
	"YAMLSource",
	"ModelYAMLSource",
	"Catalog",
]
