"""Interactive Jupyter interface for the QuantumVault teaching simulator."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from quantum_vault import (
    ProtocolConfig,
    bell_pair_circuit,
    bell_pair_demo,
    plot_protocol_dashboard,
    plot_qotp_state_comparison,
    qotp_demo,
    run_experiment,
)


STAGES = [
    ("1. Create Bell Pair", "bell"),
    ("2. Measure", "measure"),
    ("3. Detect Eve", "detect"),
    ("4. Process Key", "key"),
    ("5. Encrypt with QOTP", "encrypt"),
]


STAGE_EXPLANATIONS = {
    "bell": (
        "### 1. Create a Bell pair\n"
        "The source creates an entangled pair and distributes one qubit to Alice "
        "and one to Bob. The circuit uses H followed by CNOT."
    ),
    "measure": (
        "### 2. Measure\n"
        "Alice and Bob independently choose measurement settings. Matching key "
        "settings produce raw key bits; other settings are kept for CHSH testing."
    ),
    "detect": (
        "### 3. Detect Eve\n"
        "QBER measures disagreement in key rounds. CHSH measures the strength of "
        "the quantum correlations. A disturbed channel should not be trusted."
    ),
    "key": (
        "### 4. Process the key\n"
        "Reconciliation corrects small differences. Privacy amplification compresses "
        "the key so possible information leaked during reconciliation is reduced."
    ),
    "encrypt": (
        "### 5. Encrypt with QOTP\n"
        "The accepted key supplies two bits per message qubit. Those bits select "
        "Pauli operations that hide the original state until Bob reverses them."
    ),
}


def _plot_round_replay(
    rounds: pd.DataFrame,
    upto: int,
    title: str,
) -> tuple[plt.Figure, np.ndarray]:
    """Plot a replayable prefix of protocol rounds."""
    shown = rounds.iloc[:upto]
    figure, axes = plt.subplots(1, 2, figsize=(12, 4))
    figure.suptitle(f"{title} — round {len(shown)} of {len(rounds)}", fontsize=14)

    labels = ["00", "01", "10", "11"]
    observed = [
        int(((shown["alice_bit"].astype(str) + shown["bob_bit"].astype(str)) == label).sum())
        for label in labels
    ]
    bars = axes[0].bar(labels, observed, color=["#4472C4", "#C00000", "#C00000", "#70AD47"])
    axes[0].bar_label(bars, padding=3)
    axes[0].set_title("Observed Alice/Bob results")
    axes[0].set_xlabel("Two-bit outcome")
    axes[0].set_ylabel("Count")

    key_mask = shown["round_type"].eq("key")
    chsh_mask = ~key_mask
    axes[1].scatter(
        shown.loc[key_mask, "round_id"],
        np.ones(key_mask.sum()),
        marker="|",
        s=100,
        color="#4472C4",
        label="Key round",
    )
    axes[1].scatter(
        shown.loc[chsh_mask, "round_id"],
        np.zeros(chsh_mask.sum()),
        marker=".",
        s=35,
        color="#A5A5A5",
        label="CHSH round",
    )
    mismatch_mask = shown["mismatch"].astype(bool)
    if mismatch_mask.any():
        axes[1].scatter(
            shown.loc[mismatch_mask, "round_id"],
            np.full(mismatch_mask.sum(), 0.5),
            marker="x",
            s=50,
            color="#C00000",
            label="Mismatch",
        )
    axes[1].set_title("Protocol-round replay")
    axes[1].set_xlabel("Round")
    axes[1].set_yticks([0, 1], ["CHSH", "Key"])
    axes[1].legend(fontsize=8)
    figure.tight_layout(rect=(0, 0, 1, 0.93))
    return figure, axes


def _plot_bell_counts(counts: dict[str, int]) -> tuple[plt.Figure, plt.Axes]:
    labels = ["00", "01", "10", "11"]
    values = [counts.get(label, 0) for label in labels]
    figure, axis = plt.subplots(figsize=(7, 3.5))
    bars = axis.bar(labels, values, color=["#4472C4", "#C00000", "#C00000", "#70AD47"])
    axis.bar_label(bars, padding=3)
    axis.set_title("Bell-pair measurement outcomes")
    axis.set_xlabel("Alice/Bob result")
    axis.set_ylabel("Shots")
    figure.tight_layout()
    return figure, axis


def build_interactive_lab(
    default_rounds: int = 400,
    default_eve_probability: float = 0.75,
    default_noise_probability: float = 0.0,
    seed: int = 7,
):
    """Build and return the interactive QuantumVault Jupyter lab.

    The widget requires ``ipywidgets`` and is intended to be displayed in a
    notebook with ``display(build_interactive_lab())``.
    """
    try:
        import ipywidgets as widgets
        from IPython.display import Markdown, clear_output, display
    except ImportError as error:
        raise ImportError(
            "Install ipywidgets with `python -m pip install ipywidgets` "
            "before opening the interactive lab."
        ) from error

    state: dict[str, object] = {}

    mode = widgets.Dropdown(
        options=["Learn", "Experiment", "Challenge"],
        value="Learn",
        description="Mode:",
        layout=widgets.Layout(width="220px"),
    )
    stage = widgets.SelectionSlider(
        options=STAGES,
        value="bell",
        description="Stage:",
        continuous_update=False,
        layout=widgets.Layout(width="620px"),
    )
    channel = widgets.ToggleButtons(
        options=[("Honest channel", "honest"), ("Attacked channel", "attacked")],
        value="attacked",
        description="Replay:",
        button_style="",
    )
    rounds = widgets.IntSlider(
        value=default_rounds,
        min=200,
        max=1200,
        step=100,
        description="Rounds:",
        continuous_update=False,
        style={"description_width": "initial"},
    )
    eve_probability = widgets.FloatSlider(
        value=default_eve_probability,
        min=0.0,
        max=1.0,
        step=0.05,
        description="Eve probability:",
        readout_format=".2f",
        continuous_update=False,
        style={"description_width": "initial"},
    )
    noise_probability = widgets.FloatSlider(
        value=default_noise_probability,
        min=0.0,
        max=0.20,
        step=0.01,
        description="Noise probability:",
        readout_format=".2f",
        continuous_update=False,
        style={"description_width": "initial"},
    )
    round_slider = widgets.IntSlider(
        value=1,
        min=1,
        max=default_rounds,
        step=1,
        description="Replay round:",
        continuous_update=False,
        style={"description_width": "initial"},
        layout=widgets.Layout(width="430px"),
    )
    play = widgets.Play(
        value=1,
        min=1,
        max=default_rounds,
        step=1,
        interval=150,
        description="Play",
    )
    widgets.jslink((play, "value"), (round_slider, "value"))

    run_button = widgets.Button(description="Run simulation", button_style="primary", icon="play")
    reveal_button = widgets.Button(description="Reveal challenge result", button_style="warning")
    status = widgets.HTML()
    output = widgets.Output()

    def set_status(message: str, color: str = "#2f6f9f") -> None:
        status.value = f'<p style="color:{color};"><b>{message}</b></p>'

    def run_simulation(_=None) -> None:
        set_status("Running Bell-pair simulations…")
        honest_config = ProtocolConfig(
            rounds=int(rounds.value),
            eve_probability=0.0,
            noise_probability=float(noise_probability.value),
            seed=seed,
        )
        attacked_config = ProtocolConfig(
            rounds=int(rounds.value),
            eve_probability=float(eve_probability.value),
            noise_probability=float(noise_probability.value),
            seed=seed,
        )
        state["honest"] = run_experiment(honest_config)
        state["attacked"] = run_experiment(attacked_config)
        state["bell_counts"] = bell_pair_demo(shots=500)
        honest_key = state["honest"]["final_key"]
        state["qotp"] = qotp_demo(honest_key[:8]) if len(honest_key) >= 8 else None
        state["challenge_revealed"] = False
        round_slider.max = int(rounds.value)
        play.max = int(rounds.value)
        round_slider.value = min(round_slider.value, int(rounds.value))
        set_status("Simulation ready. Choose a stage or press Play to replay rounds.", "#26734d")
        render()

    def render(*_args) -> None:
        with output:
            clear_output(wait=True)
            if not state:
                display(Markdown("Click **Run simulation** to begin."))
                return

            selected_stage = stage.value
            selected_result = state[channel.value]
            display(Markdown(STAGE_EXPLANATIONS[selected_stage]))

            if mode.value == "Challenge" and not state.get("challenge_revealed", False):
                display(
                    Markdown(
                        "### Predict the result\n"
                        f"With Eve probability **{eve_probability.value:.2f}**, will the final key be accepted? "
                        "Make your prediction, then press **Reveal challenge result**."
                    )
                )
                return

            if selected_stage == "bell":
                print(bell_pair_circuit("Z", "Z").draw())
                figure, _ = _plot_bell_counts(state["bell_counts"])
                display(figure)
                plt.close(figure)
                display(Markdown("Matching `00` and `11` outcomes show the Bell pair's correlation."))
            elif selected_stage == "measure":
                figure, _ = _plot_round_replay(
                    selected_result["rounds"],
                    round_slider.value,
                    "Honest" if channel.value == "honest" else "Attacked",
                )
                display(figure)
                plt.close(figure)
                display(Markdown("Use **Play** to watch the protocol rounds appear one at a time."))
            elif selected_stage == "detect":
                figure, _ = plot_protocol_dashboard(
                    state["honest"],
                    state["attacked"],
                    bell_counts=state["bell_counts"],
                )
                display(figure)
                plt.close(figure)
            elif selected_stage == "key":
                result = selected_result
                display(
                    Markdown(
                        f"**{channel.value.title()} channel** — QBER `{result['qber']:.3f}`, "
                        f"CHSH `{result['chsh']:.3f}`, raw key `{result['raw_key_length']}` bits, "
                        f"final key `{result['final_key_length']}` bits, "
                        f"status: **{'ACCEPTED' if result['accepted'] else 'REJECTED'}**."
                    )
                )
                display(result["correlations"])
            elif selected_stage == "encrypt":
                qotp = state["qotp"]
                if qotp is None:
                    display(Markdown("The honest run did not produce enough key bits for the QOTP demo."))
                else:
                    print("Input circuit:")
                    print(qotp["original_circuit"].draw())
                    print("Encrypted circuit:")
                    print(qotp["encrypted_circuit"].draw())
                    figure, _ = plot_qotp_state_comparison(qotp)
                    display(figure)
                    plt.close(figure)
                    display(Markdown("Bob applies the reverse keyed operations and recovers the input state."))

    def reveal_challenge(_=None) -> None:
        state["challenge_revealed"] = True
        render()

    run_button.on_click(run_simulation)
    reveal_button.on_click(reveal_challenge)
    mode.observe(render, names="value")
    stage.observe(render, names="value")
    channel.observe(render, names="value")
    def replay_round_changed(_change) -> None:
        if stage.value == "measure":
            render()

    round_slider.observe(replay_round_changed, names="value")

    controls = widgets.VBox(
        [
            widgets.HBox([mode, stage]),
            widgets.HBox([rounds, eve_probability, noise_probability]),
            widgets.HBox([run_button, reveal_button]),
            widgets.HBox([channel, play, round_slider]),
            status,
            output,
        ]
    )
    reveal_button.layout.display = "none"

    def update_mode(change):
        reveal_button.layout.display = "inline-flex" if change["new"] == "Challenge" else "none"
        render()

    mode.observe(update_mode, names="value")
    run_simulation()
    return controls
