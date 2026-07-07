"""Deterministic decision engine — Python mirror of js/engine.js."""

OUTCOME_WEIGHTS = {"success": 1.0, "partial": 0.5, "failure": 0.0}
PRIOR_ALPHA = 1
PRIOR_BETA = 1
NEAR_TIE_MARGIN = 0.05


def get_outcome_weight(outcome: str) -> float:
    if outcome not in OUTCOME_WEIGHTS:
        raise ValueError(f'Invalid outcome "{outcome}". Use success, partial, or failure.')
    return OUTCOME_WEIGHTS[outcome]


def validate_case(case: dict) -> None:
    options = case.get("options") or []
    if not options:
        raise ValueError("Decision case must include at least one option.")

    ids = set()
    for option in options:
        if not option.get("id"):
            raise ValueError("Each option must have an id.")
        if option["id"] in ids:
            raise ValueError(f'Duplicate option id: {option["id"]}')
        ids.add(option["id"])

        if option.get("reward", -1) < 0:
            raise ValueError(f'Option {option["id"]}: reward must be non-negative.')
        if option.get("cost", -1) < 0:
            raise ValueError(f'Option {option["id"]}: cost must be non-negative.')
        prob = option.get("success_prob")
        if prob is not None and not 0 <= prob <= 1:
            raise ValueError(f'Option {option["id"]}: success_prob must be between 0 and 1.')

    for event in case.get("past_events") or []:
        if event["option_id"] not in ids:
            raise ValueError(f'Past event references unknown option: {event["option_id"]}')
        get_outcome_weight(event["outcome"])


def update_probability_from_history(option_id: str, past_events: list) -> dict | None:
    events = [e for e in past_events if e["option_id"] == option_id]
    if not events:
        return None

    alpha, beta = PRIOR_ALPHA, PRIOR_BETA
    for event in events:
        weight = get_outcome_weight(event["outcome"])
        alpha += weight
        beta += 1 - weight

    mean = alpha / (alpha + beta)
    variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
    confidence = min(1.0, (alpha + beta - 2) / 10)

    return {
        "success_prob": mean,
        "alpha": alpha,
        "beta": beta,
        "sample_size": len(events),
        "confidence": confidence,
        "uncertainty": variance ** 0.5,
    }


def resolve_probability(option: dict, past_events: list) -> dict:
    if option.get("success_prob") is not None:
        return {
            "success_prob": option["success_prob"],
            "source": "provided",
            "confidence": 1.0,
            "uncertainty": 0.0,
            "sample_size": 0,
        }

    from_history = update_probability_from_history(option["id"], past_events)
    if from_history:
        return {**from_history, "source": "history"}

    return {
        "success_prob": 0.5,
        "source": "default",
        "confidence": 0.0,
        "uncertainty": 0.25,
        "sample_size": 0,
    }


def calculate_expected_value(success_prob: float, reward: float, cost: float) -> float:
    return success_prob * reward - cost


def score_option(option: dict, past_events: list | None = None) -> dict:
    past_events = past_events or []
    prob = resolve_probability(option, past_events)
    ev = calculate_expected_value(prob["success_prob"], option["reward"], option["cost"])

    return {
        "id": option["id"],
        "label": option.get("label") or option["id"],
        "reward": option["reward"],
        "cost": option["cost"],
        "success_prob": prob["success_prob"],
        "expected_value": ev,
        "confidence": prob["confidence"],
        "uncertainty": prob["uncertainty"],
        "sample_size": prob["sample_size"],
        "prob_source": prob["source"],
    }


def rank_options(case: dict) -> list:
    validate_case(case)
    past_events = case.get("past_events") or []
    ranked = [score_option(opt, past_events) for opt in case["options"]]
    ranked.sort(key=lambda r: r["expected_value"], reverse=True)
    return ranked


def recommend(case: dict) -> dict:
    ranked = rank_options(case)
    best = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    margin = best["expected_value"] - runner_up["expected_value"] if runner_up else best["expected_value"]

    flags = []
    if runner_up and margin < NEAR_TIE_MARGIN * max(abs(best["reward"]), 1):
        flags.append("low_margin")
    if best["confidence"] < 0.3:
        flags.append("low_confidence")
    if best["prob_source"] == "default":
        flags.append("missing_data")

    return {
        "recommendation": best,
        "runner_up": runner_up,
        "margin": margin,
        "ranked": ranked,
        "flags": flags,
        "near_tie": "low_margin" in flags,
    }