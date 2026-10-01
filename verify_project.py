"""Offline structural verification for Stock AI Pro.
Does not need Streamlit, yfinance, or network access.
"""
from __future__ import annotations
import ast
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent
PACKAGES = {"data", "analysis", "ai", "alerts", "backtest", "config", "indicators", "scanner", "ui"}


def module_names():
    names = set()
    for p in ROOT.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        rel = p.relative_to(ROOT).with_suffix("")
        name = ".".join(rel.parts)
        if rel.name == "__init__":
            name = ".".join(rel.parts[:-1])
        names.add(name)
    return names


def main():
    sources = [p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts]
    modules = module_names()
    missing = []
    duplicate_keys = []
    for p in sources:
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            else:
                imported = []
            for name in imported:
                if name.split(".")[0] in PACKAGES and name not in modules and not any(m.startswith(name + ".") for m in modules):
                    missing.append((str(p.relative_to(ROOT)), name))
        for line_no, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "st." in line and "key=" in line:
                import re
                m = re.search(r"key\s*=\s*['\"]([^'\"]+)['\"]", line)
                if m:
                    duplicate_keys.append((m.group(1), str(p.relative_to(ROOT)), line_no))
    counts = Counter(k for k, _, _ in duplicate_keys)
    duplicates = {k: v for k, v in counts.items() if v > 1}
    print(f"Python source files: {len(sources)}")
    print(f"Missing internal imports: {len(missing)}")
    print(f"Duplicate explicit Streamlit keys: {len(duplicates)}")
    if missing:
        for item in missing: print("MISSING:", item)
        raise SystemExit(1)
    if duplicates:
        for item in duplicates.items(): print("DUPLICATE KEY:", item)
        raise SystemExit(1)
    print("STRUCTURE OK")


if __name__ == "__main__":
    main()
