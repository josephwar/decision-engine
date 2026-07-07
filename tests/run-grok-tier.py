#!/usr/bin/env python3
"""
L7 Grok-tier tests: verify engine ranks correctly when Grok-supplied priors are applied.
Also tests Grokipedia retrieval hit rate for fixture subjects.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.core import recommend

FIXTURES_DIR = Path(__file__).parent / "fixtures"
METRICS_DIR = Path(__file__).parent / "metrics"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "grokipedia-context.py"


def load_l7_fixtures() -> list:
    fixtures = []
    for path in sorted(FIXTURES_DIR.glob("L7-*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        case["_file"] = path.name
        fixtures.append(case)
    return fixtures


def apply_inferred_priors(case: dict) -> dict:
    """Simulate Grok filling in success_prob from research + reasoning."""
    priors = case.get("ground_truth", {}).get("inferred_priors", {})
    enriched = json.loads(json.dumps(case))
    for option in enriched["options"]:
        if option["id"] in priors:
            option["success_prob"] = priors[option["id"]]
    return enriched


def test_grokipedia(subject: str) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), subject],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return {"hit": False, "error": proc.stderr.strip()}
        return json.loads(proc.stdout)
    except Exception as e:
        return {"hit": False, "error": str(e)}


def main():
    fixtures = load_l7_fixtures()
    if not fixtures:
        print("No L7 fixtures found.", file=sys.stderr)
        sys.exit(1)

    results = []
    grok_hits = 0

    print("\nL7 Grok-Tier Test Run\n" + "=" * 40)

    for case in fixtures:
        enriched = apply_inferred_priors(case)
        result = recommend(enriched)
        predicted = result["recommendation"]["id"]
        expected = case["ground_truth"]["best_option_id"]
        correct = predicted == expected

        gk = test_grokipedia(case.get("subject", ""))
        gk_hit = gk.get("hit", False)
        if gk_hit:
            grok_hits += 1

        entry = {
            "id": case["id"],
            "correct": correct,
            "predicted": predicted,
            "expected": expected,
            "grokipedia_hit": gk_hit,
            "retrieval_latency_ms": gk.get("retrieval_latency_ms"),
        }
        results.append(entry)

        mark = "PASS" if correct else "FAIL"
        gk_mark = "HIT" if gk_hit else "MISS"
        print(f"  [{mark}] {case['id']} -> {predicted} (expected {expected}) | Grokipedia [{gk_mark}]")

    correct_count = sum(1 for r in results if r["correct"])
    accuracy = correct_count / len(results)
    hit_rate = grok_hits / len(results)
    gate = accuracy >= 0.8 and hit_rate >= 0.8

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tier": "L7",
        "total": len(results),
        "correct": correct_count,
        "accuracy": round(accuracy, 3),
        "grokipedia_hit_rate": round(hit_rate, 3),
        "gate_pass": gate,
        "results": results,
    }

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    with (METRICS_DIR / "runs.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary) + "\n")

    print(f"\nL7: {correct_count}/{len(results)} ({accuracy*100:.0f}%) | Grokipedia hits: {grok_hits}/{len(results)}")
    print(f"Gate (>=80% both): {'PASS' if gate else 'FAIL'}")
    sys.exit(0 if gate else 1)


if __name__ == "__main__":
    main()