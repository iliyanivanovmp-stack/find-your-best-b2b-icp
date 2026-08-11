#!/usr/bin/env python3
"""Validate and render the complete B2B ICP report from structured research."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import date
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("score_icp", SCRIPT_DIR / "score_icp.py")
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)

PHASE_FIELDS = {
    "phase_1": {"firmographics_economics", "technographics", "buying_committee", "triggers", "jobs_to_be_done"},
    "phase_2": {"stuck_kpis", "costs", "broken_processes", "failed_attempts", "risks", "buyer_language", "cost_of_inaction"},
    "phase_3": {"kpi_targets", "operational_change", "budget_source", "proof_required", "stakeholder_wins"},
    "phase_4": {"roadblocks", "meddicc", "primary_constraint", "pilot", "unknowns"},
}
MEDDICC_FIELDS = {"metrics", "economic_buyer", "decision_criteria", "decision_process", "identify_pain", "champion", "competition"}
HANDOFF_FIELDS = {
    "industry_sub_niche", "employee_band", "revenue_band", "geography", "operating_condition",
    "required_triggers", "economic_buyer", "champion", "technology_signals", "exclusions", "search_filters",
}


def nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value) and all(nonempty(item) for item in value.values()) if isinstance(value, dict) else all(nonempty(item) for item in value)
    return value is not None


def validate_report(score_input: dict[str, Any], research: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    scored = SCORER.score_payload(score_input)
    candidate_names = [candidate["name"] for candidate in score_input["candidates"]]
    evidence_map = {item["evidence_id"]: item for item in score_input["evidence"]}
    selected = research.get("selected_winner")
    if selected not in candidate_names:
        raise SCORER.ValidationError("selected_winner must match one of the three candidates")
    if selected != scored["winner"]:
        override = research.get("override")
        required = {"mechanical_winner", "selected_winner", "new_evidence", "business_constraint", "reason"}
        if not isinstance(override, dict) or set(override) != required:
            raise SCORER.ValidationError("overriding the mechanical result requires the complete override object")
        if override["mechanical_winner"] != scored["winner"] or override["selected_winner"] != selected:
            raise SCORER.ValidationError("override winner fields do not match the scoring result")
        if not isinstance(override["reason"], str) or not override["reason"].strip():
            raise SCORER.ValidationError("override requires a non-empty reason")
        constraint = override["business_constraint"]
        new_evidence = override["new_evidence"]
        if not isinstance(new_evidence, list) or not isinstance(constraint, str):
            raise SCORER.ValidationError("override new_evidence must be a list and business_constraint must be a string")
        if not constraint.strip() and not new_evidence:
            raise SCORER.ValidationError("override requires new evidence or a named business constraint")
        for item in new_evidence:
            if item.get("evidence_id") in evidence_map:
                raise SCORER.ValidationError("override evidence IDs must be new, not reused scoring evidence")
            SCORER.validate_evidence_item(item, date.fromisoformat(score_input["research_date"]))
            if item.get("candidate") != selected:
                raise SCORER.ValidationError("override evidence must belong to the selected winner")
            evidence_map[item["evidence_id"]] = item
        for item in new_evidence:
            if item.get("evidence_type") == "INFERENCE":
                for supporting_id in item.get("supporting_evidence_ids", []):
                    supporting = evidence_map.get(supporting_id)
                    if not supporting:
                        raise SCORER.ValidationError("override inference cites unknown supporting evidence")
                    if supporting.get("candidate") != selected:
                        raise SCORER.ValidationError("override inference cites another candidate's evidence")
        SCORER.validate_inference_graph(evidence_map)

    justification = research.get("winner_justification")
    if not isinstance(justification, list) or not 3 <= len(justification) <= 5 or not all(nonempty(x) for x in justification):
        raise SCORER.ValidationError("winner_justification must contain three to five non-empty sentences")

    summaries = research.get("candidate_summaries", [])
    if len(summaries) != 3 or {item.get("candidate") for item in summaries} != set(candidate_names):
        raise SCORER.ValidationError("candidate_summaries must contain all three candidates exactly once")
    for summary in summaries:
        if not nonempty(summary.get("summary")):
            raise SCORER.ValidationError(f"{summary.get('candidate')} summary is empty")
        for key in ("evidence_ids", "counterevidence_ids"):
            ids = summary.get(key, [])
            if not ids or any(item not in evidence_map for item in ids):
                raise SCORER.ValidationError(f"{summary.get('candidate')} has invalid or empty {key}")
            if any(evidence_map[item].get("candidate") != summary["candidate"] for item in ids):
                raise SCORER.ValidationError(f"{summary.get('candidate')} {key} cites another candidate")
        if any(evidence_map[item]["evidence_type"] != "COUNTEREVIDENCE" for item in summary["counterevidence_ids"]):
            raise SCORER.ValidationError(f"{summary.get('candidate')} counterevidence_ids must cite COUNTEREVIDENCE")

    phases = research.get("winner_research", {})
    if set(phases) != set(PHASE_FIELDS):
        raise SCORER.ValidationError("winner_research must contain exactly phase_1 through phase_4")
    for phase, fields in PHASE_FIELDS.items():
        if not isinstance(phases[phase], dict) or set(phases[phase]) != fields:
            raise SCORER.ValidationError(f"{phase} must contain exactly {sorted(fields)}")
        if not all(nonempty(value) for value in phases[phase].values()):
            raise SCORER.ValidationError(f"{phase} contains empty values")
    if set(phases["phase_4"]["meddicc"]) != MEDDICC_FIELDS:
        raise SCORER.ValidationError("phase_4 MEDDICC must contain all seven fields")
    kpis = phases["phase_3"]["kpi_targets"]
    required_kpi = {"metric", "baseline", "assumption", "formula", "range", "sensitivity", "evidence_ids"}
    if not isinstance(kpis, list) or len(kpis) != 3:
        raise SCORER.ValidationError("phase_3 requires exactly three KPI targets")
    for kpi in kpis:
        if set(kpi) != required_kpi or not all(nonempty(value) for value in kpi.values()):
            raise SCORER.ValidationError("every KPI target needs baseline, assumption, formula, range, sensitivity, and evidence_ids")
        if any(key not in evidence_map for key in kpi["evidence_ids"]):
            raise SCORER.ValidationError("KPI target cites an unknown evidence ID")
        if any(evidence_map[key].get("candidate") != selected for key in kpi["evidence_ids"]):
            raise SCORER.ValidationError("winner KPI target cites another candidate's evidence")

    quotes = research.get("buyer_quotes", [])
    if not isinstance(quotes, list) or len(quotes) < 2:
        raise SCORER.ValidationError("buyer_quotes requires at least two winner buyer quotes")
    attributed_words: dict[str, int] = {}
    for quote in quotes:
        if quote.get("phase") not in PHASE_FIELDS:
            raise SCORER.ValidationError("every buyer quote must be tagged to phase_1, phase_2, phase_3, or phase_4")
        item = evidence_map.get(quote.get("evidence_id"))
        if not item or item.get("evidence_type") != "VOICE" or quote.get("quote") != item.get("quote"):
            raise SCORER.ValidationError("buyer quote must exactly match a VOICE evidence item")
        if item.get("candidate") != selected:
            raise SCORER.ValidationError("buyer quote must belong to the selected winner")
        source_key = item.get("source_url") or item["evidence_id"]
        attributed_words[source_key] = attributed_words.get(source_key, 0) + len(quote["quote"].split())
        if attributed_words[source_key] > 25:
            raise SCORER.ValidationError("buyer quotes exceed 25 cumulative words from one source")

    signals = research.get("account_signals", [])
    required_signal = {"company", "signal", "signal_date", "source_url", "likely_buyer", "false_positive_reason"}
    if len(signals) > 5 or any(set(signal) != required_signal or not all(nonempty(v) for v in signal.values()) for signal in signals):
        raise SCORER.ValidationError("account_signals may contain up to five complete signal records")

    handoff = research.get("sales_handoff")
    if not isinstance(handoff, dict) or set(handoff) != HANDOFF_FIELDS or not all(nonempty(value) for value in handoff.values()):
        raise SCORER.ValidationError(f"sales_handoff must contain exactly {sorted(HANDOFF_FIELDS)}")
    for list_field in ("access_failures", "assumptions", "unresolved_unknowns"):
        if not isinstance(research.get(list_field), list):
            raise SCORER.ValidationError(f"{list_field} must be a list")
    return scored, evidence_map


def render_value(value: Any, indent: int = 0) -> list[str]:
    prefix = "  " * indent
    if isinstance(value, str):
        return [prefix + value]
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(prefix + "-")
                lines.extend(render_value(item, indent + 1))
            else:
                lines.append(prefix + f"- {item}")
        return lines
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            label = key.replace("_", " ").title()
            if isinstance(item, (dict, list)):
                lines.append(prefix + f"**{label}:**")
                lines.extend(render_value(item, indent + 1))
            else:
                lines.append(prefix + f"**{label}:** {item}")
        return lines
    return [prefix + str(value)]


def build_markdown(score_input: dict[str, Any], research: dict[str, Any]) -> str:
    scored, _ = validate_report(score_input, research)
    lines = SCORER.markdown(scored).rstrip().splitlines()
    lines.extend(["", "## Winner justification", ""])
    lines.extend(f"- {sentence}" for sentence in research["winner_justification"])
    lines.extend(["", "## Comparable candidate evidence", ""])
    for summary in research["candidate_summaries"]:
        lines.extend([
            f"### {summary['candidate']}",
            "",
            summary["summary"],
            "",
            f"Evidence: {', '.join(summary['evidence_ids'])}. Counterevidence: {', '.join(summary['counterevidence_ids'])}.",
            "",
        ])
    phase_titles = {
        "phase_1": "Phase 1: Ideal Customer Business",
        "phase_2": "Phase 2: Current State",
        "phase_3": "Phase 3: Dream State",
        "phase_4": "Phase 4: Roadblocks and MEDDICC",
    }
    for phase, title in phase_titles.items():
        lines.extend([f"## {title}", ""])
        lines.extend(render_value(research["winner_research"][phase]))
        lines.append("")
    lines.extend(["## Buyer quotes", ""])
    lines.extend(f"- [{quote['phase']}][{quote['evidence_id']}] \"{quote['quote']}\"" for quote in research["buyer_quotes"])
    lines.extend(["", "## Winner-only account signals", ""])
    lines.extend(render_value(research["account_signals"]))
    lines.extend(["", "## Search-ready sales handoff", "", "| Field | Definition |", "|---|---|"])
    for key, value in research["sales_handoff"].items():
        rendered = "; ".join(value) if isinstance(value, list) else str(value)
        lines.append(f"| {key.replace('_', ' ').title()} | {rendered.replace('|', chr(92) + '|')} |")
    lines.extend(["", "## Evidence ledger", "", "| ID | Candidate | Type | Claim | Source |", "|---|---|---|---|---|"])
    all_evidence = list(score_input["evidence"])
    if isinstance(research.get("override"), dict):
        all_evidence.extend(research["override"].get("new_evidence", []))
    for item in all_evidence:
        source = item.get("source_url", "calculation or inference")
        lines.append(f"| {item['evidence_id']} | {item['candidate']} | {item['evidence_type']} | {item['claim']} | {source} |")
    for title, key in (("Access failures", "access_failures"), ("Assumptions", "assumptions"), ("Unresolved unknowns", "unresolved_unknowns")):
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {item}" for item in research[key])
        if not research[key]:
            lines.append("- None recorded.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-input", required=True)
    parser.add_argument("--research-input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    score_input = json.loads(Path(args.score_input).read_text())
    research = json.loads(Path(args.research_input).read_text())
    try:
        output = build_markdown(score_input, research)
    except SCORER.ValidationError as exc:
        raise SystemExit(f"Invalid final report input: {exc}") from exc
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output)
    print(f"Final ICP report: {path}")


if __name__ == "__main__":
    main()

