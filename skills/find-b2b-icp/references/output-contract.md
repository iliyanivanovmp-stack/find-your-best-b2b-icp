# Output contract

## User-facing order

Begin with one line and nothing before it:

`**Top 3 ICPs:** [Candidate A] · [Candidate B] · [Candidate C]`

Then provide:

1. Scoring table with weighted totals, eligibility, evidence confidence, and the winner.
2. Three to five sentences explaining the winner and material counterevidence.
3. Comparable candidate evidence summary.
4. Winner-only four-phase research.
5. Short verbatim buyer quotes tagged by phase and evidence ID.
6. Winner-only example account signals.
7. Search-ready sales handoff.
8. Evidence ledger, access failures, assumptions, and unresolved unknowns.

## Score input JSON

```json
{
  "offer": "short offer description",
  "research_date": "YYYY-MM-DD",
  "candidates": [
    {
      "name": "specific candidate definition",
      "definition": {
        "industry": "...",
        "company_size": "...",
        "geography": "...",
        "operating_condition": "...",
        "trigger": "...",
        "affected_process": "..."
      },
      "active_disqualifiers": [],
      "scores": {
        "pain_severity": {"score": 8, "evidence_ids": ["E001"], "reason": "..."},
        "trigger_strength": {"score": 7, "evidence_ids": ["E002"], "reason": "..."},
        "ability_to_pay": {"score": 6, "evidence_ids": ["E003"], "reason": "..."},
        "reachability": {"score": 8, "evidence_ids": ["E004"], "reason": "..."},
        "solution_delivery_fit": {"score": 9, "evidence_ids": ["E005"], "reason": "..."},
        "time_to_revenue": {"score": 8, "evidence_ids": ["E006"], "reason": "..."},
        "deal_potential": {"score": 7, "evidence_ids": ["E007"], "reason": "..."}
      }
    }
  ],
  "evidence": [
    {
      "evidence_id": "E001",
      "candidate": "exact candidate name",
      "evidence_type": "FACT",
      "claim": "material claim",
      "source_name": "publisher or source",
      "source_url": "https://...",
      "published_at": "YYYY-MM-DD or not available",
      "accessed_at": "YYYY-MM-DD",
      "freshness_class": "trigger|company|market|foundational|not_applicable"
    }
  ]
}
```

The `candidates` array contains exactly three items. Every `definition` contains exactly the six fields shown above. Use exactly the seven scoring keys shown above. Evidence IDs are unique. Every score includes a reason and cites at least one valid evidence ID assigned to that candidate.

For `VOICE`, add `quote` and `role_context`. For `ESTIMATE`, add `formula`, `assumptions`, and `sensitivity`. For `INFERENCE`, add `reasoning` and `supporting_evidence_ids`. For `COUNTEREVIDENCE`, add `implication`.

## Search-ready handoff template

| Field | Winner definition |
|---|---|
| Industry and sub-niche | |
| Employee band | |
| Revenue band | |
| Geography | |
| Operating condition | |
| Required trigger | |
| Economic buyer | |
| Champion | |
| Technology signals | |
| Exclusions | |
| Search filters | |

## Final report research input

Use `eval/fixtures/report_input.json` as the executable schema example. It requires:

- selected winner and three to five justification sentences
- one comparable evidence summary for each candidate
- all required fields in winner phases 1 through 4
- exactly three KPI targets with baseline, assumption, formula, range, sensitivity, and evidence IDs
- all seven MEDDICC fields
- at least two winner buyer quotes that exactly match `VOICE` evidence, are tagged to a phase, and stay within 25 words per source
- no more than five complete account-signal records
- every field in the search-ready handoff
- access failures, assumptions, and unresolved unknowns as explicit lists

Run `scripts/build_report.py`. It rejects incomplete reports, unsupported or cross-candidate citations, invalid evidence, missing handoff fields, and silent winner overrides. An override requires a non-empty reason plus either a named business constraint or complete new evidence with IDs absent from the scoring ledger.

