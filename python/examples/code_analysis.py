"""Pure-Python source analysis example."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any


def analyze_python(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    functions = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    imports = sum(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))
    return {"functions": functions, "classes": classes, "import_count": imports, "line_count": len(source.splitlines())}


def analyze_file(path: str | Path) -> dict[str, Any]:
    source_path = Path(path).expanduser().resolve()
    return {"path": str(source_path), **analyze_python(source_path.read_text(encoding="utf-8"))}


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze the structure of a Python source file.")
    parser.add_argument("path", help="Python file to analyze")
    args = parser.parse_args()
    print(json.dumps(analyze_file(args.path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
