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

## Hackathon entry

QuantumVault is being submitted to the **Qollab × IonQ Global Quantum
Hackathon** in the **Quantum Unlocked** section. The project fits this theme by
turning a difficult quantum-networking and quantum-cryptography concept into an
interactive learning experience. Instead of treating the quantum circuit as a
black box, the project lets users see how entanglement is created, how channel
disturbance changes the measurements, and why the protocol rejects an unsafe
key.

The demonstration begins by generating Bell pairs for Alice and Bob. Some
rounds produce raw key bits, while other rounds are reserved for the CHSH Bell
test. The simulator can add channel noise or an Eve interception model, then
calculates QBER and CHSH to evaluate the channel. If the checks pass, the raw
key is reconciled and compressed with privacy amplification before selected key
bits drive the Quantum One-Time Pad. The QOTP section shows the original
quantum state, the keyed encrypted state, and the reverse operations used to
recover it.

The local interface is a Streamlit app that runs on the user's computer. The
sidebar provides controls for protocol rounds, Eve's interception probability,
and channel noise; pressing **Run simulation** refreshes the experiment. The
**Security overview** tab presents the full honest-versus-attacked dashboard,
the **Round replay** tab reveals protocol rounds one at a time, and the
**QOTP encryption** tab displays the input and encrypted circuits alongside
their state-vector amplitudes. This makes each security decision visible and
gives presenters a simple way to vary the attack and explain the result live.

For the Qollab Python/Qiskit runner, use the lightweight `main.py` entry point
with `quantum_vault.py`, `requirements.txt`, `LICENSE`, and this README. The
Streamlit interface is intended for local presentation; `main.py` provides the
compact textual Bell/E91 demonstration that Qollab can execute directly.

The interactive lab adds Learn, Experiment, and Challenge modes. It includes
Eve and noise controls, a round-by-round Play replay, live security metrics, and
guided views of the Bell pair, key processing, and QOTP stages.

## Repository contents

- `Quantum_Vault.ipynb` — complete notebook walkthrough and visual demo.
- `main.py` — lightweight Qollab Python/Qiskit entry point for the core demo.
- `quantum_vault.py` — reusable simulator, protocol, QOTP, and plotting code.
- `quantum_vault_ui.py` — interactive Jupyter lab built with ipywidgets.
- `quantum_vault_app.py` — compatibility launcher for the local app.
- `quantum_vault_streamlit.py` — recommended local browser-based interactive app.
- `run_quantum_vault.command` — macOS launcher for the desktop window.
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

Run the interactive lab in a notebook cell:

```python
from quantum_vault_ui import build_interactive_lab
display(build_interactive_lab())
```

You can also run the Python demonstration directly:

```bash
python quantum_vault.py
```

## Run as a local desktop window

The recommended local app is a browser-based window served only from your
computer. It avoids Jupyter and contains a security overview, round-by-round
replay, and QOTP encryption tab.

```bash
python3 -m pip install streamlit
python3 -m streamlit run quantum_vault_streamlit.py
```

On macOS, you can also double-click `run_quantum_vault.command` in Finder. If
macOS blocks it the first time, right-click the file, choose **Open**, and then
confirm. A browser tab will open at the local app address.

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
