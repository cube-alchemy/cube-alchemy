from __future__ import annotations

from typing import Dict, List, Any, Optional, Callable, Union
import copy
import pandas as pd
from cube_alchemy.transformation.abc import Transformer
from cube_alchemy.transformation.default_transformers import DEFAULT_TRANSFORMERS

class Transformation:
    """
    Query Transformation mixin: single-step query augmentation.

    - Register transformers (plugins) that take a dataframe and add analytical features (e.g., moving average, z-score, rank).
    - Transformations operate over available dimensions, metrics, and derived metrics in the query DataFrame.
    - Each query can configure at most one transformation per transformer.
    """

    def __init__(self) -> None:
    # { query_name: { transformer: {params...} } }
        if not hasattr(self, 'transformation_components'):
            self.transformation_components: Dict[str, Dict[str, Any]] = {}
        # registry: name -> Transformer or callable(df, **params)->df
        if not hasattr(self, 'transformers'):
            self.transformers: Dict[str, Union[Transformer, Callable[..., pd.DataFrame]]] = {}

        # Register the default transformers
        try:
            for name, instance in (DEFAULT_TRANSFORMERS() or {}).items():
                self.register_transformer(name, instance)
        except Exception:
            pass

    # Registry
    def register_transformer(self, name: str, transformer: Union[Transformer, Callable[..., pd.DataFrame]]) -> None:
        if not name or not isinstance(name, str):
            raise ValueError("Transformer name must be a non-empty string")
        self.transformers[name] = transformer

    # Definition management (single-step per transformer; transformer is the key)
    def define_transformation(
        self,
        query_name: str,
        transformer: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Define/update an transformation for a query.

        Storage shape per query: { transformer_name: {params...} }
        Each query can have at most one transformation per transformer.
        """
        if not transformer or not isinstance(transformer, str):
            raise ValueError("'transformer' must be a non-empty string")
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            # We keep this strict to mirror Plotting consistency
            raise ValueError(f"Query '{query_name}' not defined")

        qstate = self.transformation_components.setdefault(query_name, {})
        qstate[transformer] = dict(params or {})

        # dependency index registration (use transformer as the identifier)
        try:
            if hasattr(self, '_dep_index') and self._dep_index is not None:
                self._dep_index.add(query_name, 'transformation', transformer)
        except Exception:
            pass

    def list_transformations(self, query_name: str) -> List[str]:
        """Return the list of transformer names configured for the query."""
        qstate = self.transformation_components.get(query_name)
        if not qstate:
            return []
        return list(qstate.keys())

    def get_transformation_config(self, query_name: str, transformer: Optional[str] = None) -> Dict[str, Any]:
        """Return params for the given transformer on the query."""
        qstate = self.transformation_components.get(query_name)
        if not qstate:
            raise ValueError(f"Query '{query_name}' has no transformation configurations.")
        if transformer is None:
            raise ValueError("transformer is required when retrieving an transformation config.")
        cfg = qstate.get(transformer)
        if cfg is None:
            raise ValueError(f"Transformer '{transformer}' not found for query '{query_name}'.")
        return copy.deepcopy(cfg)

    def delete_transformation(self, query_name: str, transformer: str) -> None:
        qstate = self.transformation_components.get(query_name)
        if not qstate or transformer not in qstate:
            return
        del qstate[transformer]
    
    def transform(
        self,
        df: pd.DataFrame,
        transformer: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        *,
        overwrite: bool = False,
        copy_input: bool = False,
        **overrides,
    ) -> pd.DataFrame:
        """
        Run a single-step transformation on the provided DataFrame.
        """
        if not transformer:
            raise ValueError("'transformer' is required")
        eff_params: Dict[str, Any] = dict(params or {})
        if overrides:
            eff_params.update(overrides)
        eff_params['_log'] = getattr(self, '_log', None)

        # Optionally copy input
        out = df.copy() if copy_input else df

        transformer = self.transformers.get(transformer)
        if transformer is None:
            raise ValueError(f"Transformer '{transformer}' is not registered. Use register_transformer().")

        # Execute transformer
        if isinstance(transformer, Transformer):
            new_df = transformer.transform(out, **eff_params)
        elif callable(transformer):
            new_df = transformer(out if not copy_input else out.copy(), **eff_params)
        else:
            raise TypeError(f"Transformer '{transformer}' must be an Transformer or a callable.")

        # Merge policy
        if overwrite:
            out = new_df
        else:
            added = [c for c in new_df.columns if c not in out.columns]
            if added:
                out = out.join(new_df[added])
        return out

