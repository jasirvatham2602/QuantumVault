# Quantum Vault

Quantum Vault is an educational Jupyter/Python prototype of an entanglement-based
quantum-security pipeline:

```text
E91-style Bell pairs
→ Eve/noise model
→ QBER and CHSH checks
→ toy parity reconciliation
→ Toeplitz privacy amplification
→ Quantum One-Time Pad encryption
```

## Files

- `Quantum_Vault.ipynb` — the notebook walkthrough and demo.
- `quantum_vault.py` — reusable implementation behind the notebook.

The notebook's protocol dashboard visualizes Bell-pair outcomes, key/CHSH round
selection, Eve activity, running QBER, running CHSH, surviving key material, and
the final accept/reject decision.

## Run

Open `Quantum_Vault.ipynb` in Jupyter and run the cells from top to bottom.
The current environment needs Qiskit, NumPy, Pandas, and Matplotlib. The notebook
uses Qiskit's `StatevectorSampler` for local simulation.

## Important scope note

This is a teaching simulator, not a production QKD implementation. The Eve model
uses an educational local-correlation attack model and a configurable key-round
disturbance. Real QKD requires a physical channel, authenticated classical
communications, device characterization, finite-key security proofs, and careful
side-channel analysis.

The QOTP demonstration encrypts the four-qubit state
`|1>|+>|0>|0>` and verifies that Bob recovers it after reversing the keyed gates.
