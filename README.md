# Find Your Best B2B ICP From Real Evidence

Give your AI agent a product page, service document, or offer URL. This skill compares exactly 3 B2B customer segments, scores each one against the same 7 criteria, and returns one search-ready ICP backed by current sources.

Most ICP exercises end with a broad label such as "agencies" or "SaaS companies." That is not enough to build a lead list, choose a message, or decide who to stop targeting.

This skill forces the decision.

## What you get

- Exactly 3 specific customer segments defined by industry, company size, geography, operating condition, trigger, and affected process
- Comparable evidence for all 3 candidates, including buyer language and reasons each segment may fail
- A reproducible weighted score across pain, timing, budget, reachability, delivery fit, speed to revenue, and deal potential
- A deep research report for the winner only
- A search-ready ICP definition you can hand to Apollo, Instantly, Lemlist, Google Maps, or another lead source
- A source ledger that separates facts, buyer quotes, estimates, inferences, and counterevidence

## The decision rule

The bundled scorer weighs 7 factors:

| Factor | Weight |
|---|---:|
| Pain severity | 20% |
| Trigger strength | 15% |
| Ability to pay | 15% |
| Reachability | 15% |
| Solution and delivery fit | 15% |
| Time to revenue | 10% |
| Deal potential | 10% |

Active disqualifiers remove a segment even when its score is high. Close scores use evidence confidence, time to revenue, and delivery fit as tie-breakers.

## Install

For Claude Code:

```bash
mkdir -p ~/.claude/skills
cp -R skills/find-b2b-icp ~/.claude/skills/
```

For Codex:

```bash
mkdir -p ~/.codex/skills
cp -R skills/find-b2b-icp ~/.codex/skills/
```

No paid API key is built into the skill. Your agent needs current web research and local Python execution.

## Run it

Give the agent one of these:

- A public product or service URL
- A local offer document
- Pasted offer copy

Then ask:

```text
Use find-b2b-icp on this offer. Compare the 3 strongest customer segments and tell me which one I should target first: https://example.com/offer
```

You can also add hard limits:

```text
Use find-b2b-icp on this service document. We sell in the US, need deals above $5,000, cannot serve regulated healthcare, and want a sales cycle under 60 days.
```

The skill asks a follow-up only when missing information would change the candidate set.

## What the agent does

1. Extracts the offer, price band, proof, constraints, delivery limits, and current sales motion.
2. Creates 3 narrow candidate segments.
3. Collects the same evidence classes for all 3, including evidence against the fit.
4. Runs `scripts/score_icp.py` so the winner is calculated from the published rubric.
5. Researches the winner across company fit, current pain, desired results, roadblocks, and MEDDICC.
6. Runs `scripts/build_report.py` to reject incomplete or unsupported reports.
7. Returns the final report plus the saved Markdown and JSON files.

## Evidence rules

- Current triggers should be no older than 90 days.
- Company and technology signals should be no older than 12 months.
- Market research should be no older than 24 months.
- Search-result snippets are leads, not final evidence.
- Estimates show their formula and assumptions.
- Inferences name the facts they came from.
- Every candidate includes counterevidence.

If public evidence is thin, the report lowers confidence instead of filling gaps with guesses.

## Check the package

Run the included regression tests:

```bash
cd skills/find-b2b-icp
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/score_icp.py \
  --input eval/fixtures/score_input.json \
  --json-output /tmp/icp-scored.json \
  --markdown-output /tmp/icp-scored.md
python3 scripts/build_report.py \
  --score-input eval/fixtures/score_input.json \
  --research-input eval/fixtures/report_input.json \
  --output /tmp/icp-report.md
```

The scripts use the Python standard library. There is no package install step.

## Files

- `skills/find-b2b-icp/SKILL.md`: agent workflow
- `skills/find-b2b-icp/references/evidence-contract.md`: source and confidence rules
- `skills/find-b2b-icp/references/scoring-rubric.md`: 7-factor decision model
- `skills/find-b2b-icp/references/output-contract.md`: report schema and sales handoff
- `skills/find-b2b-icp/scripts/score_icp.py`: deterministic scorer
- `skills/find-b2b-icp/scripts/build_report.py`: final report validator and renderer
- `skills/find-b2b-icp/tests/`: regression tests

## License

MIT. Use it, adapt it, and share it.

## Next step

If you want the winning ICP turned into a live outbound system for your agency, the [24/7 Pipeline Engine](https://aiessentials.us/24-7-pipeline-engine) handles the targeting, data, outreach, and booking flow. Stuck? Email `iliyan.ivanov.mp@gmail.com` or [book a call](https://aiessentials.us/).
