#!/usr/bin/env python3
"""Run decision engine on a JSON case file or stdin."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.core import recommend


def main():
    if len(sys.argv) > 1:
        case = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        case = json.load(sys.stdin)

    result = recommend(case)
    output = {
        "recommendation": result["recommendation"],
        "runner_up": result["runner_up"],
        "margin": round(result["margin"], 4),
        "flags": result["flags"],
        "ranked": [
            {
                **r,
                "expected_value": round(r["expected_value"], 4),
                "success_prob": round(r["success_prob"], 4),
            }
            for r in result["ranked"]
        ],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()