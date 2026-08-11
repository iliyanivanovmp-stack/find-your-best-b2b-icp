import copy
import importlib.util
import json
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("build_report", SKILL_DIR / "scripts" / "build_report.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FinalReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures = SKILL_DIR / "eval" / "fixtures"
        cls.score_input = json.loads((fixtures / "score_input.json").read_text())
        cls.report_input = json.loads((fixtures / "report_input.json").read_text())

    def test_complete_report_starts_with_exactly_three_candidates(self):
        output = MODULE.build_markdown(self.score_input, self.report_input)
        first = output.splitlines()[0]
        self.assertTrue(first.startswith("**Top 3 ICPs:**"))
        self.assertEqual(first.count(" · "), 2)
        self.assertIn("## Search-ready sales handoff", output)
        self.assertIn("## Phase 4: Roadblocks and MEDDICC", output)

    def test_missing_handoff_fails(self):
        report = copy.deepcopy(self.report_input)
        report["sales_handoff"].pop("search_filters")
        with self.assertRaises(MODULE.SCORER.ValidationError):
            MODULE.build_markdown(self.score_input, report)

    def test_quote_must_match_voice_evidence(self):
        report = copy.deepcopy(self.report_input)
        report["buyer_quotes"][0]["quote"] = "Paraphrased buyer language"
        with self.assertRaises(MODULE.SCORER.ValidationError):
            MODULE.build_markdown(self.score_input, report)

    def test_quotes_are_required_and_phase_tagged(self):
        report = copy.deepcopy(self.report_input)
        report["buyer_quotes"] = []
        with self.assertRaises(MODULE.SCORER.ValidationError):
            MODULE.build_markdown(self.score_input, report)
        report = copy.deepcopy(self.report_input)
        report["buyer_quotes"][0].pop("phase")
        with self.assertRaises(MODULE.SCORER.ValidationError):
            MODULE.build_markdown(self.score_input, report)

    def test_candidate_summary_cannot_cross_cite(self):
        report = copy.deepcopy(self.report_input)
        report["candidate_summaries"][0]["evidence_ids"] = ["E007"]
        with self.assertRaises(MODULE.SCORER.ValidationError):
            MODULE.build_markdown(self.score_input, report)

    def test_override_requires_new_evidence_or_constraint(self):
        report = copy.deepcopy(self.report_input)
        report["selected_winner"] = self.score_input["candidates"][1]["name"]
        report["override"] = {
            "mechanical_winner": self.score_input["candidates"][0]["name"],
            "selected_winner": report["selected_winner"],
            "new_evidence": [],
            "business_constraint": "",
            "reason": ""
        }
        with self.assertRaises(MODULE.SCORER.ValidationError):
            MODULE.build_markdown(self.score_input, report)

    def test_winner_kpis_cannot_cite_other_candidate(self):
        report = copy.deepcopy(self.report_input)
        report["winner_research"]["phase_3"]["kpi_targets"][0]["evidence_ids"] = ["E007"]
        with self.assertRaises(MODULE.SCORER.ValidationError):
            MODULE.build_markdown(self.score_input, report)

    def test_quote_limit_is_cumulative_per_source(self):
        report = copy.deepcopy(self.report_input)
        report["buyer_quotes"] = [copy.deepcopy(report["buyer_quotes"][0]) for _ in range(6)]
        with self.assertRaises(MODULE.SCORER.ValidationError):
            MODULE.build_markdown(self.score_input, report)

    def test_override_inference_chain_must_exist(self):
        report = copy.deepcopy(self.report_input)
        report["selected_winner"] = self.score_input["candidates"][1]["name"]
        report["override"] = {
            "mechanical_winner": self.score_input["candidates"][0]["name"],
            "selected_winner": report["selected_winner"],
            "new_evidence": [{
                "evidence_id": "E100",
                "candidate": report["selected_winner"],
                "evidence_type": "INFERENCE",
                "claim": "Override inference",
                "reasoning": "A missing source allegedly changes the choice",
                "supporting_evidence_ids": ["MISSING"],
                "freshness_class": "not_applicable"
            }],
            "business_constraint": "",
            "reason": "New evidence changes the segment decision"
        }
        with self.assertRaises(MODULE.SCORER.ValidationError):
            MODULE.build_markdown(self.score_input, report)


if __name__ == "__main__":
    unittest.main()

