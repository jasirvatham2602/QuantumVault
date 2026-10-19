"""Local browser-based QuantumVault teaching app.

Launch with:
    python3 -m streamlit run quantum_vault_streamlit.py

This is local-only by default: Streamlit serves the interface from the user's
computer and opens it in a browser tab.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from quantum_vault import (
    ProtocolConfig,
    bell_pair_circuit,
    bell_pair_demo,
    experiment_report_markdown,
    plot_protocol_dashboard,
    plot_qotp_state_comparison,
    qotp_demo,
    run_experiment,
)
from quantum_vault_ui import _plot_round_replay


st.set_page_config(
    page_title="QuantumVault — Quantum Security Lab",
    page_icon="🔐",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def simulate(rounds: int, eve_probability: float, noise_probability: float) -> dict[str, object]:
    """Run one honest/attacked comparison and cache identical settings."""
    honest_config = ProtocolConfig(
        rounds=rounds,
        eve_probability=0.0,
        noise_probability=noise_probability,
        seed=7,
    )
    attacked_config = ProtocolConfig(
        rounds=rounds,
        eve_probability=eve_probability,
        noise_probability=noise_probability,
        seed=7,
    )
    honest = run_experiment(honest_config)
    attacked = run_experiment(attacked_config)
    bell_counts = bell_pair_demo(shots=500)
    final_key = honest["final_key"]
    qotp = qotp_demo(final_key[:8]) if len(final_key) >= 8 else None
    return {
        "honest": honest,
        "honest_config": honest_config,
        "attacked": attacked,
        "attacked_config": attacked_config,
        "bell_counts": bell_counts,
        "qotp": qotp,
    }


def _show_metric(label: str, value: str, help_text: str | None = None) -> None:
    st.metric(label, value, help=help_text)


def main() -> None:
    st.title("🔐 QuantumVault")
    st.subheader("Interactive quantum security lab")
    st.write(
        "See how an E91-style entanglement protocol detects a disturbed channel "
        "before its shared key is used for Quantum One-Time Pad encryption."
    )

    with st.sidebar:
        st.header("Experiment controls")
        st.caption("Change the channel, then press **Run simulation**.")
        rounds = st.slider("Protocol rounds", 200, 1200, 400, step=100)
        eve_probability = st.slider("Eve interception probability", 0.0, 1.0, 0.75, step=0.05)
        noise_probability = st.slider("Channel noise", 0.0, 0.20, 0.0, step=0.01)
        run = st.button("▶ Run simulation", type="primary", use_container_width=True)
        st.divider()
        st.markdown(
            "**Teaching path**\n\n"
            "1. Compare honest and attacked channels.\n"
            "2. Replay individual protocol rounds.\n"
            "3. Watch QBER and CHSH expose Eve.\n"
            "4. See the accepted key encrypt a quantum state."
        )

    settings = (rounds, eve_probability, noise_probability)
    if run or "quantum_vault_results" not in st.session_state:
        with st.spinner("Running Bell-pair experiments…"):
            st.session_state["quantum_vault_results"] = simulate(*settings)
            st.session_state["quantum_vault_settings"] = settings

    results = st.session_state["quantum_vault_results"]
    honest = results["honest"]
    attacked = results["attacked"]

    previous_settings = st.session_state.get("quantum_vault_settings")
    if previous_settings != settings:
        st.info("The sliders changed. Press **Run simulation** to apply the new settings.")

    honest_status = "ACCEPTED" if honest["accepted"] else "REJECTED"
    attacked_status = "ACCEPTED" if attacked["accepted"] else "REJECTED"
    st.success(
        f"Honest channel: {honest_status}  •  Attacked channel: {attacked_status}"
        if honest["accepted"] and not attacked["accepted"]
        else "Review the security checks below."
    )

    metric_columns = st.columns(5)
    with metric_columns[0]:
        _show_metric("Honest QBER", f"{honest['qber']:.3f}", "Lower is better; the demo threshold is 0.15.")
    with metric_columns[1]:
        _show_metric("Attacked QBER", f"{attacked['qber']:.3f}", "A disturbed channel creates more mismatched key bits.")
    with metric_columns[2]:
        _show_metric("Honest CHSH", f"{honest['chsh']:.3f}", "A quantum result is above the classical limit of 2.")
    with metric_columns[3]:
        _show_metric("Attacked CHSH", f"{attacked['chsh']:.3f}", "Eve's local attack weakens the Bell correlation.")
    with metric_columns[4]:
        _show_metric("Final key", f"{honest['final_key_length']} bits", "The honest key is used for the QOTP demonstration.")

    overview, replay, encryption = st.tabs(
        ["📊 Security overview", "🔎 Round replay", "🔒 QOTP encryption"]
    )

    with overview:
        st.markdown(
            "The dashboard is the main story: Bell-pair correlations are created, "
            "rounds are tested, QBER and CHSH are calculated, and the key is accepted "
            "only when the checks pass."
        )
        figure, _ = plot_protocol_dashboard(
            honest,
            attacked,
            bell_counts=results["bell_counts"],
        )
        st.pyplot(figure, clear_figure=False, use_container_width=True)
        plt.close(figure)

        with st.expander("Explain the result in plain language"):
            st.markdown(
                f"- **QBER:** `{honest['qber']:.3f}` honest versus `{attacked['qber']:.3f}` attacked. "
                "It counts disagreements in the key rounds.\n"
                f"- **CHSH:** `{honest['chsh']:.3f}` honest versus `{attacked['chsh']:.3f}` attacked. "
                "It tests whether the observed correlations remain stronger than a classical strategy.\n"
                f"- **Decision:** the honest key is `{'accepted' if honest['accepted'] else 'rejected'}`, "
                f"while the attacked key is `{'accepted' if attacked['accepted'] else 'rejected'}`."
            )

    with replay:
        channel = st.radio("Replay channel", ["Honest channel", "Attacked channel"], horizontal=True)
        replay_round = st.slider("Reveal protocol rounds", 1, rounds, min(100, rounds), step=1)
        selected = honest if channel == "Honest channel" else attacked
        figure, _ = _plot_round_replay(selected["rounds"], replay_round, channel)
        st.pyplot(figure, clear_figure=False, use_container_width=True)
        plt.close(figure)
        st.caption(
            "Blue vertical marks are key rounds. Gray points are CHSH test rounds. "
            "Red X marks show Alice/Bob mismatches."
        )

    with encryption:
        qotp = results["qotp"]
        if qotp is None:
            st.warning("The honest run did not produce enough key bits for QOTP. Lower noise and run again.")
        else:
            left, right = st.columns(2)
            with left:
                st.markdown("### Input state")
                st.code(str(qotp["original_circuit"].draw()), language="text")
            with right:
                st.markdown("### Encrypted state")
                st.code(str(qotp["encrypted_circuit"].draw()), language="text")
            st.write(f"QOTP key bits used: `{qotp['key_bits']}`")
            figure, _ = plot_qotp_state_comparison(qotp)
            st.pyplot(figure, clear_figure=False, use_container_width=True)
            plt.close(figure)
            st.info("Bob applies the reverse keyed operations and recovers the original state.")

    with st.expander("📄 Experiment report"):
        report_channel = st.radio(
            "Report for channel",
            ["Honest channel", "Attacked channel"],
            horizontal=True,
            key="report_channel_radio",
        )
        if report_channel == "Honest channel":
            report_text = experiment_report_markdown(honest, results["honest_config"])
        else:
            report_text = experiment_report_markdown(attacked, results["attacked_config"])
        st.markdown(report_text)
        st.download_button(
            label="⬇ Download report (.md)",
            data=report_text,
            file_name="quantum_vault_experiment_report.md",
            mime="text/markdown",
        )

    with st.expander("Show the Bell-pair circuit"):
        st.code(str(bell_pair_circuit("Z", "Z").draw()), language="text")
        st.caption("H creates superposition; CNOT creates entanglement; measurement reveals correlated outcomes.")


if __name__ == "__main__":
    main()
