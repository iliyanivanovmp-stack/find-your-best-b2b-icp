# Evidence contract

## Comparable candidate packs

Research the same questions for all three candidates before scoring. Each candidate targets at least six independent source items:

1. Two buyer-voice items from different publishers or communities.
2. One market-size, firmographic, or economic source.
3. One current trigger or timing signal.
4. One process, technology, or buying-committee source.
5. One counterevidence or disqualifier source.

This is a target, not permission to fabricate. A shortfall lowers confidence and remains visible.

## Evidence types

| Type | Meaning | Required fields |
|---|---|---|
| `FACT` | Externally verifiable observation | claim, source name, URL, publication date when available, access date |
| `VOICE` | Exact buyer or practitioner language | short quote, role or context, source name, URL, publication date when available |
| `ESTIMATE` | Calculated number or range | formula, inputs, assumptions, sensitivity |
| `INFERENCE` | Analyst conclusion from named evidence | reasoning and supporting evidence IDs |
| `COUNTEREVIDENCE` | Evidence against fit or urgency | claim, source name, URL, implication |

Never cite an `INFERENCE` or `ESTIMATE` as an observed fact. Never convert an inaccessible search result into a read source.

## Source hierarchy

Prefer sources in this order:

1. Company filings, official product documentation, regulatory sources, job postings, and primary research.
2. Named practitioners, buyer communities, review platforms, implementation partners, and trade associations.
3. Reputable industry publications and analyst research.
4. Aggregators and search snippets only for discovery, not as final evidence when the underlying source is available.

Avoid counting syndicated copies, repeated press releases, or multiple pages from one study as independent confirmation.

## Freshness

- Trigger and current-company signals: no older than 90 days.
- Company facts, hiring, and technology signals: no older than 12 months.
- Market reports and benchmarks: no older than 24 months.
- Older sources must be labeled `foundational` and cannot prove current urgency.

## Confidence

- High: at least six source items across five named publishers, two buyer-voice sources from different publishers, one counterevidence item, and one current trigger.
- Medium: at least four source items across three named publishers, one buyer-voice source, and one counterevidence item.
- Low: anything below medium or any material unresolved contradiction.

Freshness is calculated against the report's `research_date`, not the source access date. Access dates must be within 30 days of the research date.

Confidence describes evidence coverage, not whether the segment is attractive.

## Access failures

Record the source, attempted URL, date, and failure reason. Use accessible alternatives. Do not infer what a gated page probably said.

