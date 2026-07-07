# Decision Case JSON Schema

## User case

```json
{
  "id": "optional-id",
  "subject": "optional free-text topic",
  "options": [
    {
      "id": "a",
      "label": "Option A",
      "reward": 100,
      "cost": 20,
      "success_prob": 0.7
    }
  ],
  "past_events": [
    {
      "option_id": "a",
      "outcome": "success",
      "reward": 90,
      "cost": 25,
      "notes": "optional context"
    }
  ]
}
```

## Test fixture (adds ground truth)

```json
{
  "tier": "L1",
  "ground_truth": {
    "best_option_id": "a"
  }
}
```

## Fields

| Field | Required | Notes |
|-------|----------|-------|
| `options[].id` | yes | Unique per case |
| `options[].reward` | yes | Numeric payoff on success |
| `options[].cost` | yes | Cost to attempt (always incurred) |
| `options[].success_prob` | no | 0–1; if omitted, derived from `past_events` |
| `past_events[].outcome` | yes | `success`, `failure`, or `partial` |
| `past_events[].option_id` | yes | Must match an option id |

## Outcome weights

- `success` → 1.0
- `partial` → 0.5
- `failure` → 0.0

## Grokipedia sources (output)

```json
{
  "sources": [
    {
      "type": "grokipedia",
      "title": "Expected value",
      "slug": "Expected_value",
      "url": "https://grokipedia.com/page/Expected_value",
      "excerpt": "probability-weighted sum..."
    }
  ]
}
```

Retrieve via `python scripts/grokipedia-context.py "subject"`.