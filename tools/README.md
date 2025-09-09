# Developer tools

Small, focused utilities to help maintain and refactor this repo.

## Tools index

- bulk_replace_metrics.py — refactors any substring variant of "computed metric" to "derived metric" across files and notebooks.
- bulk_replace_enrich_to_transform.py — refactors root word "enrich*" (enrichment, enricher, enrich/ed/es/ing) to the "transform*" family.
- format_md_lists.py — normalizes inline Markdown lists after headers (Parameters/Notes/Args/Returns/Raises) into stacked bullet lists; idempotent.
- generate_uml.py — produces class/package diagrams (DOT/PlantUML) for the `cube_alchemy` package using Pyreverse; optionally renders PNG/SVG when Graphviz/PlantUML are available.

## Quick usage (PowerShell)

- Preview computed→derived changes for code and notebooks
  - python tools/bulk_replace_metrics.py --path . --ext .py,.ipynb
  - Apply with backups: python tools/bulk_replace_metrics.py --path . --ext .py,.ipynb --apply --backup

- Preview enrich*→transform* changes
  - python tools/bulk_replace_enrich_to_transform.py --path . --ext .py,.ipynb
  - Apply with backups: python tools/bulk_replace_enrich_to_transform.py --path . --ext .py,.ipynb --apply --backup

- Reformat Markdown lists (defaults to docs/)
  - python tools/format_md_lists.py --root docs

- Generate UML for cube_alchemy
  - PlantUML source (recommended for large projects):
    - python tools/generate_uml.py --target cube_alchemy --format plantuml --out artifacts/uml
    - Outputs classes.puml/packages.puml (or .plantuml depending on version) into artifacts/uml.
    - Render to images with your PlantUML runner/editor.
  - DOT + SVG images (requires Graphviz):
    - python tools/generate_uml.py --target cube_alchemy --format dot --render svg --out artifacts/uml
    - Outputs classes.dot/packages.dot and renders classes.svg/packages.svg.

### Requirements for UML

- Pyreverse (bundled with pylint): pip install pylint
- For rendering DOT to images: Graphviz binary `dot` on PATH (https://graphviz.org/)
- For PlantUML images: use any PlantUML renderer (VS Code extension, CLI, or server) to convert .puml/.plantuml files.

### Troubleshooting

- ImportError: No module named --ignore-patterns
  - Different pyreverse versions expose either `--ignore-patterns` or `--ignore`. The script probes `pyreverse --help` and uses whichever is supported.
  - If both are missing, it runs without an ignore filter.

- WARN: expected output not found: classes.plantuml
  - Some pyreverse versions write `.puml` instead of `.plantuml`. The script looks for both and copies whatever exists to `artifacts/uml`.

- Render step says Graphviz `dot` not found
  - Install Graphviz and ensure `dot` is on PATH, or run with `--render none` and post-process DOT/PUML yourself.

## Other useful maintenance tools to consider

- Quality: ruff (lint+fix), black (format), isort (imports), mypy/pyright (types), bandit (security)
- Testing: pytest + coverage, hypothesis (property-based), tox/nox (multi-env)
- Repo hygiene: pre-commit (hook runner), commitizen or cz-git (conventional commits)
- Docs: mkdocs-material, mkdocstrings (Python), mike (versioned docs)
- Graphs/visuals: pydeps (import graph), pyan3 (call graph), grimp (imports), pyreverse (UML)
- CI: GitHub Actions for lint/test/build/docs

## Notes

- The refactoring tools skip heavy/hidden/build directories by default and won’t edit themselves.
- Always run in dry-run first, then apply with backups when changing identifiers.
