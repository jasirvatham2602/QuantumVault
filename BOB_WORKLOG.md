# BOB_WORKLOG.md — IBM Bob Hackathon Improvements

This file documents the analysis, bug fix, new feature, and tests added to
QuantumVault during the IBM Bob hackathon session on the `ibm-bob-hackathon`
branch.

---

## 1. Analysis: reproducibility bug in `sweep_eve_probability()`

**File:** `quantum_vault.py`, function `sweep_eve_probability()`

**Finding:**  
The original implementation varied the simulation seed by list position:

```python
seed=seed + index,   # BUG: seed changes with list position
```

This meant that running the sweep with `probabilities=(0.0, 0.25, 0.75)` gave
*different* per-scenario results than running each probability individually (or
in a different order), because each scenario was initialized from a different
RNG state. It was impossible to reproduce a single scenario without knowing its
exact index in the original call.

**Root cause:** The intent of the `seed` parameter is to make the entire sweep
deterministic. Adding the loop index breaks that intent: the 0.25 scenario in a
three-element list uses `seed + 1`, but as a one-element list it uses `seed + 0`.

---

## 2. Bug fix: use the same base seed for every scenario

**Change 1 — sweep loop:** Removed `index` from the loop variable and changed
`seed=seed + index` to `seed=seed`.

```python
# Before
for index, probability in enumerate(probabilities):
    config = ProtocolConfig(..., seed=seed + index)

# After
for probability in probabilities:
    config = ProtocolConfig(..., seed=seed)
```

Each scenario now uses the same base seed. Differences in their results come
exclusively from their different `eve_probability` values, which is the only
independent variable the sweep is designed to vary.

**Change 2 — sampler seed:** The `StatevectorSampler` inside
`_quantum_samples_by_setting()` was instantiated without a seed, meaning it drew
from system entropy on every call and was the primary source of non-determinism.
The sampler's seed is now derived from the NumPy RNG (`rng.integers(0, 2**31)`)
so the entire simulation — including the Qiskit quantum sampling — is
reproducible from a single `seed` integer. `bell_pair_demo()` also accepts an
optional `seed` parameter for the same reason.

---

## 3. New feature: `experiment_report_markdown()`

**File:** `quantum_vault.py`, new function `experiment_report_markdown(result, config)`

A Markdown report generator that produces a human-readable summary of a single
protocol run. It includes:

- **Simulation settings** table (rounds, Eve probability, noise, thresholds, seed)
- **Security metrics** table (QBER, CHSH, reconciliation — each with a pass/fail icon)
- **Key material** table (raw key bits, final key bits after amplification)
- **Decision** (ACCEPTED / REJECTED)
- **Plain-language explanation** that adapts to the specific failure mode(s)

Secret key material (`final_key`, `alice_key`, `bob_key`) is intentionally
excluded from the report.

---

## 4. New feature: Streamlit report expander and download button

**File:** `quantum_vault_streamlit.py`

- The `simulate()` helper now stores `honest_config` and `attacked_config` in
  its return dict so the Streamlit page can pass them to `experiment_report_markdown`.
- An `📄 Experiment report` expander was added below the QOTP tab. It contains:
  - A radio button to choose Honest or Attacked channel.
  - A live Markdown preview of the report.
  - A **⬇ Download report (.md)** button that saves the report as
    `quantum_vault_experiment_report.md`.

---

## 5. Tests added

**File:** `test_quantum_vault.py`

| Test class | What it verifies |
|---|---|
| `TestSweepEveReproducibility.test_identical_results_on_repeated_calls` | Two sweep calls with the same arguments return bit-for-bit identical DataFrames. |
| `TestSweepEveReproducibility.test_results_independent_of_list_order` | Each probability's QBER/CHSH in the full sweep equals its value in a single-item sweep — confirming the seed is no longer position-dependent. |
| `TestExperimentReportMarkdown.test_report_contains_required_sections` | The report contains all five required sections. |
| `TestExperimentReportMarkdown.test_report_does_not_contain_key_bits` | Secret key bits do not appear in the report text. |
| `TestExperimentReportMarkdown.test_report_is_valid_markdown_string` | The report is a non-empty string starting with the expected heading. |

---

## 6. Files modified

| File | Change |
|---|---|
| `quantum_vault.py` | Bug fix in `sweep_eve_probability()`; new `experiment_report_markdown()` function |
| `quantum_vault_streamlit.py` | Import + use `experiment_report_markdown`; store configs; add report expander and download button |
| `test_quantum_vault.py` | New file — regression and unit tests |
| `BOB_WORKLOG.md` | New file — this document |
| `README.md` | Updated with IBM Bob hackathon section |
