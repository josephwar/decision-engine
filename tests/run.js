import { readdir, readFile, mkdir, appendFile } from "fs/promises";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { recommend } from "../js/engine.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURES_DIR = join(__dirname, "fixtures");
const METRICS_DIR = join(__dirname, "metrics");
const METRICS_FILE = join(METRICS_DIR, "runs.jsonl");

const tierArg = process.argv.find((a) => a.startsWith("--tier="));
const filterTier = tierArg ? tierArg.split("=")[1] : null;

async function loadFixtures() {
  const files = (await readdir(FIXTURES_DIR)).filter((f) => f.endsWith(".json"));
  const fixtures = [];

  for (const file of files) {
    const content = await readFile(join(FIXTURES_DIR, file), "utf-8");
    const fixture = JSON.parse(content);
    fixture._file = file;
    if (!filterTier || fixture.tier === filterTier) {
      fixtures.push(fixture);
    }
  }

  return fixtures.sort((a, b) => a.tier.localeCompare(b.tier) || a.id.localeCompare(b.id));
}

function groupByTier(fixtures) {
  return fixtures.reduce((acc, f) => {
    (acc[f.tier] ||= []).push(f);
    return acc;
  }, {});
}

async function runFixture(fixture) {
  const start = performance.now();
  const result = recommend(fixture);
  const runtime_ms = Math.round(performance.now() - start);

  const predicted = result.recommendation.id;
  const expected = fixture.ground_truth.best_option_id;
  const correct = predicted === expected;

  return {
    id: fixture.id,
    tier: fixture.tier,
    file: fixture._file,
    correct,
    predicted,
    expected,
    margin: result.margin,
    flags: result.flags,
    runtime_ms,
    ranked: result.ranked.map((r) => ({
      id: r.id,
      ev: Math.round(r.expected_value * 1000) / 1000,
      prob: Math.round(r.success_prob * 1000) / 1000,
    })),
  };
}

async function main() {
  const fixtures = await loadFixtures();
  if (!fixtures.length) {
    console.error("No fixtures found.");
    process.exit(1);
  }

  const byTier = groupByTier(fixtures);
  const allResults = [];
  let totalCorrect = 0;

  console.log("\nDecision Engine Test Run\n" + "=".repeat(40));

  for (const tier of Object.keys(byTier).sort()) {
    const tierFixtures = byTier[tier];
    const tierResults = [];

    for (const fixture of tierFixtures) {
      const result = await runFixture(fixture);
      tierResults.push(result);
      allResults.push(result);

      const mark = result.correct ? "PASS" : "FAIL";
      console.log(`  [${mark}] ${result.id} → ${result.predicted} (expected ${result.expected})`);
      if (!result.correct) {
        console.log(`         ranked: ${result.ranked.map((r) => `${r.id}:${r.ev}`).join(", ")}`);
      }
    }

    const tierCorrect = tierResults.filter((r) => r.correct).length;
    totalCorrect += tierCorrect;
    const tierRate = ((tierCorrect / tierResults.length) * 100).toFixed(0);
    const gate = tierCorrect === tierResults.length ? "GATE PASS" : "GATE FAIL";
    console.log(`\n${tier}: ${tierCorrect}/${tierResults.length} (${tierRate}%) — ${gate}\n`);
  }

  const accuracy = totalCorrect / allResults.length;
  const avgRuntime = Math.round(
    allResults.reduce((s, r) => s + r.runtime_ms, 0) / allResults.length
  );
  const margins = allResults.map((r) => r.margin);
  const marginAvg = Math.round((margins.reduce((a, b) => a + b, 0) / margins.length) * 1000) / 1000;

  const summary = {
    timestamp: new Date().toISOString(),
    total: allResults.length,
    correct: totalCorrect,
    accuracy: Math.round(accuracy * 1000) / 1000,
    tier_pass_rate: Object.keys(byTier).filter((t) =>
      byTier[t].every((f) => allResults.find((r) => r.id === f.id)?.correct)
    ).length / Object.keys(byTier).length,
    margin_avg: marginAvg,
    runtime_ms: avgRuntime,
    filter_tier: filterTier,
    results: allResults,
  };

  await mkdir(METRICS_DIR, { recursive: true });
  await appendFile(METRICS_FILE, JSON.stringify(summary) + "\n");

  console.log("=".repeat(40));
  console.log(`Overall: ${totalCorrect}/${allResults.length} (${(accuracy * 100).toFixed(1)}%)`);
  console.log(`Margin avg: ${marginAvg} | Runtime avg: ${avgRuntime}ms`);
  console.log(`Metrics logged to tests/metrics/runs.jsonl`);

  process.exit(totalCorrect === allResults.length ? 0 : 1);
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});