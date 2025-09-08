#!/usr/bin/env python3
"""
Normalize inline Markdown lists following headers like "Parameters:" or "Notes:" into
stacked bullet lists across all .md files under a root folder (default: docs).

Example transforms:
  Parameters: - name: ... - expression: ...
into
  Parameters:
  - name: ...
  - expression: ...

Idempotent: only rewrites when header line contains inline items after a colon.
"""

from __future__ import annotations

import argparse
from pathlib import Path


HEADERS = (
    "Parameters",
    "Notes",
    "Arguments",
    "Args",
    "Returns",
    "Raises",
)


def reformat_line(line: str) -> str:
    """If line starts with a known header and has inline items, split them into lines.

    Only triggers when the content after ":" contains " - ".
    """
    stripped = line.strip("\n")
    # Fast-path: colon must be present
    if ":" not in stripped:
        return line
    head, rest = stripped.split(":", 1)
    head = head.strip()
    if head not in HEADERS:
        return line
    # Require inline list marker in the remainder
    if " - " not in rest:
        return line
    trailing = rest.strip()
    # Split on " - " and ignore empties
    parts = [p.strip() for p in trailing.split(" - ") if p.strip()]
    if not parts:
        return line
    # Build a normalized block
    new = head + ":\n" + "\n".join([f"- {p}" for p in parts]) + "\n"
    return new


def is_list_item(s: str) -> bool:
    s = s.lstrip()
    if not s:
        return False
    # bullet or numbered list
    if s.startswith(('- ', '* ', '+ ')):
        return True
    # simple numbered list like "1. item"
    if len(s) > 2 and s[0].isdigit():
        i = 1
        while i < len(s) and s[i].isdigit():
            i += 1
        if i < len(s) and s[i:i+2] == '. ':
            return True
    return False


def process_file(path: Path) -> bool:
    src = path.read_text(encoding="utf-8")
    # Pass 1: reformat inline header lists
    pass1_lines: list[str] = []
    changed = False
    for ln in src.splitlines(keepends=True):
        new_ln = reformat_line(ln)
        pass1_lines.append(new_ln)
        if new_ln != ln:
            changed = True

    # Pass 2: insert blank line between consecutive list items outside code fences
    result_lines: list[str] = []
    in_fence = False
    prev_line_text = ""
    for ln in pass1_lines:
        stripped = ln.rstrip("\n")
        # toggle code/mermaid fences
        fence_marker = stripped.strip()
        if fence_marker.startswith("```") or fence_marker.startswith("~~~"):
            in_fence = not in_fence
            result_lines.append(ln)
            prev_line_text = stripped
            continue

        if not in_fence:
            # If current is list item and previous non-empty line was also list item, add a blank line between
            if is_list_item(stripped):
                # find previous non-empty line in result_lines
                j = len(result_lines) - 1
                prev_nonempty = None
                while j >= 0:
                    prev = result_lines[j].rstrip("\n")
                    if prev.strip() == "":
                        j -= 1
                        continue
                    prev_nonempty = prev
                    break
                if prev_nonempty is not None and is_list_item(prev_nonempty):
                    # Ensure exactly one blank line separation
                    if len(result_lines) > 0 and result_lines[-1].strip() != "":
                        result_lines.append("\n")

        result_lines.append(ln)
        prev_line_text = stripped

    new_src = "".join(result_lines)
    if new_src != src:
        path.write_text(new_src, encoding="utf-8")
        changed = True
    return changed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--root",
        type=Path,
        default=Path("docs"),
        help="Root folder to scan for .md files (default: docs)",
    )
    args = ap.parse_args()

    root: Path = args.root
    if not root.exists():
        raise SystemExit(f"Root not found: {root}")

    changed_count = 0
    total = 0
    for p in root.rglob("*.md"):
        total += 1
        try:
            if process_file(p):
                changed_count += 1
        except Exception as e:
            print(f"WARN: Failed to process {p}: {e}")
    print(f"Processed {total} files; changed {changed_count}.")


if __name__ == "__main__":
    main()
