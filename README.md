# QuantumVault

QuantumVault is an educational quantum-cybersecurity simulator built for the
Qollab × IonQ Global Quantum Hackathon. It demonstrates how an E91-style
entanglement-based key exchange can detect channel disturbance before the
resulting key is used for Quantum One-Time Pad (QOTP) encryption.

## The protocol

```text
Bell-pair generation
        ↓
E91-style key and CHSH test rounds
        ↓
Eve/noise attack simulation
        ↓
QBER and CHSH analysis
        ↓
Toy key reconciliation
        ↓
Toeplitz privacy amplification
        ↓
QOTP encryption and decryption
```

QuantumVault compares an honest channel with an attacked channel. Its dashboard
shows Bell-pair outcomes, key and CHSH round selection, Eve activity, running
QBER, running CHSH, surviving key material, and the final accept/reject result.
The QOTP visualization compares the original and encrypted quantum-state
amplitudes, including real and imaginary components.

## Repository contents

- `Quantum_Vault.ipynb` — complete notebook walkthrough and visual demo.
- `quantum_vault.py` — reusable simulator, protocol, QOTP, and plotting code.
- `requirements.txt` — Python dependencies.
- `LICENSE` — MIT license.

## Quick start

```bash
git clone https://github.com/jasirvatham2602/QuantumVault.git
cd QuantumVault
python3 -m venv .venv
source .venv/bin/activate       # macOS/Linux
python -m pip install -r requirements.txt
jupyter notebook Quantum_Vault.ipynb
```

You can also run the Python demonstration directly:

```bash
python quantum_vault.py
```

This prints the Bell-pair counts and protocol summaries, then opens the protocol
and QOTP visualizations.

## Reading the results

- **Bell-pair counts:** an honest `|Φ+⟩` pair should produce mostly `00` and
  `11` results.
- **QBER:** the fraction of key-round bits where Alice and Bob disagree.
- **CHSH score:** a Bell-correlation statistic. An ideal honest simulation is
  near `2√2`, while classical correlations cannot exceed `2`.
- **Final key:** generated only when the security checks and reconciliation
  succeed.
- **QOTP:** consumes two shared key bits per message qubit, applies keyed Pauli
  operations, and reverses them to recover the original state.

## Important scope note

This is a teaching and visualization prototype, not a production-secure QKD
implementation. The Eve model is a simplified local-correlation attack model,
the reconciliation procedure is intentionally compact, and the simulation does
not model a physical quantum channel. Real QKD would also require authenticated
classical communication, finite-key security proofs, device characterization,
side-channel analysis, and a carefully validated threat model.

The demo message is the four-qubit state `|1⟩|+⟩|0⟩|0⟩`. It is a quantum-state
demonstration rather than a direct encoding of ordinary text.

## Project disclosure

QuantumVault is an original educational prototype built with Qiskit and
AI-assisted development. It uses established E91, QBER, CHSH, privacy
amplification, and QOTP concepts; the project contribution is their integrated,
visual, hackathon-ready demonstration. All implementation claims should be
understood within the educational scope described above.

## License

Released under the MIT license. See `LICENSE`.
