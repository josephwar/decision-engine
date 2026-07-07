const OUTCOME_WEIGHTS = {
  success: 1.0,
  partial: 0.5,
  failure: 0.0,
};

const PRIOR_ALPHA = 1;
const PRIOR_BETA = 1;
const NEAR_TIE_MARGIN = 0.05;

function getOutcomeWeight(outcome) {
  const weight = OUTCOME_WEIGHTS[outcome];
  if (weight === undefined) {
    throw new Error(`Invalid outcome "${outcome}". Use success, partial, or failure.`);
  }
  return weight;
}

function validateCase(decisionCase) {
  if (!decisionCase?.options?.length) {
    throw new Error("Decision case must include at least one option.");
  }

  const ids = new Set();
  for (const option of decisionCase.options) {
    if (!option.id) throw new Error("Each option must have an id.");
    if (ids.has(option.id)) throw new Error(`Duplicate option id: ${option.id}`);
    ids.add(option.id);

    if (typeof option.reward !== "number" || option.reward < 0) {
      throw new Error(`Option ${option.id}: reward must be a non-negative number.`);
    }
    if (typeof option.cost !== "number" || option.cost < 0) {
      throw new Error(`Option ${option.id}: cost must be a non-negative number.`);
    }
    if (option.success_prob !== undefined) {
      if (option.success_prob < 0 || option.success_prob > 1) {
        throw new Error(`Option ${option.id}: success_prob must be between 0 and 1.`);
      }
    }
  }

  for (const event of decisionCase.past_events || []) {
    if (!ids.has(event.option_id)) {
      throw new Error(`Past event references unknown option: ${event.option_id}`);
    }
    getOutcomeWeight(event.outcome);
  }
}

function updateProbabilityFromHistory(optionId, pastEvents = []) {
  const events = pastEvents.filter((e) => e.option_id === optionId);
  if (!events.length) return null;

  let alpha = PRIOR_ALPHA;
  let beta = PRIOR_BETA;

  for (const event of events) {
    const weight = getOutcomeWeight(event.outcome);
    alpha += weight;
    beta += 1 - weight;
  }

  const mean = alpha / (alpha + beta);
  const variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1));
  const confidence = Math.min(1, (alpha + beta - 2) / 10);

  return {
    success_prob: mean,
    alpha,
    beta,
    sample_size: events.length,
    confidence,
    uncertainty: Math.sqrt(variance),
  };
}

function resolveProbability(option, pastEvents) {
  if (option.success_prob !== undefined) {
    return {
      success_prob: option.success_prob,
      source: "provided",
      confidence: 1,
      uncertainty: 0,
      sample_size: 0,
    };
  }

  const fromHistory = updateProbabilityFromHistory(option.id, pastEvents);
  if (fromHistory) {
    return { ...fromHistory, source: "history" };
  }

  return {
    success_prob: 0.5,
    source: "default",
    confidence: 0,
    uncertainty: 0.25,
    sample_size: 0,
  };
}

export function calculateExpectedValue(successProb, reward, cost) {
  return successProb * reward - cost;
}

export function scoreOption(option, pastEvents = []) {
  const prob = resolveProbability(option, pastEvents);
  const expected_value = calculateExpectedValue(
    prob.success_prob,
    option.reward,
    option.cost
  );

  return {
    id: option.id,
    label: option.label || option.id,
    reward: option.reward,
    cost: option.cost,
    success_prob: prob.success_prob,
    expected_value,
    confidence: prob.confidence,
    uncertainty: prob.uncertainty,
    sample_size: prob.sample_size,
    prob_source: prob.source,
  };
}

export function rankOptions(decisionCase) {
  validateCase(decisionCase);
  const pastEvents = decisionCase.past_events || [];

  return decisionCase.options
    .map((option) => scoreOption(option, pastEvents))
    .sort((a, b) => b.expected_value - a.expected_value);
}

export function recommend(decisionCase) {
  const ranked = rankOptions(decisionCase);
  const best = ranked[0];
  const runnerUp = ranked[1] || null;
  const margin = runnerUp
    ? best.expected_value - runnerUp.expected_value
    : best.expected_value;

  const flags = [];
  if (runnerUp && margin < NEAR_TIE_MARGIN * Math.max(Math.abs(best.reward), 1)) {
    flags.push("low_margin");
  }
  if (best.confidence < 0.3) {
    flags.push("low_confidence");
  }
  if (best.prob_source === "default") {
    flags.push("missing_data");
  }

  return {
    recommendation: best,
    runner_up: runnerUp,
    margin,
    ranked,
    flags,
    near_tie: flags.includes("low_margin"),
  };
}

export const constants = {
  OUTCOME_WEIGHTS,
  PRIOR_ALPHA,
  PRIOR_BETA,
  NEAR_TIE_MARGIN,
};