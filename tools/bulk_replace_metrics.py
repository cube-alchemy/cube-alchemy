#!/usr/bin/env python3
"""
Bulk replace any occurrence of the "computed metric" pair with "derived metric" across a repository.

What it does
- Recursively scans from the current working directory by default; override with --path.
- Operates on .py and .ipynb files by default; add more via --ext ".py,.ipynb,.md,...".
- Generic substring replacements (no explicit identifier lists, no word-boundaries):
  - Snake/space/kebab: computed_metric, computed metric, computed-metric (also plural: computed_metrics)
  - Camel/Pascal: ComputedMetric, computedMetrics, COMPUTEDMETRIC(S)
  - Collapsed: computedmetric(s) in any case
- Case-preserving for the words and keeps original separators and plural 's' where present.
- Dry-run by default; use --apply to write changes. No backups by default (opt-in with --backup).
- Skips common heavy/hidden dirs unless --include-hidden is used.
- Skips editing this tool file itself.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple, Callable, Union


@dataclass(frozen=True)
class Replacement:
    pattern: re.Pattern
    repl: Union[str, Callable[[re.Match], str]]
    desc: str


def smart_case(sample: str, word: str) -> str:
    """Map 'word' into the case style of 'sample'."""
    if sample.isupper():
        return word.upper()
    if sample.islower():
        return word.lower()
    if sample[0].isupper():
        return word.capitalize()
    return word


def build_replacements() -> List[Replacement]:
    replacements: List[Replacement] = []

    # 1) Separator-insensitive substring (snake/space/kebab) with optional plural 's'.
    #    Matches anywhere (no word-boundaries), preserving original separators and case.
    sep_pair = re.compile(r"(computed)([_\-\s]+)(metric)(s?)", re.IGNORECASE)

    def sep_repl(m: re.Match) -> str:
        left = smart_case(m.group(1), "derived")
        sep = m.group(2)
        metric_word = smart_case(m.group(3), "metric")
        plural = m.group(4) or ""
        return f"{left}{sep}{metric_word}{plural}"

    replacements.append(Replacement(sep_pair, sep_repl, "separator-insensitive (with optional plural)"))

    # 2) Camel/Pascal case substring: (Computed|computed|COMPUTED)(Metric|Metrics|METRIC|METRICS)
    camel = re.compile(r"(Computed|computed|COMPUTED)(Metric|Metrics|METRIC|METRICS)")

    def camel_repl(m: re.Match) -> str:
        left, right = m.group(1), m.group(2)
        # Preserve case style of the first token
        d = "DERIVED" if left.isupper() else ("Derived" if left[0].isupper() else "derived")
        # Preserve case and plurality of Metric(s)
        if right.isupper():
            met = "METRICS" if right.endswith("S") else "METRIC"
        elif right[0].isupper():
            met = "Metrics" if right.endswith("s") else "Metric"
        else:
            met = "metrics" if right.endswith("s") else "metric"
        return f"{d}{met}"

    replacements.append(Replacement(camel, camel_repl, "camel/pascal case (with optional plural)"))

    # 3) Collapsed no-separator forms (e.g., computedmetric / COMPUTEDMETRICS)
    collapsed = re.compile(r"computedmetric(s?)", re.IGNORECASE)

    def collapsed_repl(m: re.Match) -> str:
        sfx = m.group(1)  # keep original case for 's' if present
        full = m.group(0)
        if full.isupper():
            base = "DERIVEDMETRIC"
        elif full[0].isupper():
            base = "DerivedMetric"
        else:
            base = "derivedmetric"
        return base + sfx

    replacements.append(Replacement(collapsed, collapsed_repl, "collapsed no-separator (with optional plural)"))

    return replacements


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".ipynb_checkpoints",
    "site",
    "build",
    "dist",
    "egg-info",
    "cube_alchemy.egg-info",
}


def iter_files(root: Path, exts: Iterable[str], include_hidden: bool) -> Iterable[Path]:
    exts = {e.lower() for e in exts}
    for p in root.rglob("*"):
        if p.is_dir():
            continue
        if not include_hidden:
            parts = set(p.parts)
            if any(part in SKIP_DIRS or part.startswith(".") for part in parts):
                continue
        if p.suffix.lower() in exts:
            yield p


def apply_replacements(text: str, replacements: List[Replacement]) -> Tuple[str, List[str]]:
    changes: List[str] = []
    out = text
    for r in replacements:
        new = r.pattern.sub(r.repl, out)
        if new != out:
            changes.append(r.desc)
            out = new
    return out, changes


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bulk replace 'computed metric' with 'derived metric' (substring-aware).")
    parser.add_argument("--path", type=str, default=".", help="Root path to scan (default: current working directory)")
    parser.add_argument("--ext", type=str, default=".py,.ipynb", help="Comma-separated list of file extensions to include (default: .py,.ipynb)")
    parser.add_argument("--apply", action="store_true", help="Write changes to files (otherwise dry-run)")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden and typical skip dirs")
    parser.add_argument("--backup", action="store_true", help="Create .bak backups when applying (default: off)")

    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"Path not found: {root}", file=sys.stderr)
        return 2

    raw_exts = [s.strip() for s in args.ext.split(",") if s.strip()]
    exts = [e if e.startswith(".") else f".{e}" for e in raw_exts]

    replacements = build_replacements()

    # Resolve the path of this script to avoid editing itself
    self_path = Path(__file__).resolve()

    total_files = 0
    changed_files = 0
    for f in iter_files(root, exts, include_hidden=args.include_hidden):
        # Skip modifying this script itself
        try:
            if f.resolve() == self_path:
                continue
        except Exception:
            pass
        total_files += 1
        # If notebook, parse JSON and update textual fields only
        if f.suffix.lower() == ".ipynb":
            try:
                nb_obj = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                # Skip non-JSON or unreadable notebooks
                continue

            changed = False
            change_kinds: set[str] = set()

            def replace_field(val):
                nonlocal changed, change_kinds
                if isinstance(val, str):
                    new_val, kinds = apply_replacements(val, replacements)
                    if new_val != val:
                        changed = True
                        change_kinds.update(kinds)
                    return new_val
                if isinstance(val, list):
                    any_local = False
                    out_list = []
                    for item in val:
                        if isinstance(item, str):
                            new_item, kinds = apply_replacements(item, replacements)
                            if new_item != item:
                                any_local = True
                                changed = True
                                change_kinds.update(kinds)
                            out_list.append(new_item)
                        else:
                            out_list.append(item)
                    return out_list if any_local else val
                return val

            for cell in nb_obj.get("cells", []):
                if "source" in cell:
                    cell["source"] = replace_field(cell["source"])
                if cell.get("cell_type") == "code":
                    for out in cell.get("outputs", []) or []:
                        if "text" in out:
                            out["text"] = replace_field(out["text"]) 
                        data = out.get("data")
                        if isinstance(data, dict):
                            for mime, payload in list(data.items()):
                                if mime in ("text/plain", "text/markdown"):
                                    data[mime] = replace_field(payload)

            if not changed:
                continue
            changed_files += 1
            print(f"- {f.relative_to(root)}: {len(change_kinds)} change group(s): {', '.join(sorted(change_kinds))}")
            if args.apply:
                f.write_text(json.dumps(nb_obj, ensure_ascii=False), encoding="utf-8")
            continue

        # Default text file handling
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new_text, changes = apply_replacements(text, replacements)
        if not changes:
            continue
        changed_files += 1
        print(f"- {f.relative_to(root)}: {len(changes)} change group(s): {', '.join(sorted(set(changes)))}")
        if args.apply:
            if args.backup:
                bak = f.with_suffix(f.suffix + ".bak")
                try:
                    bak.write_text(text, encoding="utf-8")
                except Exception:
                    pass
            f.write_text(new_text, encoding="utf-8")

    print(
        f"\nScanned {total_files} file(s). "
        + (f"Modified {changed_files} file(s)." if args.apply else f"Would modify {changed_files} file(s).")
    )
    if not args.apply:
        print("Run again with --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

