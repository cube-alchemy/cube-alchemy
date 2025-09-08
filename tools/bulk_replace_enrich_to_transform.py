#!/usr/bin/env python3
"""
Bulk replace any occurrence of the root word "enrich" with the corresponding
"transform" form across a repository, preserving case and common morphology.

Like the computed→derived tool, this is substring-aware: it replaces matches even
when they appear inside identifiers (e.g., define_enrichment, register_enricher,
DefineEnrichment). Use with care as it will refactor code identifiers.

What it does
- Recursively scans from the current working directory by default; override with --path.
- Operates on .py and .ipynb files by default; add more via --ext ".py,.ipynb,.md,...".
- Replacements (substring, case/morphology preserving; order matters):
  - enrichment(s) -> transformation(s)
  - enricher(s)   -> transformer(s)
  - enrich(ed|es|ing)? -> transform(ed|s|ing)
  - Handles UPPER, lower, Title/Camel case.
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


def apply_case(sample: str, word: str) -> str:
    """Map 'word' into the case style of 'sample'."""
    if sample.isupper():
        return word.upper()
    if sample.islower():
        return word.lower()
    if sample[0].isupper():
        return word.capitalize()
    return word


def build_replacements() -> List[Replacement]:
    reps: List[Replacement] = []

    # 1) enrichment(s) -> transformation(s) [substring-aware]
    enrichment = re.compile(r"(enrichment)(s?)", re.IGNORECASE)

    def enrichment_repl(m: re.Match) -> str:
        base = apply_case(m.group(1), "transformation")
        plural = m.group(2)
        if plural:
            if m.group(0).isupper():
                base += plural.upper()
            else:
                base += "s"
        return base

    reps.append(Replacement(enrichment, enrichment_repl, "enrichment->transformation"))

    # 2) enricher(s) -> transformer(s) [substring-aware]
    enricher = re.compile(r"(enricher)(s?)", re.IGNORECASE)

    def enricher_repl(m: re.Match) -> str:
        base = apply_case(m.group(1), "transformer")
        plural = m.group(2)
        if plural:
            if m.group(0).isupper():
                base += plural.upper()
            else:
                base += "s"
        return base

    reps.append(Replacement(enricher, enricher_repl, "enricher->transformer"))

    # 3) enrich(ed|es|ing)? -> transform(ed|s|ing) [substring-aware]
    enrich = re.compile(r"(enrich)(ed|es|ing)?", re.IGNORECASE)

    def enrich_repl(m: re.Match) -> str:
        root = apply_case(m.group(1), "transform")
        suf = (m.group(2) or "").lower()
        suf_map = {"ed": "ed", "es": "s", "ing": "ing"}
        mapped = suf_map.get(suf, "")
        if m.group(0).isupper():
            return (root + mapped).upper()
        return root + mapped

    reps.append(Replacement(enrich, enrich_repl, "enrich-verb forms"))

    return reps


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


def apply_replacements(text: str, reps: List[Replacement]) -> Tuple[str, List[str]]:
    changes: List[str] = []
    out = text
    for r in reps:
        new = r.pattern.sub(r.repl, out)
        if new != out:
            changes.append(r.desc)
            out = new
    return out, changes


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bulk replace 'enrich*' with 'transform*' (substring/case aware).")
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
        try:
            if f.resolve() == self_path:
                continue
        except Exception:
            pass
        total_files += 1

        if f.suffix.lower() == ".ipynb":
            try:
                nb_obj = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
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
