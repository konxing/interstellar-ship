#!/usr/bin/env python3
"""Dependency-free test runner for the DSX-01 modelling workbench.

Discovers ``tests/test_*.py``, runs every top-level ``test_*`` callable and
reports pass/fail. No third-party test framework is required, keeping the
project runnable with only the standard library and NumPy.

Usage
-----
    python3 scripts/run_tests.py              # run everything
    python3 scripts/run_tests.py test_glb     # run modules matching a substring
    python3 scripts/run_tests.py -v           # verbose (print each test name)
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time
import traceback

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

TESTS_DIR = os.path.join(_ROOT, "tests")


def _load_module(path: str):
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(f"dsx_tests.{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filter", nargs="?", default="", help="substring to filter test modules")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    files = sorted(
        os.path.join(TESTS_DIR, f)
        for f in os.listdir(TESTS_DIR)
        if f.startswith("test_") and f.endswith(".py") and args.filter in f
    )
    if not files:
        print(f"no test modules matched {args.filter!r}")
        return 1

    passed, failed = 0, 0
    failures: list[tuple[str, str]] = []
    for path in files:
        module_name = os.path.basename(path)
        print(f"\n== {module_name}")
        try:
            module = _load_module(path)
        except Exception:  # noqa: BLE001
            failed += 1
            failures.append((module_name, traceback.format_exc()))
            print("  IMPORT ERROR")
            continue
        for name in sorted(dir(module)):
            if not name.startswith("test_"):
                continue
            fn = getattr(module, name)
            if not callable(fn):
                continue
            started = time.time()
            try:
                fn()
                passed += 1
                if args.verbose:
                    print(f"  PASS {name} ({time.time()-started:.2f}s)")
            except Exception:  # noqa: BLE001
                failed += 1
                failures.append((f"{module_name}::{name}", traceback.format_exc()))
                print(f"  FAIL {name}")
        # per-module counts line
    print(f"\n{'-' * 60}")
    print(f"passed={passed} failed={failed}")
    if failures:
        print("\nFailures:")
        for label, tb in failures:
            print(f"\n--- {label}\n{tb}")
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
