"""Qollab entry point for the QuantumVault demonstration.

Qollab's Python runner looks for a top-level ``main.py``. This file keeps the
published runner lightweight: it uses Qiskit for the honest Bell/E91 rounds and
plain Python for the intentionally simplified Eve comparison. The full local
Streamlit interface remains in ``quantum_vault_streamlit.py``.
"""

from __future__ import annotations

from math import pi
from random import Random

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler


ANGLES = {
    "Z": 0.0,
    "X": pi / 2,
    "B+": pi / 4,
    "B-": -pi / 4,
}


def e91_circuit(alice_setting: str, bob_setting: str) -> QuantumCircuit:
    """Create one measured Bell-pair circuit for an E91 analyzer pair."""
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.ry(-ANGLES[alice_setting], 0)
    circuit.ry(-ANGLES[bob_setting], 1)
    circuit.measure(0, 0)
    circuit.measure(1, 1)
    return circuit


def _counts_with_qollab_backend(circuit: QuantumCircuit, shots: int):
    """Use Qollab's injected backend when available."""
    qollab_backend = globals().get("backend")
    if qollab_backend is None:
        return None
    job = qollab_backend.run(circuit, shots=shots)
    return dict(job.result().get_counts(circuit))


def sample_counts(circuit: QuantumCircuit, shots: int) -> dict[str, int]:
    """Run on Qollab's backend, or use a local StatevectorSampler fallback."""
    backend_counts = _counts_with_qollab_backend(circuit, shots)
    if backend_counts is not None:
        return backend_counts

    sampler = StatevectorSampler()
    result = sampler.run([circuit], shots=shots).result()
    data = result[0].data
    for register_name in ("c", "meas"):
        register = getattr(data, register_name, None)
        if register is not None:
            return dict(register.get_counts())
    raise RuntimeError("Could not find measured counts in the Qiskit result.")


def correlation(counts: dict[str, int]) -> float:
    """Calculate E(a,b) = same outcomes minus different outcomes."""
    total = sum(counts.values())
    if total == 0:
        return float("nan")
    same = sum(value for bits, value in counts.items() if bits.replace(" ", "")[0] == bits.replace(" ", "")[-1])
    return (2 * same - total) / total


def honest_e91_demo(shots: int) -> tuple[dict[str, int], float, float]:
    """Return Bell counts, key-round QBER, and the honest CHSH score."""
    bell_counts = sample_counts(e91_circuit("Z", "Z"), shots)
    key_qber = 1.0 - correlation(bell_counts)

    correlations = {}
    for alice_setting, bob_setting in (
        ("Z", "B+"),
        ("Z", "B-"),
        ("X", "B+"),
        ("X", "B-"),
    ):
        counts = sample_counts(e91_circuit(alice_setting, bob_setting), shots)
        correlations[(alice_setting, bob_setting)] = correlation(counts)

    chsh = (
        correlations[("Z", "B+")]
        + correlations[("Z", "B-")]
        + correlations[("X", "B+")]
        - correlations[("X", "B-")]
    )
    return bell_counts, key_qber, chsh


def attacked_demo(rounds: int = 200, seed: int = 7) -> tuple[float, float]:
    """Toy local-correlation attack used to explain Eve detection."""
    rng = Random(seed)
    key_errors = 0
    key_rounds = 0
    chsh_correlations = {pair: [] for pair in (("Z", "B+"), ("Z", "B-"), ("X", "B+"), ("X", "B-"))}
    test_index = 0

    for round_id in range(rounds):
        if round_id % 2 == 0:
            alice_bit = rng.randrange(2)
            bob_bit = alice_bit
            if rng.random() < 0.25:
                bob_bit ^= 1
            key_errors += int(alice_bit != bob_bit)
            key_rounds += 1
        else:
            pair = list(chsh_correlations)[test_index % 4]
            test_index += 1
            # Eve's local shared bit cannot reproduce the quantum CHSH violation.
            alice_bit = rng.randrange(2)
            bob_bit = alice_bit
            chsh_correlations[pair].append(1 if alice_bit == bob_bit else -1)

    qber = key_errors / key_rounds
    values = {pair: sum(samples) / len(samples) for pair, samples in chsh_correlations.items()}
    chsh = values[("Z", "B+")] + values[("Z", "B-")] + values[("X", "B+")] - values[("X", "B-")]
    return qber, chsh


def main(
    shots: int = 100,
    excludeLowProbabilityValues: bool = True,
    lowProbabilityThreshold: float = 0.05,
) -> None:
    """Run the compact QuantumVault demo in Qollab's textual output panel."""
    del excludeLowProbabilityValues, lowProbabilityThreshold
    shots = max(20, int(shots))

    bell_counts, honest_qber, honest_chsh = honest_e91_demo(shots)
    attacked_qber, attacked_chsh = attacked_demo(rounds=max(200, shots * 2))

    print("QUANTUMVAULT — E91 QUANTUM SECURITY DEMO")
    print("=" * 45)
    print("Bell-pair measurement counts:", bell_counts)
    print()
    print("HONEST CHANNEL")
    print(f"QBER:  {honest_qber:.3f}")
    print(f"CHSH:  {honest_chsh:.3f}")
    print(f"Decision: {'ACCEPTED' if honest_qber <= 0.15 and honest_chsh > 2.0 else 'REJECTED'}")
    print()
    print("EVE-INTERCEPTED CHANNEL (teaching model)")
    print(f"QBER:  {attacked_qber:.3f}")
    print(f"CHSH:  {attacked_chsh:.3f}")
    print(f"Decision: {'ACCEPTED' if attacked_qber <= 0.15 and attacked_chsh > 2.0 else 'REJECTED'}")
    print()
    print("Interpretation: QBER measures key-bit mismatches; CHSH tests whether")
    print("the correlations remain beyond the classical limit of 2.")


if __name__ == "__main__":
    main()
