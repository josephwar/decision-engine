#!/usr/bin/env python3
"""
L8 natural-language tier: simulates Grok parsing NL -> structured case, then engine + Grokipedia.

In production, Grok parses natural_language into parsed_case. This runner uses ground_truth.parsed_case
as the expected parse output to verify the full pipeline end-to-end.
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
GK_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "grokipedia-context.py"


def load_l8_fixtures() -> list:
    fixtures = []
    for path in sorted(FIXTURES_DIR.glob("L8-*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        case["_file"] = path.name
        fixtures.append(case)
    return fixtures


def build_case_from_parse(fixture: dict) -> dict:
    """Simulate Grok: NL -> structured case (+ optional inferred priors)."""
    parsed = json.loads(json.dumps(fixture["ground_truth"]["parsed_case"]))
    priors = fixture["ground_truth"].get("inferred_priors", {})
    for option in parsed.get("options", []):
        if option["id"] in priors:
            option["success_prob"] = priors[option["id"]]
    return parsed


def test_grokipedia(subject: str) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, str(GK_SCRIPT), subject],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return {"hit": False, "error": proc.stderr.strip()}
        return json.loads(proc.stdout)
    except Exception as e:
        return {"hit": False, "error": str(e)}


def validate_parse_fidelity(fixture: dict, parsed: dict) -> bool:
    """Check parsed case has minimum required fields."""
    if not parsed.get("options") or len(parsed["options"]) < 2:
        return False
    for opt in parsed["options"]:
        if not all(k in opt for k in ("id", "reward", "cost")):
            return False
    return True


def main():
    fixtures = load_l8_fixtures()
    if not fixtures:
        print("No L8 fixtures found.", file=sys.stderr)
        sys.exit(1)

    results = []
    gk_hits = 0
    parse_ok = 0

    print("\nL8 Natural-Language Tier Test Run\n" + "=" * 40)

    for fixture in fixtures:
        nl_preview = fixture["natural_language"][:60] + "..."
        parsed = build_case_from_parse(fixture)
        parse_valid = validate_parse_fidelity(fixture, parsed)
        if parse_valid:
            parse_ok += 1

        result = recommend(parsed)
        predicted = result["recommendation"]["id"]
        expected = fixture["ground_truth"]["best_option_id"]
        correct = predicted == expected

        subject = parsed.get("subject", "")
        gk = test_grokipedia(subject) if subject else {"hit": False}
        gk_hit = gk.get("hit", False)
        if gk_hit:
            gk_hits += 1

        entry = {
            "id": fixture["id"],
            "correct": correct,
            "predicted": predicted,
            "expected": expected,
            "parse_valid": parse_valid,
            "grokipedia_hit": gk_hit,
            "retrieval_latency_ms": gk.get("retrieval_latency_ms"),
            "nl_preview": nl_preview,
        }
        results.append(entry)

        mark = "PASS" if correct else "FAIL"
        gk_mark = "HIT" if gk_hit else "MISS"
        print(f"  [{mark}] {fixture['id']} -> {predicted} (expected {expected}) | Parse [{'OK' if parse_valid else 'BAD'}] | GK [{gk_mark}]")

    correct_count = sum(1 for r in results if r["correct"])
    accuracy = correct_count / len(results)
    hit_rate = gk_hits / len(results)
    parse_rate = parse_ok / len(results)
    gate = accuracy >= 0.8 and hit_rate >= 0.8 and parse_rate >= 1.0

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tier": "L8",
        "total": len(results),
        "correct": correct_count,
        "accuracy": round(accuracy, 3),
        "grokipedia_hit_rate": round(hit_rate, 3),
        "parse_fidelity_rate": round(parse_rate, 3),
        "gate_pass": gate,
        "results": results,
    }

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    with (METRICS_DIR / "runs.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary) + "\n")

    print(f"\nL8: {correct_count}/{len(results)} ({accuracy*100:.0f}%)")
    print(f"Parse fidelity: {parse_ok}/{len(results)} | Grokipedia: {gk_hits}/{len(results)}")
    print(f"Gate (>=80% accuracy & GK, 100% parse): {'PASS' if gate else 'FAIL'}")
    sys.exit(0 if gate else 1)


if __name__ == "__main__":
    main()