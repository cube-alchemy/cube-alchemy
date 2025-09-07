from __future__ import annotations

from typing import Dict, List, Any, Optional, Callable, Union
import copy
import pandas as pd
from cube_alchemy.enrichment.abc import Enricher
from cube_alchemy.enrichment.default_enrichers import DEFAULT_ENRICHERS

class Enrichment:
    """
    Query Enrichment mixin: single-step query augmentation.

    - Register enrichers (plugins) that take a dataframe and add analytical features (e.g., moving average, z-score, rank).
    - Enrichments operate over available dimensions, metrics, and computed metrics in the query DataFrame.
    - Each query can configure at most one enrichment per transformer.
    """

    def __init__(self) -> None:
    # { query_name: { transformer: {params...} } }
        if not hasattr(self, 'enrichment_components'):
            self.enrichment_components: Dict[str, Dict[str, Any]] = {}
        # registry: name -> Enricher or callable(df, **params)->df
        if not hasattr(self, 'enrichers'):
            self.enrichers: Dict[str, Union[Enricher, Callable[..., pd.DataFrame]]] = {}

        # Register the default enrichers
        try:
            for name, instance in (DEFAULT_ENRICHERS() or {}).items():
                self.register_enricher(name, instance)
        except Exception:
            pass

    # Registry
    def register_enricher(self, name: str, enricher: Union[Enricher, Callable[..., pd.DataFrame]]) -> None:
        if not name or not isinstance(name, str):
            raise ValueError("Enricher name must be a non-empty string")
        self.enrichers[name] = enricher

    # Definition management (single-step per enricher; transformer is the key)
    def define_enrichment(
        self,
        query_name: str,
        transformer: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Define/update an enrichment for a query.

        Storage shape per query: { transformer_name: {params...} }
        Each query can have at most one enrichment per transformer.
        """
        if not transformer or not isinstance(transformer, str):
            raise ValueError("'transformer' must be a non-empty string")
        if not hasattr(self, 'queries') or query_name not in getattr(self, 'queries', {}):
            # We keep this strict to mirror Plotting consistency
            raise ValueError(f"Query '{query_name}' not defined")

        qstate = self.enrichment_components.setdefault(query_name, {})
        qstate[transformer] = dict(params or {})

        # dependency index registration (use transformer as the identifier)
        try:
            if hasattr(self, '_dep_index') and self._dep_index is not None:
                self._dep_index.add(query_name, 'enrichment', transformer)
        except Exception:
            pass

    def list_enrichments(self, query_name: str) -> List[str]:
        """Return the list of transformer names configured for the query."""
        qstate = self.enrichment_components.get(query_name)
        if not qstate:
            return []
        return list(qstate.keys())

    def get_enrichment_config(self, query_name: str, transformer: Optional[str] = None) -> Dict[str, Any]:
        """Return params for the given transformer on the query."""
        qstate = self.enrichment_components.get(query_name)
        if not qstate:
            raise ValueError(f"Query '{query_name}' has no enrichment configurations.")
        if transformer is None:
            raise ValueError("transformer is required when retrieving an enrichment config.")
        cfg = qstate.get(transformer)
        if cfg is None:
            raise ValueError(f"Transformer '{transformer}' not found for query '{query_name}'.")
        return copy.deepcopy(cfg)

    def delete_enrichment(self, query_name: str, transformer: str) -> None:
        qstate = self.enrichment_components.get(query_name)
        if not qstate or transformer not in qstate:
            return
        del qstate[transformer]
    def enrich(
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
        Run a single-step enrichment on the provided DataFrame.
        """
        if not transformer:
            raise ValueError("'transformer' is required")
        eff_params: Dict[str, Any] = dict(params or {})
        if overrides:
            eff_params.update(overrides)

        # Optionally copy input
        out = df.copy() if copy_input else df

        enricher = self.enrichers.get(transformer)
        if enricher is None:
            raise ValueError(f"Enricher '{transformer}' is not registered. Use register_enricher().")

        # Execute enricher
        if isinstance(enricher, Enricher):
            new_df = enricher.enrich(out, **eff_params)
        elif callable(enricher):
            new_df = enricher(out if not copy_input else out.copy(), **eff_params)
        else:
            raise TypeError(f"Enricher '{transformer}' must be an Enricher or a callable.")

        # Merge policy
        if overwrite:
            out = new_df
        else:
            added = [c for c in new_df.columns if c not in out.columns]
            if added:
                out = out.join(new_df[added])
        return out

