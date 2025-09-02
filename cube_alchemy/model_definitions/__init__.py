"""Model Definitions: pluggable specs loading via ABCs.

Public API:
- DefinitionSource: ABC for reading model specs.
- DefinitionRepository: ABC for storing/serving normalized specs.
- YAMLDefinitionSource: default source that reads a single YAML file.
- InMemoryRepository: simple repository implementation.
- Catalog: facade to load/refresh and query definitions.
"""

from .abc import DefinitionSource, DefinitionRepository, Spec, Key
from .repository.in_memory import InMemoryRepository
from .sources.yaml_single_file import YAMLDefinitionSource
from .service import Catalog

__all__ = [
	"DefinitionSource",
	"DefinitionRepository",
	"Spec",
	"Key",
	"InMemoryRepository",
	"YAMLDefinitionSource",
	"Catalog",
]
