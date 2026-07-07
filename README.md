# Decision Engine

Compare two or more options using expected value, Bayesian success probabilities from past outcomes, and optional Grokipedia-grounded research.

**Live app:** [https://josephwar.github.io/decision-engine/](https://josephwar.github.io/decision-engine/)

## Features

- Rank options by **expected value** = (success_prob × reward) − cost
- Update probabilities from **past events** (success / partial / failure)
- Graduated **test harness** (L1–L6) with efficiency metrics
- **Grokipedia** subject research via `scripts/grokipedia-context.py`
- **Grok skill** for natural-language decision analysis

## Quick start

### Web UI

```powershell
cd "C:\Users\jlgue\OneDrive\Documents\Claude\Projects\decision-engine"
python -m http.server 8080
```

Open http://localhost:8080

### Run tests

```powershell
python tests/run.py            # L1-L6 engine tests (100% gate)
python tests/run-grok-tier.py  # L7 Grok + Grokipedia tier (80% gate)
python tests/run-l8-tier.py    # L8 natural-language tier (80% gate)
```

### Analyze a case

```powershell
python scripts/run-case.py tests/fixtures/L2-01.json
```

### Grokipedia research

```powershell
python scripts/grokipedia-context.py "expected value"
```

## Grok skill

Invoke `/probabilistic-decision` in Grok to analyze decisions with the hard-task-execution loop:

1. Retrieve Grokipedia context for the subject
2. Parse past events and estimate priors
3. Run `python scripts/run-case.py` for the ranking
4. Explain the recommendation with citations

## How decisions are scored

```
Expected value = (success_probability × reward) − cost
```

When `success_prob` is omitted, the engine uses Beta-Binomial updating from `past_events`.

## Test tiers

| Tier | Focus |
|------|-------|
| L1 | 2 options, known probabilities |
| L2 | History shifts the winner |
| L3 | 3+ options |
| L4 | Near-tie margins |
| L5 | Sparse history |
| L6 | Conflicting outcomes |
| L7 | Grokipedia-informed priors (Grok supplies probabilities) |
| L8 | Natural-language decisions (parse → research → rank) |

**Gate:** 100% accuracy on L1–L6; ≥80% on L7 and L8 (accuracy + Grokipedia hit rate).

## Efficiency metrics

Logged to `tests/metrics/runs.jsonl`:

- `accuracy` — correct recommendations / total
- `tier_pass_rate` — tiers at 100%
- `margin_avg` — average EV gap between #1 and #2
- `runtime_ms` — engine execution time

## Tech

- [Grokipedia](https://grokipedia.com) — subject-grounded research
- Pure JS engine (browser) + Python mirror (CLI/tests)
- No API keys required for core engine