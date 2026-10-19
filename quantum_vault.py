"""Quantum Vault: an educational E91 + QOTP simulator.

This module is intentionally transparent rather than production-ready. It models
an entanglement-based key exchange, a simple intercept/resend-like local model for
Eve, channel noise, QBER, CHSH testing, toy parity reconciliation, universal-hash
privacy amplification, and Quantum One-Time Pad encryption.

The E91 quantum samples are generated with Qiskit's StatevectorSampler. The Eve
model is a deliberately simple educational attack model: attacked rounds use a
local hidden-variable correlation (which cannot violate CHSH), and attacked key
rounds receive an additional disturbance so QBER visibly rises. A laboratory-
grade intercept/resend model would require a physical channel and device model.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler
from qiskit.quantum_info import Statevector


SETTING_ANGLES = {
    "Z": 0.0,
    "X": pi / 2,
    "B+": pi / 4,
    "B-": -pi / 4,
}


@dataclass(frozen=True)
class ProtocolConfig:
    rounds: int = 1200
    key_fraction: float = 0.5
    eve_probability: float = 0.0
    noise_probability: float = 0.0
    qber_threshold: float = 0.15
    chsh_threshold: float = 2.0
    min_chsh_samples: int = 10
    block_size: int = 8
    seed: int = 7


def bell_pair_circuit(
    alice_setting: str = "Z",
    bob_setting: str = "Z",
    measure: bool = True,
) -> QuantumCircuit:
    """Build one Bell-pair circuit for the requested analyzer settings.

    The circuit uses |Phi+> = (|00> + |11>)/sqrt(2). A Ry(-theta) rotation
    followed by Z measurement measures the X-Z plane axis at angle theta.
    """
    if alice_setting not in SETTING_ANGLES:
        raise ValueError(f"Unknown Alice setting: {alice_setting}")
    if bob_setting not in SETTING_ANGLES:
        raise ValueError(f"Unknown Bob setting: {bob_setting}")

    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.ry(-SETTING_ANGLES[alice_setting], 0)
    circuit.ry(-SETTING_ANGLES[bob_setting], 1)

    if measure:
        circuit.measure(0, 0)
        circuit.measure(1, 1)

    return circuit


def bell_pair_demo(shots: int = 1100, seed: int | None = None) -> dict[str, int]:
    """Sample the basic Z/Z Bell-pair circuit."""
    circuit = bell_pair_circuit("Z", "Z")
    sampler = StatevectorSampler(seed=seed)
    result = sampler.run([circuit], shots=shots).result()
    counts = result[0].data.c.get_counts()
    return dict(counts)


def _parse_counts(counts: dict[str, int], rng: np.random.Generator) -> list[tuple[int, int]]:
    """Expand Qiskit count strings into (alice_bit, bob_bit) samples.

    Qiskit prints classical bit strings in high-to-low order, so c1 c0 is
    displayed as Bob Alice for the explicit measurement mapping used here.
    """
    samples: list[tuple[int, int]] = []
    for bitstring, count in counts.items():
        normalized = bitstring.replace(" ", "")
        if len(normalized) != 2:
            raise ValueError(f"Unexpected count key: {bitstring!r}")
        bob_bit = int(normalized[0])
        alice_bit = int(normalized[1])
        samples.extend([(alice_bit, bob_bit)] * int(count))
    rng.shuffle(samples)
    return samples


def _quantum_samples_by_setting(
    setting_pairs: Iterable[tuple[str, str]],
    rng: np.random.Generator,
) -> dict[tuple[str, str], list[tuple[int, int]]]:
    """Sample honest Bell-pair outcomes grouped by setting pair.

    The StatevectorSampler is seeded from the same NumPy RNG that drives the
    rest of the protocol so the entire simulation is reproducible from a single
    seed integer.
    """
    pairs = list(setting_pairs)
    if not pairs:
        return {}

    counts_by_pair: dict[tuple[str, str], int] = {}
    for pair in pairs:
        counts_by_pair[pair] = counts_by_pair.get(pair, 0) + 1

    circuits = [bell_pair_circuit(a, b) for a, b in counts_by_pair]
    sampler_seed = int(rng.integers(0, 2**31))
    sampler = StatevectorSampler(seed=sampler_seed)

    output: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for pair, circuit in zip(counts_by_pair, circuits):
        result = sampler.run([circuit], shots=counts_by_pair[pair]).result()
        pub_result = result[0]
        output[pair] = _parse_counts(pub_result.data.c.get_counts(), rng)
    return output


def _local_attack_sample(rng: np.random.Generator) -> tuple[int, int]:
    """Return a local-hidden-variable pair that cannot violate CHSH."""
    shared_bit = int(rng.integers(0, 2))
    return shared_bit, shared_bit


def _apply_noise(bit: int, probability: float, rng: np.random.Generator) -> int:
    if rng.random() < probability:
        return 1 - bit
    return bit


def make_round_plan(config: ProtocolConfig, rng: np.random.Generator) -> list[dict[str, object]]:
    """Create key and CHSH test rounds before quantum sampling."""
    chsh_pairs = [("Z", "B+"), ("Z", "B-"), ("X", "B+"), ("X", "B-")]
    plan: list[dict[str, object]] = []

    for round_id in range(config.rounds):
        if rng.random() < config.key_fraction:
            plan.append(
                {
                    "round_id": round_id,
                    "round_type": "key",
                    "alice_setting": "Z",
                    "bob_setting": "Z",
                }
            )
        else:
            alice_setting, bob_setting = chsh_pairs[int(rng.integers(0, len(chsh_pairs)))]
            plan.append(
                {
                    "round_id": round_id,
                    "round_type": "chsh",
                    "alice_setting": alice_setting,
                    "bob_setting": bob_setting,
                }
            )
    return plan


def run_protocol(config: ProtocolConfig | None = None) -> pd.DataFrame:
    """Run an E91-style simulation and return one row per round."""
    config = config or ProtocolConfig()
    if not 0 <= config.eve_probability <= 1:
        raise ValueError("eve_probability must be between 0 and 1")
    if not 0 <= config.noise_probability <= 1:
        raise ValueError("noise_probability must be between 0 and 1")

    rng = np.random.default_rng(config.seed)
    plan = make_round_plan(config, rng)
    for row in plan:
        row["eve_intercepted"] = bool(rng.random() < config.eve_probability)

    honest_pairs = [
        (str(row["alice_setting"]), str(row["bob_setting"]))
        for row in plan
        if not bool(row["eve_intercepted"])
    ]
    honest_samples = _quantum_samples_by_setting(honest_pairs, rng)
    sample_offsets = {pair: 0 for pair in honest_samples}

    records: list[dict[str, object]] = []
    for row in plan:
        pair = (str(row["alice_setting"]), str(row["bob_setting"]))
        attacked = bool(row["eve_intercepted"])

        if attacked:
            alice_bit, bob_bit = _local_attack_sample(rng)
            if row["round_type"] == "key" and rng.random() < 0.25:
                bob_bit = 1 - bob_bit
        else:
            offset = sample_offsets[pair]
            alice_bit, bob_bit = honest_samples[pair][offset]
            sample_offsets[pair] += 1

        bob_bit = _apply_noise(bob_bit, config.noise_probability, rng)

        records.append(
            {
                "round_id": int(row["round_id"]),
                "round_type": row["round_type"],
                "alice_setting": row["alice_setting"],
                "bob_setting": row["bob_setting"],
                "alice_bit": alice_bit,
                "bob_bit": bob_bit,
                "eve_intercepted": attacked,
                "mismatch": alice_bit != bob_bit,
            }
        )

    return pd.DataFrame.from_records(records)


def extract_raw_key(rounds: pd.DataFrame) -> tuple[list[int], list[int]]:
    key_rounds = rounds[rounds["round_type"] == "key"]
    alice_key = [int(value) for value in key_rounds["alice_bit"]]
    bob_key = [int(value) for value in key_rounds["bob_bit"]]
    return alice_key, bob_key


def calculate_qber(alice_key: Sequence[int], bob_key: Sequence[int]) -> float:
    if len(alice_key) != len(bob_key):
        raise ValueError("Keys must have equal length")
    if not alice_key:
        return float("nan")
    return sum(a != b for a, b in zip(alice_key, bob_key)) / len(alice_key)


def _correlation(group: pd.DataFrame) -> float:
    if group.empty:
        return float("nan")
    same = int((group["alice_bit"] == group["bob_bit"]).sum())
    different = len(group) - same
    return (same - different) / len(group)


def calculate_chsh(rounds: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    chsh_rounds = rounds[rounds["round_type"] == "chsh"]
    rows: list[dict[str, object]] = []
    for alice_setting in ("Z", "X"):
        for bob_setting in ("B+", "B-"):
            group = chsh_rounds[
                (chsh_rounds["alice_setting"] == alice_setting)
                & (chsh_rounds["bob_setting"] == bob_setting)
            ]
            rows.append(
                {
                    "alice_setting": alice_setting,
                    "bob_setting": bob_setting,
                    "samples": len(group),
                    "correlation": _correlation(group),
                }
            )

    correlations = pd.DataFrame(rows)
    values = {
        (row.alice_setting, row.bob_setting): row.correlation
        for row in correlations.itertuples()
    }
    if any(np.isnan(value) for value in values.values()):
        return float("nan"), correlations

    score = values[("Z", "B+")] + values[("Z", "B-")] \
        + values[("X", "B+")] - values[("X", "B-")]
    return float(score), correlations


def reconcile_keys(
    alice_key: Sequence[int],
    bob_key: Sequence[int],
    block_size: int = 8,
) -> tuple[list[int], list[int], int, bool]:
    """Toy parity reconciliation for low-error demonstrations.

    It locates one parity-detectable error per block and reports the number of
    parity bits disclosed. Production Cascade reconciliation is more involved.
    """
    alice = list(map(int, alice_key))
    bob = list(map(int, bob_key))
    leakage = 0
    corrected = 0

    for start in range(0, len(alice), block_size):
        end = min(start + block_size, len(alice))
        if end - start <= 1:
            continue

        alice_block = alice[start:end]
        bob_block = bob[start:end]
        leakage += 1
        if sum(alice_block) % 2 == sum(bob_block) % 2:
            continue

        left = start
        right = end
        while right - left > 1:
            midpoint = (left + right) // 2
            leakage += 1
            alice_left_parity = sum(alice[left:midpoint]) % 2
            bob_left_parity = sum(bob[left:midpoint]) % 2
            if alice_left_parity != bob_left_parity:
                right = midpoint
            else:
                left = midpoint

        bob[left] = alice[left]
        corrected += 1

    success = alice == bob
    return alice, bob, leakage, success


def toeplitz_privacy_amplification(
    key_bits: Sequence[int],
    output_length: int,
    seed: int = 17,
) -> tuple[list[int], np.ndarray]:
    """Compress key bits with a public random binary Toeplitz matrix."""
    key = np.asarray(list(map(int, key_bits)), dtype=np.int8)
    if output_length <= 0 or output_length > len(key):
        raise ValueError("output_length must be between 1 and input length")

    rng = np.random.default_rng(seed)
    toeplitz_seed = rng.integers(0, 2, size=len(key) + output_length - 1, dtype=np.int8)
    matrix = np.empty((output_length, len(key)), dtype=np.int8)
    for row in range(output_length):
        matrix[row] = toeplitz_seed[row:row + len(key)]
    output = (matrix @ key) % 2
    return [int(bit) for bit in output], matrix


def prepare_demo_message() -> QuantumCircuit:
    """Prepare |1>|+>|0>|0> without measuring it."""
    circuit = QuantumCircuit(4)
    circuit.x(0)
    circuit.h(1)
    return circuit


def apply_qotp_encryption(circuit: QuantumCircuit, key_bits: Sequence[int]) -> QuantumCircuit:
    """Apply QOTP, with X first and Z second for each message qubit."""
    if len(key_bits) < 2 * circuit.num_qubits:
        raise ValueError("QOTP requires two key bits per message qubit")

    for qubit in range(circuit.num_qubits):
        kx = int(key_bits[2 * qubit])
        kz = int(key_bits[2 * qubit + 1])
        if kx:
            circuit.x(qubit)
        if kz:
            circuit.z(qubit)
    return circuit


def apply_qotp_decryption(circuit: QuantumCircuit, key_bits: Sequence[int]) -> QuantumCircuit:
    """Reverse QOTP: Z first, then X."""
    if len(key_bits) < 2 * circuit.num_qubits:
        raise ValueError("QOTP requires two key bits per message qubit")

    for qubit in range(circuit.num_qubits):
        kx = int(key_bits[2 * qubit])
        kz = int(key_bits[2 * qubit + 1])
        if kz:
            circuit.z(qubit)
        if kx:
            circuit.x(qubit)
    return circuit


def qotp_demo(key_bits: Sequence[int]) -> dict[str, object]:
    """Return original, encrypted, and decrypted circuits/statevectors."""
    needed = 8
    if len(key_bits) < needed:
        raise ValueError("The four-qubit demo needs at least eight key bits")
    used_key = list(map(int, key_bits[:needed]))

    original = prepare_demo_message()
    encrypted = original.copy()
    apply_qotp_encryption(encrypted, used_key)
    decrypted = encrypted.copy()
    apply_qotp_decryption(decrypted, used_key)

    return {
        "key_bits": used_key,
        "key_pairs": [used_key[i:i + 2] for i in range(0, needed, 2)],
        "original_circuit": original,
        "encrypted_circuit": encrypted,
        "decrypted_circuit": decrypted,
        "original_state": Statevector.from_instruction(original),
        "encrypted_state": Statevector.from_instruction(encrypted),
        "decrypted_state": Statevector.from_instruction(decrypted),
    }


def plot_qotp_state_comparison(
    qotp_result: dict[str, object],
) -> tuple[plt.Figure, np.ndarray]:
    """Plot the input and QOTP-encrypted statevector amplitudes.

    Real and imaginary amplitudes are shown separately. The x-axis uses
    Qiskit's computational-basis labels, so the plot makes both bit flips and
    phase changes visible instead of showing only measurement probabilities.
    """
    original = qotp_result["original_state"]
    encrypted = qotp_result["encrypted_state"]
    if not isinstance(original, Statevector) or not isinstance(encrypted, Statevector):
        raise TypeError("Expected the result returned by qotp_demo()")

    original_data = np.asarray(original.data)
    encrypted_data = np.asarray(encrypted.data)
    number_of_qubits = original.num_qubits
    basis_labels = [
        format(index, f"0{number_of_qubits}b")
        for index in range(len(original_data))
    ]
    x = np.arange(len(basis_labels))
    width = 0.36

    figure, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
    figure.suptitle(
        "Quantum One-Time Pad: input state versus encrypted state",
        fontsize=16,
    )

    for axis, amplitudes, title in (
        (axes[0], original_data, "Input state: |1⟩|+⟩|0⟩|0⟩"),
        (axes[1], encrypted_data, "Encrypted state: Pauli operations selected by the shared key"),
    ):
        axis.bar(
            x - width / 2,
            amplitudes.real,
            width,
            label="Real amplitude",
            color="#4472C4",
        )
        axis.bar(
            x + width / 2,
            amplitudes.imag,
            width,
            label="Imaginary amplitude",
            color="#ED7D31",
        )
        axis.axhline(0, color="#555555", linewidth=0.8)
        axis.set_ylabel("Amplitude")
        axis.set_title(title)
        axis.set_ylim(-0.85, 0.85)
        axis.legend(loc="upper right", fontsize=8)

    axes[1].set_xlabel("Computational-basis state (Qiskit display order)")
    axes[1].set_xticks(x, basis_labels)
    figure.tight_layout(rect=(0, 0, 1, 0.95))
    return figure, axes


def protocol_summary(
    rounds: pd.DataFrame,
    config: ProtocolConfig,
) -> dict[str, object]:
    alice_key, bob_key = extract_raw_key(rounds)
    qber = calculate_qber(alice_key, bob_key)
    chsh, correlations = calculate_chsh(rounds)
    alice_fixed, bob_fixed, leakage, reconciliation_ok = reconcile_keys(
        alice_key, bob_key, config.block_size
    )

    available_key_length = len(alice_fixed) - leakage - 2
    if reconciliation_ok and available_key_length >= 8:
        final_key_length = min(64, available_key_length)
        final_key, _ = toeplitz_privacy_amplification(
            alice_fixed,
            final_key_length,
            seed=config.seed + 101,
        )
    else:
        final_key = []

    qber_pass = bool(np.isfinite(qber) and qber <= config.qber_threshold)
    chsh_pass = bool(
        np.isfinite(chsh)
        and chsh > config.chsh_threshold
        and (correlations["samples"] >= config.min_chsh_samples).all()
    )
    accepted = qber_pass and chsh_pass and reconciliation_ok and len(final_key) >= 8

    return {
        "qber": qber,
        "chsh": chsh,
        "qber_pass": qber_pass,
        "chsh_pass": chsh_pass,
        "reconciliation_ok": reconciliation_ok,
        "parity_leakage": leakage,
        "raw_key_length": len(alice_key),
        "final_key_length": len(final_key),
        "final_key": final_key,
        "accepted": accepted,
        "correlations": correlations,
        "alice_key": alice_fixed,
        "bob_key": bob_fixed,
    }


def run_experiment(config: ProtocolConfig | None = None) -> dict[str, object]:
    config = config or ProtocolConfig()
    rounds = run_protocol(config)
    summary = protocol_summary(rounds, config)
    summary["rounds"] = rounds
    return summary


def sweep_eve_probability(
    probabilities: Sequence[float] = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0),
    rounds: int = 800,
    noise_probability: float = 0.0,
    seed: int = 7,
) -> pd.DataFrame:
    """Sweep over Eve interception probabilities and return a summary DataFrame.

    Every scenario uses the *same* base seed so that results are reproducible
    regardless of how many probabilities are in the list or their order.
    The previous behaviour (seed + index) made each run depend on list position,
    which broke reproducibility when the list was reordered or extended.
    """
    records: list[dict[str, object]] = []
    for probability in probabilities:
        config = ProtocolConfig(
            rounds=rounds,
            eve_probability=float(probability),
            noise_probability=noise_probability,
            seed=seed,
        )
        result = run_experiment(config)
        records.append(
            {
                "eve_probability": probability,
                "qber": result["qber"],
                "chsh": result["chsh"],
                "accepted": result["accepted"],
                "final_key_length": result["final_key_length"],
            }
        )
    return pd.DataFrame(records)


def plot_attack_sweep(results: pd.DataFrame) -> tuple[plt.Figure, np.ndarray]:
    figure, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(results["eve_probability"], results["qber"], marker="o")
    axes[0].axhline(0.15, color="red", linestyle="--", label="demo QBER threshold")
    axes[0].set_title("QBER vs Eve probability")
    axes[0].set_xlabel("Eve probability")
    axes[0].set_ylabel("QBER")
    axes[0].legend()

    axes[1].plot(results["eve_probability"], results["chsh"], marker="o")
    axes[1].axhline(2.0, color="red", linestyle="--", label="classical CHSH limit")
    axes[1].set_title("CHSH score vs Eve probability")
    axes[1].set_xlabel("Eve probability")
    axes[1].set_ylabel("CHSH score")
    axes[1].legend()

    figure.tight_layout()
    return figure, axes


def _running_qber(rounds: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return key-round number and cumulative QBER for plotting."""
    key_rounds = rounds[rounds["round_type"] == "key"]
    if key_rounds.empty:
        return np.array([]), np.array([])

    mismatches = key_rounds["mismatch"].astype(int).to_numpy()
    key_numbers = np.arange(1, len(mismatches) + 1)
    running_qber = np.cumsum(mismatches) / key_numbers
    return key_numbers, running_qber


def _running_chsh(rounds: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return round number and cumulative CHSH score once defined."""
    round_numbers = np.arange(1, len(rounds) + 1)
    scores = []
    for end in range(1, len(rounds) + 1):
        score, _ = calculate_chsh(rounds.iloc[:end])
        scores.append(score)
    return round_numbers, np.asarray(scores, dtype=float)


def plot_protocol_dashboard(
    honest_result: dict[str, object],
    attacked_result: dict[str, object],
    bell_counts: dict[str, int] | None = None,
) -> tuple[plt.Figure, np.ndarray]:
    """Plot the main E91 signals for honest and attacked experiments.

    The dashboard shows Bell-pair outcomes, the round plan and Eve activity,
    running QBER, running CHSH, raw/final key lengths, and the final decision.
    It is intended for notebook demonstrations and returns the Matplotlib
    figure and axes so the caller can further customize or save them.
    """
    honest_rounds = honest_result["rounds"]
    attacked_rounds = attacked_result["rounds"]
    if not isinstance(honest_rounds, pd.DataFrame) or not isinstance(
        attacked_rounds, pd.DataFrame
    ):
        raise TypeError("Results must come from run_experiment()")

    if bell_counts is None:
        bell_counts = bell_pair_demo(shots=1000)

    figure, axes = plt.subplots(2, 3, figsize=(16, 9))
    figure.suptitle("Quantum Vault: honest channel vs. Eve-intercepted channel", fontsize=16)

    # Bell-pair sanity check.
    bell_labels = ["00", "11", "01", "10"]
    bell_values = [bell_counts.get(label, 0) for label in bell_labels]
    bars = axes[0, 0].bar(
        bell_labels,
        bell_values,
        color=["#4472C4", "#70AD47", "#A5A5A5", "#A5A5A5"],
    )
    axes[0, 0].set_title("Bell-pair measurement outcomes")
    axes[0, 0].set_xlabel("Alice/Bob result")
    axes[0, 0].set_ylabel("Number of shots")
    axes[0, 0].bar_label(bars, padding=3)

    # Round plan and Eve activity.
    for row_index, (label, rounds, color) in enumerate(
        (("Honest", honest_rounds, "#4472C4"), ("Attacked", attacked_rounds, "#ED7D31"))
    ):
        key_mask = rounds["round_type"].eq("key")
        chsh_mask = ~key_mask
        axes[0, 1].scatter(
            rounds.loc[key_mask, "round_id"],
            np.full(key_mask.sum(), row_index),
            s=12,
            marker="|",
            color=color,
            label=f"{label} key rounds",
        )
        axes[0, 1].scatter(
            rounds.loc[chsh_mask, "round_id"],
            np.full(chsh_mask.sum(), row_index),
            s=12,
            marker=".",
            color="#A5A5A5",
            label=f"{label} CHSH rounds" if row_index == 0 else None,
        )
        eve_mask = rounds["eve_intercepted"].astype(bool)
        if eve_mask.any():
            axes[0, 1].scatter(
                rounds.loc[eve_mask, "round_id"],
                np.full(eve_mask.sum(), row_index),
                s=24,
                marker="x",
                color="#C00000",
                label="Eve-intercepted" if row_index == 1 else None,
            )
    axes[0, 1].set_title("What happened in each protocol round")
    axes[0, 1].set_xlabel("Round")
    axes[0, 1].set_yticks([0, 1], ["Honest", "Attacked"])
    axes[0, 1].legend(loc="upper right", fontsize=8)

    # Running QBER on the key rounds.
    for label, rounds, color in (
        ("Honest", honest_rounds, "#4472C4"),
        ("Attacked", attacked_rounds, "#ED7D31"),
    ):
        key_numbers, qber = _running_qber(rounds)
        axes[0, 2].plot(key_numbers, qber, color=color, label=label)
    axes[0, 2].axhline(0.15, color="#C00000", linestyle="--", label="QBER threshold")
    axes[0, 2].set_title("Running QBER")
    axes[0, 2].set_xlabel("Key rounds revealed so far")
    axes[0, 2].set_ylabel("Mismatch rate")
    axes[0, 2].set_ylim(0, 0.35)
    axes[0, 2].legend(fontsize=8)

    # Running CHSH score on the test rounds.
    for label, rounds, color in (
        ("Honest", honest_rounds, "#4472C4"),
        ("Attacked", attacked_rounds, "#ED7D31"),
    ):
        round_numbers, chsh_scores = _running_chsh(rounds)
        axes[1, 0].plot(round_numbers, chsh_scores, color=color, label=label)
    axes[1, 0].axhline(2.0, color="#C00000", linestyle="--", label="Classical limit")
    axes[1, 0].set_title("Running CHSH score")
    axes[1, 0].set_xlabel("Protocol round")
    axes[1, 0].set_ylabel("CHSH S")
    axes[1, 0].set_ylim(1.5, 3.0)
    axes[1, 0].legend(fontsize=8)

    # Key material surviving each stage.
    labels = ["Honest", "Attacked"]
    raw_lengths = [honest_result["raw_key_length"], attacked_result["raw_key_length"]]
    final_lengths = [honest_result["final_key_length"], attacked_result["final_key_length"]]
    x = np.arange(len(labels))
    width = 0.36
    raw_bars = axes[1, 1].bar(
        x - width / 2, raw_lengths, width, label="Raw key", color="#A5A5A5"
    )
    final_bars = axes[1, 1].bar(
        x + width / 2, final_lengths, width, label="Final key", color="#70AD47"
    )
    axes[1, 1].set_title("Key material after security checks")
    axes[1, 1].set_ylabel("Bits")
    axes[1, 1].set_xticks(x, labels)
    axes[1, 1].legend(fontsize=8)
    axes[1, 1].bar_label(raw_bars, padding=3)
    axes[1, 1].bar_label(final_bars, padding=3)

    # Final accept/reject decision.
    axes[1, 2].axis("off")
    for row_index, (label, result, color) in enumerate(
        (("HONEST", honest_result, "#70AD47"), ("ATTACKED", attacked_result, "#C00000"))
    ):
        status = "ACCEPTED" if result["accepted"] else "REJECTED"
        axes[1, 2].text(
            0.02,
            0.86 - row_index * 0.42,
            f"{label}: {status}",
            color=color,
            fontsize=14,
            fontweight="bold",
            transform=axes[1, 2].transAxes,
        )
        axes[1, 2].text(
            0.02,
            0.74 - row_index * 0.42,
            f"QBER {result['qber']:.3f}   |   CHSH {result['chsh']:.3f}\n"
            f"Raw key {result['raw_key_length']} bits   →   Final key {result['final_key_length']} bits",
            transform=axes[1, 2].transAxes,
            verticalalignment="top",
        )
    axes[1, 2].set_title("Protocol decision")

    figure.tight_layout(rect=(0, 0, 1, 0.96))
    return figure, axes


def experiment_report_markdown(
    result: dict[str, object],
    config: ProtocolConfig,
) -> str:
    """Return a Markdown experiment report for the given run.

    The report includes the simulation settings, key security metrics, key
    lengths, the accept/reject decision, and a plain-language explanation.
    Secret key material is intentionally excluded.
    """
    qber = float(result["qber"])  # type: ignore[arg-type]
    chsh = float(result["chsh"])  # type: ignore[arg-type]
    raw_len = int(result["raw_key_length"])  # type: ignore[arg-type]
    final_len = int(result["final_key_length"])  # type: ignore[arg-type]
    accepted = bool(result["accepted"])
    qber_pass = bool(result["qber_pass"])
    chsh_pass = bool(result["chsh_pass"])
    recon_ok = bool(result["reconciliation_ok"])

    status_icon = "✅ ACCEPTED" if accepted else "❌ REJECTED"

    qber_str = f"{qber:.4f}" if not (qber != qber) else "N/A"  # NaN guard
    chsh_str = f"{chsh:.4f}" if not (chsh != chsh) else "N/A"

    if accepted:
        explanation = (
            "The channel behaved as expected for an honest entangled source. "
            f"The quantum bit-error rate ({qber_str}) stayed below the {config.qber_threshold:.2f} threshold, "
            f"and the CHSH score ({chsh_str}) exceeded the classical limit of {config.chsh_threshold:.1f}, "
            "confirming that the measured correlations are stronger than any classical strategy could produce. "
            "Key reconciliation succeeded and a final key was produced after privacy amplification."
        )
    else:
        reasons = []
        if not qber_pass:
            reasons.append(
                f"the QBER ({qber_str}) exceeded the threshold of {config.qber_threshold:.2f}, "
                "indicating too many measurement mismatches"
            )
        if not chsh_pass:
            reasons.append(
                f"the CHSH score ({chsh_str}) did not exceed the classical limit of {config.chsh_threshold:.1f}, "
                "suggesting the correlations are too weak to confirm entanglement"
            )
        if not recon_ok:
            reasons.append("key reconciliation failed, leaving uncorrected errors in the shared key")
        if final_len < 8:
            reasons.append("too few key bits survived reconciliation and privacy amplification")
        joined = "; ".join(reasons) if reasons else "one or more security checks failed"
        explanation = (
            f"The key exchange was rejected because {joined}. "
            "This is the expected outcome when an eavesdropper or high channel noise "
            "disturbs the entangled pairs."
        )

    lines = [
        "# QuantumVault Experiment Report",
        "",
        "## Simulation settings",
        "",
        f"| Parameter | Value |",
        f"|---|---|",
        f"| Protocol rounds | {config.rounds} |",
        f"| Eve interception probability | {config.eve_probability:.2f} |",
        f"| Channel noise probability | {config.noise_probability:.2f} |",
        f"| QBER threshold | {config.qber_threshold:.2f} |",
        f"| CHSH threshold | {config.chsh_threshold:.1f} |",
        f"| Random seed | {config.seed} |",
        "",
        "## Security metrics",
        "",
        f"| Metric | Value | Pass? |",
        f"|---|---|---|",
        f"| QBER | {qber_str} | {'✅' if qber_pass else '❌'} |",
        f"| CHSH score | {chsh_str} | {'✅' if chsh_pass else '❌'} |",
        f"| Reconciliation | — | {'✅' if recon_ok else '❌'} |",
        "",
        "## Key material",
        "",
        f"| Stage | Bits |",
        f"|---|---|",
        f"| Raw key | {raw_len} |",
        f"| Final key (after amplification) | {final_len} |",
        "",
        "## Decision",
        "",
        f"**{status_icon}**",
        "",
        "## Explanation",
        "",
        explanation,
        "",
        "---",
        "*Generated by QuantumVault. Secret key material is not included in this report.*",
    ]
    return "\n".join(lines)


def print_result(result: dict[str, object]) -> None:
    print(f"QBER:             {result['qber']:.3f}")
    print(f"CHSH score:       {result['chsh']:.3f}")
    print(f"Raw key length:   {result['raw_key_length']}")
    print(f"Final key length: {result['final_key_length']}")
    print(f"Accepted:         {result['accepted']}")


if __name__ == "__main__":
    bell_counts = bell_pair_demo()
    print("Bell-pair counts:", bell_counts)
    honest = run_experiment(ProtocolConfig(eve_probability=0.0, noise_probability=0.01))
    attacked = run_experiment(ProtocolConfig(eve_probability=0.5, noise_probability=0.01))
    print("\nHonest run")
    print_result(honest)
    print("\nAttacked run")
    print_result(attacked)

    # Open the visual dashboard when this file is run directly.
    plot_protocol_dashboard(honest, attacked, bell_counts=bell_counts)
    qotp = qotp_demo(honest["final_key"][:8])
    print("\nInput statevector")
    print(qotp["original_state"])
    print("\nEncrypted statevector")
    print(qotp["encrypted_state"])
    plot_qotp_state_comparison(qotp)
    plt.show()
