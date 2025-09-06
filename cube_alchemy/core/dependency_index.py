from typing import Dict, Set, Tuple

# Dependent is a tuple of (kind, name), e.g., ('query', 'Sales by Country') or ('plot', 'Default bar')
Dependent = Tuple[str, str]


class DependencyIndex:
    """Reverse index of components (analytics and plotting) dependencies: source name -> set of dependents.

    Example edges:
    - 'Revenue' -> {('query', 'Sales by Country')}
    - 'Sales by Country' -> {('plot', 'Default bar')}
    """

    def __init__(self) -> None:
        self._idx: Dict[str, Set[Dependent]] = {}

    def add(self, source: str, kind: str, name: str) -> None:
        if not source or not kind or not name:
            return
        self._idx.setdefault(source, set()).add((kind, name))

    def get(self, source: str) -> Set[Dependent]:
        return self._idx.get(source, set())

    def pop(self, source: str) -> Set[Dependent]:
        return self._idx.pop(source, set())

    def remove_query(self, query_name: str) -> None:
        """Remove all edges pointing to a given query."""
        target = ('query', query_name)
        for deps in self._idx.values():
            deps.discard(target)

    def remove_plot(self, plot_name: str) -> None:
        """Remove all edges pointing to a given plot."""
        target = ('plot', plot_name)
        for deps in self._idx.values():
            deps.discard(target)

    def clear(self) -> None:
        self._idx.clear()

    # Debug/export helpers
    def snapshot(self) -> Dict[str, Set[Dependent]]:
        """Return a shallow copy of the internal mapping for inspection."""
        return {k: set(v) for k, v in self._idx.items()}
