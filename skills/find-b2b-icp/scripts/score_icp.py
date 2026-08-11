#!/usr/bin/env python3
"""Validate and reproducibly score exactly three B2B ICP candidates."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

WEIGHTS = {
    "pain_severity": 0.20,
    "trigger_strength": 0.15,
    "ability_to_pay": 0.15,
    "reachability": 0.15,
    "solution_delivery_fit": 0.15,
    "time_to_revenue": 0.10,
    "deal_potential": 0.10,
}
CONFIDENCE_ORDER = {"low": 1, "medium": 2, "high": 3}
SOURCE_TYPES = {"FACT", "VOICE", "COUNTEREVIDENCE"}
DEFINITION_FIELDS = {"industry", "company_size", "geography", "operating_condition", "trigger", "affected_process"}
FRESHNESS_DAYS = {"trigger": 90, "company": 365, "market": 730}


class ValidationError(ValueError):
    pass


def validate_inference_graph(evidence_map: dict[str, dict[str, Any]]) -> None:
    visiting: set[str] = set()
    resolved: dict[str, bool] = {}

    def visit(evidence_id: str, candidate: str) -> bool:
        if evidence_id in resolved:
            return resolved[evidence_id]
        if evidence_id in visiting:
            raise ValidationError(f"circular inference chain detected at {evidence_id}")
        item = evidence_map[evidence_id]
        if item.get("candidate") != candidate:
            raise ValidationError(f"inference chain crosses candidates at {evidence_id}")
        if item.get("evidence_type") != "INFERENCE":
            resolved[evidence_id] = True
            return True
        visiting.add(evidence_id)
        supporting_ids = item.get("supporting_evidence_ids", [])
        if not supporting_ids:
            raise ValidationError(f"{evidence_id} inference has no supporting evidence")
        grounded = False
        for supporting_id in supporting_ids:
            if supporting_id not in evidence_map:
                raise ValidationError(f"{evidence_id} cites unknown supporting evidence {supporting_id}")
            grounded = visit(supporting_id, candidate) or grounded
        visiting.remove(evidence_id)
        if not grounded:
            raise ValidationError(f"{evidence_id} inference is not grounded in non-inference evidence")
        resolved[evidence_id] = True
        return True

    for evidence_id, item in evidence_map.items():
        if item.get("evidence_type") == "INFERENCE":
            visit(evidence_id, item.get("candidate"))


def confidence_for(candidate_name: str, evidence: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    items = [item for item in evidence if item.get("candidate") == candidate_name]
    source_items = [item for item in items if item.get("evidence_type") in SOURCE_TYPES]
    voices = [item for item in items if item.get("evidence_type") == "VOICE"]
    counter = [item for item in items if item.get("evidence_type") == "COUNTEREVIDENCE"]
    triggers = [
        item for item in items
        if item.get("freshness_class") == "trigger" and item.get("evidence_type") == "FACT"
    ]
    publishers = {str(item.get("source_name", "")).strip().casefold() for item in source_items}
    voice_publishers = {str(item.get("source_name", "")).strip().casefold() for item in voices}
    coverage = {
        "source_items": len(source_items),
        "independent_publishers": len(publishers),
        "buyer_voice_items": len(voices),
        "independent_buyer_voice_publishers": len(voice_publishers),
        "counterevidence_items": len(counter),
        "current_trigger_items": len(triggers),
    }
    if (
        len(source_items) >= 6
        and len(publishers) >= 5
        and len(voices) >= 2
        and len(voice_publishers) >= 2
        and counter
        and triggers
    ):
        return "high", coverage
    if len(source_items) >= 4 and len(publishers) >= 3 and voices and counter:
        return "medium", coverage
    return "low", coverage


def validate_evidence_item(item: dict[str, Any], research_date: date) -> None:
    required = {"evidence_id", "candidate", "evidence_type", "claim"}
    missing = sorted(required - item.keys())
    if missing:
        raise ValidationError(f"evidence item missing fields: {', '.join(missing)}")
    evidence_type = item["evidence_type"]
    if evidence_type not in {"FACT", "VOICE", "ESTIMATE", "INFERENCE", "COUNTEREVIDENCE"}:
        raise ValidationError(f"unsupported evidence_type: {evidence_type}")
    if evidence_type in SOURCE_TYPES:
        for field in ("source_name", "source_url", "accessed_at"):
            if not item.get(field):
                raise ValidationError(f"{item['evidence_id']} {evidence_type} missing {field}")
    freshness_class = item.get("freshness_class")
    if freshness_class not in {"trigger", "company", "market", "foundational", "not_applicable"}:
        raise ValidationError(f"{item['evidence_id']} has unsupported freshness_class {freshness_class}")
    if freshness_class in FRESHNESS_DAYS:
        try:
            published = date.fromisoformat(item["published_at"])
            accessed = date.fromisoformat(item["accessed_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError(f"{item['evidence_id']} needs ISO published_at and accessed_at dates") from exc
        if accessed > research_date or (research_date - accessed).days > 30:
            raise ValidationError(f"{item['evidence_id']} access date is not current for this research run")
        age = (research_date - published).days
        if age < 0 or age > FRESHNESS_DAYS[freshness_class]:
            raise ValidationError(
                f"{item['evidence_id']} is {age} days old, outside the {freshness_class} freshness window"
            )
    if evidence_type == "VOICE" and not all(item.get(field) for field in ("quote", "role_context")):
        raise ValidationError(f"{item['evidence_id']} VOICE missing quote or role_context")
    if evidence_type == "ESTIMATE" and not all(item.get(field) for field in ("formula", "assumptions", "sensitivity")):
        raise ValidationError(f"{item['evidence_id']} ESTIMATE missing formula, assumptions, or sensitivity")
    if evidence_type == "INFERENCE" and not all(item.get(field) for field in ("reasoning", "supporting_evidence_ids")):
        raise ValidationError(f"{item['evidence_id']} INFERENCE missing reasoning or supporting_evidence_ids")
    if evidence_type == "COUNTEREVIDENCE" and not item.get("implication"):
        raise ValidationError(f"{item['evidence_id']} COUNTEREVIDENCE missing implication")


def score_payload(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        research_date = date.fromisoformat(payload["research_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError("research_date must be an ISO date") from exc
    candidates = payload.get("candidates", [])
    if len(candidates) != 3:
        raise ValidationError(f"exactly three candidates are required; received {len(candidates)}")
    names = [candidate.get("name") for candidate in candidates]
    if any(not name for name in names) or len(names) != len(set(names)):
        raise ValidationError("candidate names must be present and unique")

    evidence = payload.get("evidence", [])
    for item in evidence:
        validate_evidence_item(item, research_date)
    evidence_ids = [item["evidence_id"] for item in evidence]
    duplicates = [key for key, count in Counter(evidence_ids).items() if count > 1]
    if duplicates:
        raise ValidationError(f"duplicate evidence IDs: {', '.join(duplicates)}")
    evidence_map = {item["evidence_id"]: item for item in evidence}
    for item in evidence:
        if item["evidence_type"] == "INFERENCE":
            for supporting_id in item["supporting_evidence_ids"]:
                supporting = evidence_map.get(supporting_id)
                if not supporting:
                    raise ValidationError(f"{item['evidence_id']} cites unknown supporting evidence {supporting_id}")
                if supporting.get("candidate") != item.get("candidate"):
                    raise ValidationError(f"{item['evidence_id']} cites supporting evidence from another candidate")
    validate_inference_graph(evidence_map)

    rows = []
    for candidate in candidates:
        name = candidate["name"]
        definition = candidate.get("definition")
        if not isinstance(definition, dict) or set(definition) != DEFINITION_FIELDS:
            raise ValidationError(f"{name} definition must contain exactly {sorted(DEFINITION_FIELDS)}")
        if any(not isinstance(value, str) or not value.strip() for value in definition.values()):
            raise ValidationError(f"{name} definition fields must be non-empty strings")
        active_disqualifiers = candidate.get("active_disqualifiers", [])
        if not isinstance(active_disqualifiers, list) or any(
            not isinstance(value, str) or not value.strip() for value in active_disqualifiers
        ):
            raise ValidationError(f"{name} active_disqualifiers must be a list of non-empty strings")
        scores = candidate.get("scores", {})
        if set(scores) != set(WEIGHTS):
            missing = sorted(set(WEIGHTS) - set(scores))
            extra = sorted(set(scores) - set(WEIGHTS))
            raise ValidationError(f"{name} scoring keys mismatch; missing={missing}, extra={extra}")
        weighted = 0.0
        score_details = {}
        for criterion, weight in WEIGHTS.items():
            detail = scores[criterion]
            if not isinstance(detail.get("reason"), str) or not detail["reason"].strip():
                raise ValidationError(f"{name} {criterion} requires a non-empty reason")
            value = detail.get("score")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not 1 <= value <= 10:
                raise ValidationError(f"{name} {criterion} score must be between 1 and 10")
            cited = detail.get("evidence_ids", [])
            if not cited:
                raise ValidationError(f"{name} {criterion} requires evidence_ids")
            for evidence_id in cited:
                item = evidence_map.get(evidence_id)
                if not item:
                    raise ValidationError(f"{name} {criterion} cites unknown evidence ID {evidence_id}")
                if item.get("candidate") != name:
                    raise ValidationError(f"{name} {criterion} cites evidence assigned to {item.get('candidate')}")
            contribution = round(value * weight, 3)
            weighted += contribution
            score_details[criterion] = {
                **detail,
                "weight": weight,
                "weighted_contribution": contribution,
            }
        confidence, coverage = confidence_for(name, evidence)
        rows.append({
            "name": name,
            "definition": candidate.get("definition", ""),
            "eligible": not bool(active_disqualifiers),
            "active_disqualifiers": active_disqualifiers,
            "weighted_total": round(weighted, 3),
            "evidence_confidence": confidence,
            "evidence_coverage": coverage,
            "scores": score_details,
        })

    eligible = sorted(
        [row for row in rows if row["eligible"]],
        key=lambda row: (
            row["weighted_total"],
            CONFIDENCE_ORDER[row["evidence_confidence"]],
            row["scores"]["time_to_revenue"]["score"],
            row["scores"]["solution_delivery_fit"]["score"],
        ),
        reverse=True,
    )
    winner = eligible[0]["name"] if eligible else None
    tied = False
    if len(eligible) >= 2:
        top_total = eligible[0]["weighted_total"]
        contenders = [row for row in eligible if top_total - row["weighted_total"] <= 0.30]
        contenders.sort(
            key=lambda row: (
                CONFIDENCE_ORDER[row["evidence_confidence"]],
                row["scores"]["time_to_revenue"]["score"],
                row["scores"]["solution_delivery_fit"]["score"],
            ),
            reverse=True,
        )
        if len(contenders) >= 2:
            first_key = (
                CONFIDENCE_ORDER[contenders[0]["evidence_confidence"]],
                contenders[0]["scores"]["time_to_revenue"]["score"],
                contenders[0]["scores"]["solution_delivery_fit"]["score"],
            )
            second_key = (
                CONFIDENCE_ORDER[contenders[1]["evidence_confidence"]],
                contenders[1]["scores"]["time_to_revenue"]["score"],
                contenders[1]["scores"]["solution_delivery_fit"]["score"],
            )
            if first_key != second_key:
                winner = contenders[0]["name"]
            else:
                tied = True
                winner = None
    return {
        "schema_version": 1,
        "offer": payload.get("offer", ""),
        "research_date": payload["research_date"],
        "weights": WEIGHTS,
        "candidates": rows,
        "winner": winner,
        "unresolved_tie": tied,
    }


def markdown(result: dict[str, Any]) -> str:
    names = [row["name"] for row in result["candidates"]]
    lines = [
        f"**Top 3 ICPs:** {' · '.join(names)}",
        "",
        "| Candidate | Pain | Trigger | Ability to pay | Reachability | Delivery fit | Time to revenue | Deal potential | Weighted total | Confidence | Eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in sorted(result["candidates"], key=lambda item: item["weighted_total"], reverse=True):
        score = row["scores"]
        lines.append(
            "| " + " | ".join([
                row["name"],
                str(score["pain_severity"]["score"]),
                str(score["trigger_strength"]["score"]),
                str(score["ability_to_pay"]["score"]),
                str(score["reachability"]["score"]),
                str(score["solution_delivery_fit"]["score"]),
                str(score["time_to_revenue"]["score"]),
                str(score["deal_potential"]["score"]),
                f"{row['weighted_total']:.2f}",
                row["evidence_confidence"],
                "yes" if row["eligible"] else "no",
            ]) + " |"
        )
    lines.extend(["", f"**Mechanical winner:** {result['winner'] or 'No winner'}"])
    if result["unresolved_tie"]:
        lines.append("Two candidates remain tied after the documented tie-break. Run a falsification test.")
    for row in result["candidates"]:
        if row["active_disqualifiers"]:
            lines.append(f"- {row['name']} disqualified: {'; '.join(row['active_disqualifiers'])}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--markdown-output", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text())
    try:
        result = score_payload(payload)
    except ValidationError as exc:
        raise SystemExit(f"Invalid score input: {exc}") from exc
    json_path = Path(args.json_output)
    markdown_path = Path(args.markdown_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2))
    markdown_path.write_text(markdown(result))
    print(f"Scored JSON: {json_path}")
    print(f"Scored Markdown: {markdown_path}")
    print(f"Winner: {result['winner'] or 'unresolved'}")


if __name__ == "__main__":
    main()

