#!/usr/bin/env python3
"""Test runner for decision engine fixtures."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.core import recommend

FIXTURES_DIR = Path(__file__).parent / "fixtures"
METRICS_DIR = Path(__file__).parent / "metrics"
METRICS_FILE = METRICS_DIR / "runs.jsonl"


ENGINE_TIERS = {"L1", "L2", "L3", "L4", "L5", "L6"}


def load_fixtures(tier_filter: str | None = None) -> list:
    fixtures = []
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        case["_file"] = path.name
        tier = case.get("tier", "")
        if tier_filter:
            if tier == tier_filter:
                fixtures.append(case)
        elif tier in ENGINE_TIERS:
            fixtures.append(case)
    return sorted(fixtures, key=lambda c: (c.get("tier", ""), c.get("id", "")))


def run_fixture(case: dict) -> dict:
    start = time.perf_counter()
    result = recommend(case)
    runtime_ms = round((time.perf_counter() - start) * 1000)

    predicted = result["recommendation"]["id"]
    expected = case["ground_truth"]["best_option_id"]

    return {
        "id": case["id"],
        "tier": case["tier"],
        "file": case["_file"],
        "correct": predicted == expected,
        "predicted": predicted,
        "expected": expected,
        "margin": result["margin"],
        "flags": result["flags"],
        "runtime_ms": runtime_ms,
        "ranked": [
            {
                "id": r["id"],
                "ev": round(r["expected_value"], 3),
                "prob": round(r["success_prob"], 3),
            }
            for r in result["ranked"]
        ],
    }


def main():
    tier_filter = None
    for arg in sys.argv[1:]:
        if arg.startswith("--tier="):
            tier_filter = arg.split("=", 1)[1]

    fixtures = load_fixtures(tier_filter)
    if not fixtures:
        print("No fixtures found.", file=sys.stderr)
        sys.exit(1)

    by_tier: dict[str, list] = {}
    for f in fixtures:
        by_tier.setdefault(f["tier"], []).append(f)

    all_results = []
    total_correct = 0

    print("\nDecision Engine Test Run\n" + "=" * 40)

    for tier in sorted(by_tier):
        tier_results = []
        for case in by_tier[tier]:
            result = run_fixture(case)
            tier_results.append(result)
            all_results.append(result)

            mark = "PASS" if result["correct"] else "FAIL"
            print(f"  [{mark}] {result['id']} -> {result['predicted']} (expected {result['expected']})")
            if not result["correct"]:
                ranked_str = ", ".join(f"{r['id']}:{r['ev']}" for r in result["ranked"])
                print(f"         ranked: {ranked_str}")

        tier_correct = sum(1 for r in tier_results if r["correct"])
        total_correct += tier_correct
        tier_rate = round(tier_correct / len(tier_results) * 100)
        gate = "GATE PASS" if tier_correct == len(tier_results) else "GATE FAIL"
        print(f"\n{tier}: {tier_correct}/{len(tier_results)} ({tier_rate}%) — {gate}\n")

    accuracy = total_correct / len(all_results)
    avg_runtime = round(sum(r["runtime_ms"] for r in all_results) / len(all_results))
    margin_avg = round(sum(r["margin"] for r in all_results) / len(all_results), 3)

    tiers_passed = sum(
        1 for t in by_tier if all(r["correct"] for r in all_results if r["tier"] == t)
    )

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(all_results),
        "correct": total_correct,
        "accuracy": round(accuracy, 3),
        "tier_pass_rate": round(tiers_passed / len(by_tier), 3),
        "margin_avg": margin_avg,
        "runtime_ms": avg_runtime,
        "filter_tier": tier_filter,
        "results": all_results,
    }

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    with METRICS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary) + "\n")

    print("=" * 40)
    print(f"Overall: {total_correct}/{len(all_results)} ({accuracy * 100:.1f}%)")
    print(f"Margin avg: {margin_avg} | Runtime avg: {avg_runtime}ms")
    print(f"Metrics logged to tests/metrics/runs.jsonl")

    sys.exit(0 if total_correct == len(all_results) else 1)


if __name__ == "__main__":
    main()