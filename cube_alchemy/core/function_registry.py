from __future__ import annotations

from typing import Any, Dict, Optional
import importlib
import inspect

import pandas as pd 
import numpy as np  


def DEFAULT_REGISTERED_FUNCTIONS() -> Dict[str, Any]:
    """Return the default function/module registry for expressions and aggregations.

    Kept as a function to avoid import-time side effects and allow easy extension.
    """
    

    base: Dict[str, Any] = {"pd": pd, "np": np}
    return base


class FunctionRegistry(dict):
    """A dict subclass registry that pickles as import specs and rehydrates on load.

    Key goals:
    - Be a real dict so eval(..., globals, ...) accepts it.
    - On pickle, store import specs (module or module:qualname) for entries.
    - On unpickle, import and resolve specs back to live objects.
    - Skip non-importable entries (lambdas/closures/bound methods) silently.
    """

    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(initial or {})

    # Serialization helpers
    @staticmethod
    def _to_spec(obj: Any) -> Optional[str]:
        """Convert an object to an import spec if possible.

        Returns a string spec or None if unsupported.
        Specs:
        - module:<module_name>
        - obj:<module_name>:<qualname>
        """
        if inspect.ismodule(obj):
            name = getattr(obj, "__name__", None)
            if name:
                return f"module:{name}"
            return None
        if inspect.isclass(obj) or inspect.isfunction(obj):
            mod = getattr(obj, "__module__", None)
            qn = getattr(obj, "__qualname__", None)
            if mod and qn and "<locals>" not in qn:
                return f"obj:{mod}:{qn}"
            return None
        # Methods or callables bound to instances are not supported
        return None

    @staticmethod
    def _from_spec(spec: str) -> Any:
        kind, payload = spec.split(":", 1)
        if kind == "module":
            return importlib.import_module(payload)
        if kind == "obj":
            mod_name, qual = payload.split(":", 1)
            mod = importlib.import_module(mod_name)
            obj = mod
            for part in qual.split("."):
                obj = getattr(obj, part)
            return obj
        raise ValueError(f"Unknown spec kind: {kind}")

    # Custom pickling: export specs and rebuild via a classmethod
    def __reduce_ex__(self, protocol: int):  # type: ignore[override]
        specs: Dict[str, str] = {}
        for name, obj in self.items():
            spec = self._to_spec(obj)
            if spec is not None:
                specs[name] = spec
        return (self.__class__._from_specs, (specs,))

    @classmethod
    def _from_specs(cls, specs: Dict[str, str]) -> "FunctionRegistry":
        inst = cls()
        for name, spec in specs.items():
            try:
                inst[name] = cls._from_spec(spec)
            except Exception:
                # Silently ignore broken specs
                pass
        return inst

    # Factories
    @classmethod
    def from_defaults(cls, extra: Optional[Dict[str, Any]] = None) -> "FunctionRegistry":
        base = DEFAULT_REGISTERED_FUNCTIONS()
        if extra:
            base.update(extra)
        return cls(base)
