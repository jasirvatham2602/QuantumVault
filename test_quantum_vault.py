"""Regression tests for quantum_vault.py.

Run with:
    python -m pytest test_quantum_vault.py -v
"""

from __future__ import annotations

import math

import pytest

from quantum_vault import (
    ProtocolConfig,
    experiment_report_markdown,
    run_experiment,
    sweep_eve_probability,
)


# ---------------------------------------------------------------------------
# Reproducibility regression: sweep_eve_probability
# ---------------------------------------------------------------------------

class TestSweepEveReproducibility:
    """The sweep must return identical numbers when called twice with the same seed."""

    PROBABILITIES = (0.0, 0.25, 0.75)

    def _run(self) -> list[dict]:
        df = sweep_eve_probability(
            probabilities=self.PROBABILITIES,
            rounds=200,
            seed=42,
        )
        return df.to_dict(orient="records")

    def test_identical_results_on_repeated_calls(self) -> None:
        """Two identical sweep calls must produce bit-for-bit equal DataFrames."""
        first = self._run()
        second = self._run()
        assert first == second, (
            "sweep_eve_probability() returned different results on two calls with the same seed. "
            "This is the reproducibility bug: ensure seed=seed, not seed=seed+index."
        )

    def test_results_independent_of_list_order(self) -> None:
        """A single-entry sweep must equal the corresponding row in the full sweep."""
        full_df = sweep_eve_probability(
            probabilities=self.PROBABILITIES,
            rounds=200,
            seed=42,
        )
        for prob in self.PROBABILITIES:
            single_df = sweep_eve_probability(
                probabilities=(prob,),
                rounds=200,
                seed=42,
            )
            full_row = full_df[full_df["eve_probability"] == prob].iloc[0]
            single_row = single_df.iloc[0]
            assert full_row["qber"] == pytest.approx(single_row["qber"]), (
                f"QBER for eve_probability={prob} differs depending on list position. "
                "Fix: all scenarios must use the same seed, not seed + index."
            )
            assert full_row["chsh"] == pytest.approx(single_row["chsh"]), (
                f"CHSH for eve_probability={prob} differs depending on list position."
            )


# ---------------------------------------------------------------------------
# experiment_report_markdown
# ---------------------------------------------------------------------------

class TestExperimentReportMarkdown:
    """Basic checks on the Markdown report generator."""

    def _honest_result_and_config(self) -> tuple[dict, ProtocolConfig]:
        config = ProtocolConfig(rounds=300, eve_probability=0.0, seed=7)
        result = run_experiment(config)
        return result, config

    def test_report_contains_required_sections(self) -> None:
        result, config = self._honest_result_and_config()
        report = experiment_report_markdown(result, config)
        for section in (
            "Simulation settings",
            "Security metrics",
            "Key material",
            "Decision",
            "Explanation",
        ):
            assert section in report, f"Report missing section: {section}"

    def test_report_does_not_contain_key_bits(self) -> None:
        result, config = self._honest_result_and_config()
        report = experiment_report_markdown(result, config)
        # The final key is a list of ints; its repr would contain commas and brackets.
        # We check that neither the raw list nor the label "final_key" appears.
        assert "final_key" not in report.lower() or "final key (after" in report.lower(), (
            "The report must not expose the raw key bit list."
        )
        key_bits = result.get("final_key", [])
        if len(key_bits) >= 4:
            # A substring of the key bits joined without spaces should not appear.
            key_sample = "".join(str(b) for b in key_bits[:8])
            assert key_sample not in report, "Secret key bits found in the report."

    def test_report_is_valid_markdown_string(self) -> None:
        result, config = self._honest_result_and_config()
        report = experiment_report_markdown(result, config)
        assert isinstance(report, str)
        assert len(report) > 100
        assert report.startswith("# QuantumVault Experiment Report")
