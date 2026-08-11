import copy
import importlib.util
import json
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("score_icp", SKILL_DIR / "scripts" / "score_icp.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class IcpScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((SKILL_DIR / "eval" / "fixtures" / "score_input.json").read_text())

    def test_requires_exactly_three_candidates(self):
        payload = copy.deepcopy(self.fixture)
        payload["candidates"].pop()
        with self.assertRaises(MODULE.ValidationError):
            MODULE.score_payload(payload)

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(MODULE.WEIGHTS.values()), 1.0)

    def test_weighted_winner_is_reproducible(self):
        result = MODULE.score_payload(self.fixture)
        self.assertEqual(result["winner"], "US e-commerce brands with 20-100 staff and rising support volume")
        winner = next(row for row in result["candidates"] if row["name"] == result["winner"])
        self.assertAlmostEqual(winner["weighted_total"], 8.05)

    def test_active_disqualifier_blocks_winner(self):
        payload = copy.deepcopy(self.fixture)
        payload["candidates"][0]["active_disqualifiers"] = ["required data residency cannot be met"]
        result = MODULE.score_payload(payload)
        self.assertNotEqual(result["winner"], payload["candidates"][0]["name"])

    def test_unknown_evidence_id_fails(self):
        payload = copy.deepcopy(self.fixture)
        payload["candidates"][0]["scores"]["pain_severity"]["evidence_ids"] = ["MISSING"]
        with self.assertRaises(MODULE.ValidationError):
            MODULE.score_payload(payload)

    def test_stale_trigger_fails_freshness_validation(self):
        payload = copy.deepcopy(self.fixture)
        trigger = next(item for item in payload["evidence"] if item["evidence_id"] == "E003")
        trigger["published_at"] = "2020-01-01"
        with self.assertRaises(MODULE.ValidationError):
            MODULE.score_payload(payload)

    def test_old_access_date_does_not_make_old_trigger_current(self):
        payload = copy.deepcopy(self.fixture)
        trigger = next(item for item in payload["evidence"] if item["evidence_id"] == "E003")
        trigger["published_at"] = "2020-01-01"
        trigger["accessed_at"] = "2020-01-02"
        with self.assertRaises(MODULE.ValidationError):
            MODULE.score_payload(payload)

    def test_repeated_publisher_counts_as_one_independent_source(self):
        payload = copy.deepcopy(self.fixture)
        candidate = payload["candidates"][0]["name"]
        index = 0
        for item in payload["evidence"]:
            if item["candidate"] == candidate:
                index += 1
                item["source_url"] = f"https://source{index}.example.com/item"
                item["source_name"] = "One repeated publisher"
        result = MODULE.score_payload(payload)
        row = next(item for item in result["candidates"] if item["name"] == candidate)
        self.assertEqual(row["evidence_confidence"], "low")

    def test_distinct_publishers_on_multi_level_domains_remain_independent(self):
        payload = copy.deepcopy(self.fixture)
        candidate = payload["candidates"][0]["name"]
        index = 0
        for item in payload["evidence"]:
            if item["candidate"] == candidate:
                index += 1
                item["source_url"] = f"https://publisher{index}.co.in/item"
                item["source_name"] = f"Publisher {index}"
        result = MODULE.score_payload(payload)
        row = next(item for item in result["candidates"] if item["name"] == candidate)
        self.assertEqual(row["evidence_confidence"], "high")

    def test_inference_support_must_exist(self):
        payload = copy.deepcopy(self.fixture)
        payload["evidence"].append({
            "evidence_id": "E099",
            "candidate": payload["candidates"][0]["name"],
            "evidence_type": "INFERENCE",
            "claim": "Synthetic inference",
            "reasoning": "Derived from a missing record",
            "supporting_evidence_ids": ["MISSING"],
            "freshness_class": "not_applicable"
        })
        with self.assertRaises(MODULE.ValidationError):
            MODULE.score_payload(payload)

    def test_inference_cannot_support_itself(self):
        payload = copy.deepcopy(self.fixture)
        payload["evidence"].append({
            "evidence_id": "E099",
            "candidate": payload["candidates"][0]["name"],
            "evidence_type": "INFERENCE",
            "claim": "Circular inference",
            "reasoning": "It cites itself",
            "supporting_evidence_ids": ["E099"],
            "freshness_class": "not_applicable"
        })
        with self.assertRaises(MODULE.ValidationError):
            MODULE.score_payload(payload)

    def test_mutual_inference_cycle_is_rejected(self):
        payload = copy.deepcopy(self.fixture)
        candidate = payload["candidates"][0]["name"]
        payload["evidence"].extend([
            {"evidence_id": "E098", "candidate": candidate, "evidence_type": "INFERENCE", "claim": "Cycle A", "reasoning": "A cites B", "supporting_evidence_ids": ["E099"], "freshness_class": "not_applicable"},
            {"evidence_id": "E099", "candidate": candidate, "evidence_type": "INFERENCE", "claim": "Cycle B", "reasoning": "B cites A", "supporting_evidence_ids": ["E098"], "freshness_class": "not_applicable"}
        ])
        with self.assertRaises(MODULE.ValidationError):
            MODULE.score_payload(payload)

    def test_candidate_definition_requires_six_structured_fields(self):
        payload = copy.deepcopy(self.fixture)
        payload["candidates"][0]["definition"] = "broad e-commerce segment"
        with self.assertRaises(MODULE.ValidationError):
            MODULE.score_payload(payload)

    def test_unresolved_tie_is_not_given_false_precision(self):
        payload = copy.deepcopy(self.fixture)
        for candidate in payload["candidates"][:2]:
            for detail in candidate["scores"].values():
                detail["score"] = 7
        result = MODULE.score_payload(payload)
        self.assertTrue(result["unresolved_tie"])
        self.assertIsNone(result["winner"])


if __name__ == "__main__":
    unittest.main()

