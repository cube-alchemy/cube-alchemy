#!/usr/bin/env python3
"""
Generate UML class and package diagrams for the cube_alchemy project using Pyreverse.

Outputs DOT or PlantUML sources and can optionally render images (SVG/PNG)
when Graphviz (dot) or PlantUML is available.

Examples (PowerShell):
  # Generate DOT and render to SVG
  python tools/generate_uml.py --target cube_alchemy --format dot --render svg --out artifacts/uml

  # Generate PlantUML sources only
  python tools/generate_uml.py --target cube_alchemy --format plantuml --out artifacts/uml

Requirements:
- Pyreverse (ships with pylint): pip install pylint
- For rendering DOT: Graphviz binary 'dot' on PATH
- For PlantUML rendering (not done here): use your PlantUML tool to convert .plantuml to images
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import ast
from typing import Optional, Set, Tuple, Dict, List


def _pyreverse_supports(flag: str) -> bool:
    """Return True if `pyreverse --help` output mentions `flag`.

    This avoids invoking pyreverse with unsupported flags that sometimes get
    misinterpreted as module names (e.g. "--ignore-patterns"), which leads to
    confusing ImportError traces like "No module named --ignore-patterns".
    """
    exe = shutil.which("pyreverse")
    if not exe:
        return False
    try:
        res = subprocess.run([exe, "--help"], check=False, capture_output=True, text=True)
        help_text = (res.stdout or "") + (res.stderr or "")
        return flag in help_text
    except Exception:
        return False


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> int:
    print("$ ", " ".join(cmd))
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, check=False)
        return p.returncode
    except FileNotFoundError:
        return 127


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", default="cube_alchemy", help="Python package or path to analyze (default: cube_alchemy)")
    # Only PlantUML is supported now
    ap.add_argument("--format", choices=["plantuml"], default="plantuml", help="Output format for pyreverse (only plantuml)")
    ap.add_argument("--out", type=Path, default=Path("artifacts/uml"), help="Output directory (default: artifacts/uml)")
    # Rendering of DOT removed; use your PlantUML tool to render .plantuml if needed
    ap.add_argument("--ignore", default="tests,site,docs,.venv,.git,__pycache__", help="Comma-separated paths to ignore")
    ap.add_argument("--project", default="cube_alchemy", help="Project name used by pyreverse -p (default: cube_alchemy)")
    ap.add_argument("--filter", dest="filter_mode", default="ALL", help="pyreverse filter mode (PUBLIC, SPECIAL, ALL). Default: ALL to include private members")
    ap.add_argument("--augment-assoc", dest="augment_assoc", action="store_true", default=True, help="Infer associations from container annotations (Dict/List/Optional/Union) and inject into PlantUML output (default: on)")
    args = ap.parse_args(argv)

    out_dir: Path = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Check pyreverse
    if shutil.which("pyreverse") is None:
        print("ERROR: pyreverse not found. Install with: pip install pylint", file=sys.stderr)
        return 1

    # Build pyreverse command, probing for supported ignore flag to avoid
    # ImportError traces like "No module named --ignore-patterns".
    cmd = [
        "pyreverse",
        "-o",
        args.format,
        "-p",
        args.project,
    ]
    # Include private members so associations on _attributes show up
    if args.filter_mode:
        if _pyreverse_supports("-f ") or _pyreverse_supports("-f\n") or _pyreverse_supports("-f, --filter-mode"):
            cmd += ["-f", args.filter_mode]
        elif _pyreverse_supports("--filter-mode"):
            cmd += ["--filter-mode", args.filter_mode]
    if args.ignore:
        if _pyreverse_supports("--ignore-patterns"):
            cmd += ["--ignore-patterns", args.ignore]
        elif _pyreverse_supports("--ignore"):
            cmd += ["--ignore", args.ignore]
        # else: no ignore flag available; proceed without
    cmd.append(args.target)

    # Run pyreverse in a temporary working directory to avoid littering repo root
    repo_root = Path.cwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        env = os.environ.copy()
        # Ensure the project can be imported when running from tmpdir
        env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")

        rc = run(cmd, cwd=tmp_path, env=env)
        if rc != 0:
            print("pyreverse failed", file=sys.stderr)
            return rc

        # Determine produced files in tmpdir. pyreverse uses:
        # - classes(.|_<project>).dot / packages(.|_<project>).dot for DOT
        # - classes(.|_<project>).puml or .plantuml for PlantUML
        produced: list[Path] = []
        base_candidates = [
            tmp_path / "classes.puml",
            tmp_path / "packages.puml",
            tmp_path / f"classes_{args.project}.puml",
            tmp_path / f"packages_{args.project}.puml",
            tmp_path / "classes.plantuml",
            tmp_path / "packages.plantuml",
            tmp_path / f"classes_{args.project}.plantuml",
            tmp_path / f"packages_{args.project}.plantuml",
        ]

        for f in base_candidates:
            if f.exists():
                produced.append(f)
            else:
                print(f"WARN: expected output not found: {f}")

        # Copy produced artifacts to output directory
        copied: list[Path] = []
        for f in produced:
            dest = out_dir / f.name
            dest.write_bytes(f.read_bytes())
            print(f"Saved {dest}")
            copied.append(dest)

    # Optional: augment PlantUML with inferred associations from type annotations
    if args.format == "plantuml" and args.augment_assoc:
        try:
            _augment_plantuml_with_inferred_associations(out_dir, args.target)
        except Exception as e:
            print(f"WARN: failed to augment PlantUML associations: {e}")


    return 0


def _augment_plantuml_with_inferred_associations(out_dir: Path, target: str) -> None:
    """Scan the source package for container annotations that reference other
    classes and inject additional associations into the PlantUML output.

    This helps when pyreverse does not follow Dict/List/Optional/Union inner types.
    """
    repo_root = Path.cwd()
    pkg_path = (repo_root / target.replace(".", "/")).resolve()
    if not pkg_path.exists():
        # If target is a file or module path wasn't found, do nothing
        return

    # 1) Discover class names in target package
    class_names: Set[str] = set()
    for py in pkg_path.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_names.add(node.name)

    # 2) Collect associations: (owner, child, role)
    associations: Set[Tuple[str, str, str]] = set()
    for py in pkg_path.rglob("*.py"):
        try:
            src = py.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                owner = node.name
                # class-level annotations (e.g., metrics: Dict[str, Metric])
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        role = stmt.target.id
                        types = _extract_referenced_types(stmt.annotation)
                        for t in types:
                            if t in class_names:
                                associations.add((owner, t, role))
                # instance-level annotated assignments inside methods (self.attr: Type = ...)
                for stmt in node.body:
                    if isinstance(stmt, ast.FunctionDef):
                        # Infer from instance-level annotated assignments
                        for sub in ast.walk(stmt):
                            if isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Attribute):
                                # look for self.<name>: T
                                if isinstance(sub.target.value, ast.Name) and sub.target.value.id == 'self':
                                    role = sub.target.attr
                                    types = _extract_referenced_types(sub.annotation)
                                    for t in types:
                                        if t in class_names:
                                            associations.add((owner, t, role))
                        # Infer from __init__(self, param: Iterable[Source]) -> self.attr = param
                        if stmt.name == "__init__":
                            # Map parameter names to their annotated element types
                            param_elem_types: Dict[str, Set[str]] = {}
                            for arg, ann in zip(stmt.args.args, getattr(stmt.args, 'annotations', []) or []):
                                pass  # safety for older ASTs
                            for arg in stmt.args.args:
                                if arg.arg == 'self':
                                    continue
                                ann = getattr(arg, 'annotation', None)
                                if ann is not None:
                                    param_elem_types[arg.arg] = _extract_referenced_types(ann)
                            # Look for assignments: self.<attr> = <param>
                            for sub in ast.walk(stmt):
                                if isinstance(sub, ast.Assign):
                                    if len(sub.targets) == 1 and isinstance(sub.targets[0], ast.Attribute):
                                        tgt = sub.targets[0]
                                        if isinstance(tgt.value, ast.Name) and tgt.value.id == 'self':
                                            role = tgt.attr
                                            # RHS cases:
                                            # 1) Name(param)
                                            # 2) Call like list(param)/tuple(param)/set(param)
                                            pname: Optional[str] = None
                                            if isinstance(sub.value, ast.Name):
                                                pname = sub.value.id
                                            elif isinstance(sub.value, ast.Call):
                                                # one-arg call wrapping a parameter
                                                if len(sub.value.args) == 1 and isinstance(sub.value.args[0], ast.Name):
                                                    pname = sub.value.args[0].id
                                            if pname:
                                                elem_types = param_elem_types.get(pname, set())
                                                for t in elem_types:
                                                    if t in class_names:
                                                        associations.add((owner, t, role))
                            # calls/instantiations: e.g., MetricGroup(...)
                            if isinstance(sub, ast.Call):
                                callee = sub.func
                                name: Optional[str] = None
                                if isinstance(callee, ast.Name):
                                    name = callee.id
                                elif isinstance(callee, ast.Attribute):
                                    name = callee.attr
                                if name and name in class_names:
                                    associations.add((owner, name, "uses"))

    if not associations:
        return

    # 3) Insert association lines into any PlantUML classes file
    for puml in list(out_dir.glob("classes*.puml")) + list(out_dir.glob("classes*.plantuml")):
        try:
            text = puml.read_text(encoding="utf-8")
        except Exception:
            continue
        lines = text.splitlines()

        # Build display->alias map from class declarations like:
        # class "Hypercube" as cube_alchemy.core.hypercube.Hypercube {
        import re
        name_to_alias: Dict[str, str] = {}
        display_names: Set[str] = set()
        decl_re = re.compile(r'^\s*class\s+"([^"]+)"\s+as\s+([^\s{]+)')
        for l in lines:
            m = decl_re.match(l)
            if m:
                display, alias = m.group(1), m.group(2)
                name_to_alias[display] = alias
                display_names.add(display)
        try:
            end_idx = max(i for i, l in enumerate(lines) if l.strip().lower() == "@enduml")
        except ValueError:
            # No @enduml, append at end
            end_idx = len(lines)

        # Avoid duplicates: build set of existing association lines
        existing = set(l.strip() for l in lines)

        # Remove previously injected short-name associations that cause duplicate nodes
        assoc_short_re = re.compile(r'^\s*([A-Za-z_][\w]*)\s*\*--\s*([A-Za-z_][\w]*)\s*:')
        cleaned_lines: List[str] = []
        for l in lines:
            m = assoc_short_re.match(l.strip())
            if m:
                a, b = m.group(1), m.group(2)
                # If both are display names (no dots) and present in declarations, drop line
                if a in display_names and b in display_names:
                    continue
            cleaned_lines.append(l)
        lines = cleaned_lines

        # Globally remove any 'uses' relation lines to hide usage-only dependencies
        # Example patterns:
        #   X *-- Y : uses
        #   X ..> Y : uses
        no_uses_lines: List[str] = []
        for l in lines:
            if ": uses" in l:
                continue
            no_uses_lines.append(l)
        lines = no_uses_lines
        existing = set(l.strip() for l in lines)
        injected: List[str] = []
        for owner, child, role in sorted(associations):
            owner_alias = name_to_alias.get(owner)
            child_alias = name_to_alias.get(child)
            if not owner_alias or not child_alias:
                continue  # skip if we can't resolve aliases; prevents duplicate nodes

            # Skip all call-based 'uses' dependencies completely
            if role == "uses":
                continue

            # Use composition for attribute-backed links only
            arrow = "*--"
            assoc_line = f"{owner_alias} {arrow} {child_alias} : {role}"
            if assoc_line not in existing:
                injected.append(assoc_line)

        # Merge injected lines, then canonicalize and de-duplicate composition edges
        merged_lines = lines[:end_idx] + injected + lines[end_idx:]

        # Build alias->display map for owner/child resolution
        alias_to_display = {v: k for k, v in name_to_alias.items()}

        # Index associations by (owner_alias, child_alias, role) for orientation guidance
        assoc_owner_lookup: Set[Tuple[str, str, str]] = set()
        for owner, child, role in associations:
            owner_alias = name_to_alias.get(owner)
            child_alias = name_to_alias.get(child)
            if owner_alias and child_alias:
                assoc_owner_lookup.add((owner_alias, child_alias, role))

        import re as _re
        assoc_dir_re = _re.compile(r"^\s*([^\s{]+)\s*(\*--|--\*|o--|--o)\s*([^\s{]+)\s*:\s*([^\n]+?)\s*$")

        seen_keys: Set[Tuple[frozenset, str]] = set()
        deduped: List[str] = []
        for l in merged_lines:
            m = assoc_dir_re.match(l)
            if not m:
                deduped.append(l)
                continue
            a1, arrow, a2, role_label = m.group(1), m.group(2), m.group(3), m.group(4).strip()
            # Build key ignoring direction
            key = (frozenset({a1, a2}), role_label)
            if key in seen_keys:
                # skip duplicate
                continue
            # Decide preferred orientation: if AST told us owner->child for this role, use that
            owner_alias = None
            child_alias = None
            if (a1, a2, role_label) in assoc_owner_lookup:
                owner_alias, child_alias = a1, a2
            elif (a2, a1, role_label) in assoc_owner_lookup:
                owner_alias, child_alias = a2, a1
            else:
                # Fallback to deterministic order
                owner_alias, child_alias = sorted([a1, a2])

            # Canonicalize to composition arrow for attribute-backed links
            canon_line = f"{owner_alias} *-- {child_alias} : {role_label}"
            deduped.append(canon_line)
            seen_keys.add(key)

        # Add light layout hints if not present
        def _inject_layout_hints(lines_in: List[str]) -> List[str]:
            out_l = []
            injected = False
            for line in lines_in:
                out_l.append(line)
                if not injected and line.strip().lower().startswith("set namespaceseparator"):
                    out_l.append("left to right direction")
                    out_l.append("skinparam nodesep 20")
                    out_l.append("skinparam ranksep 30")
                    injected = True
                if line.strip().lower().startswith("@startuml") and not injected:
                    out_l.append("left to right direction")
                    out_l.append("skinparam nodesep 20")
                    out_l.append("skinparam ranksep 30")
                    injected = True
            return out_l

        deduped = _inject_layout_hints(deduped)

        # Group by owner -> children using only declared aliases and create HIDDEN edges
        # instead of 'together { ... }' blocks to avoid PlantUML creating empty nodes.
        declared_aliases: Set[str] = set(name_to_alias.values())
        owner_children: Dict[str, Set[str]] = {}
        for owner, child, role in associations:
            o = name_to_alias.get(owner)
            c = name_to_alias.get(child)
            if not o or not c:
                continue
            if o not in declared_aliases or c not in declared_aliases or o == c:
                continue
            owner_children.setdefault(o, set()).add(c)

        # Before injecting our hidden edges, strip any previous 'together { ... }' blocks
        stripped: List[str] = []
        skipping = False
        for l in deduped:
            lt = l.strip()
            if not skipping and lt.startswith("together {"):
                skipping = True
                continue
            if skipping:
                if lt == "}":
                    skipping = False
                continue
            stripped.append(l)
        deduped = stripped

        hidden_edges: List[str] = []
        emitted_groups: Set[frozenset] = set()
        for o, kids in owner_children.items():
            members = {o, *kids}
            if len(members) < 3:
                continue  # only cluster meaningful sets
            key = frozenset(members)
            if key in emitted_groups:
                continue
            emitted_groups.add(key)
            chain = sorted(members)
            # Create a simple chain of hidden edges to pull nodes together
            for a, b in zip(chain, chain[1:]):
                edge = f"{a} -[hidden]-> {b}"
                if edge not in existing:
                    hidden_edges.append(edge)

        if hidden_edges:
            try:
                end_idx2 = max(i for i, l in enumerate(deduped) if l.strip().lower() == "@enduml")
            except ValueError:
                end_idx2 = len(deduped)
            deduped = deduped[:end_idx2] + hidden_edges + deduped[end_idx2:]

        puml.write_text("\n".join(deduped), encoding="utf-8")
        print(f"Augmented associations in {puml} (+{len(injected)}) — deduplicated, added {len(hidden_edges)} hidden edges for clustering")


def _extract_referenced_types(annotation: ast.AST) -> Set[str]:
    """Return a set of class names referenced by a type annotation, with
    special handling for Dict/List/Optional/Union constructs.
    """
    out: Set[str] = set()

    def _dotted_name(attr: ast.Attribute) -> str:
        parts: List[str] = []
        cur: Optional[ast.AST] = attr
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value  # type: ignore[assignment]
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        parts.reverse()
        return ".".join(parts)

    def add_from(node: Optional[ast.AST]):
        if node is None:
            return
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Use full dotted path to avoid collisions with in-package class names
            out.add(_dotted_name(node))
        elif isinstance(node, ast.Subscript):
            # Handle generics: Dict[K,V], List[T], Optional[T], Union[A,B]
            base = node.value
            arg = node.slice
            base_name = None
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr

            # Py3.9+: slice is the actual node; older versions used ast.Index
            args: List[ast.AST] = []
            if isinstance(arg, ast.Tuple):
                args = list(arg.elts)
            else:
                args = [arg]

            # Normalize Optional[T] -> [T]
            if base_name in {"Optional"}:
                for a in args:
                    add_from(a)
                return
            # Union[A,B]
            if base_name in {"Union"}:
                for a in args:
                    add_from(a)
                return
            # Dict[K,V] / Mapping[K,V]
            if base_name in {"Dict", "Mapping"}:
                if len(args) == 2:
                    add_from(args[1])  # value type
                return
            # List/Set/Sequence/Iterable[T]
            if base_name in {"List", "Set", "Sequence", "Iterable"}:
                for a in args:
                    add_from(a)
                return
            # Fallback: visit generically
            for a in args:
                add_from(a)
        elif isinstance(node, ast.BinOp):
            # Rare: A | B (PEP 604 unions). Collect both sides if present.
            add_from(getattr(node, 'left', None))
            add_from(getattr(node, 'right', None))
        # else: ignore other node kinds

    add_from(annotation)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
