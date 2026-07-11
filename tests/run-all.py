#!/usr/bin/env python3
"""Run all test tiers: L1-L6, L7, L8."""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TESTS_DIR = Path(__file__).parent
METRICS_DIR = TESTS_DIR / "metrics"

RUNNERS = [
    ("L1-L6", TESTS_DIR / "run.py"),
    ("L7", TESTS_DIR / "run-grok-tier.py"),
    ("L8", TESTS_DIR / "run-l8-tier.py"),
]


def main():
    results = []
    print("\n" + "=" * 50)
    print("  DECISION ENGINE — ALL TIERS")
    print("=" * 50)

    for label, script in RUNNERS:
        print(f"\n>>> Running {label} ({script.name})...\n")
        proc = subprocess.run([sys.executable, str(script)], cwd=TESTS_DIR.parent)
        results.append({"tier": label, "passed": proc.returncode == 0})
        if proc.returncode != 0:
            print(f"\n!!! {label} FAILED (exit {proc.returncode})")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    all_pass = passed == total

    print("\n" + "=" * 50)
    print("  SUMMARY")
    print("=" * 50)
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  [{mark}] {r['tier']}")
    print(f"\n  Tiers: {passed}/{total} passed")
    print(f"  Overall: {'PASS' if all_pass else 'FAIL'}")
    print("=" * 50 + "\n")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()