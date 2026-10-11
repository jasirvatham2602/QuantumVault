"""Compatibility launcher for the local QuantumVault app.

Run this file if you prefer the older command name. The actual interface is
the browser-based Streamlit app in ``quantum_vault_streamlit.py``.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


if __name__ == "__main__":
    app_path = Path(__file__).with_name("quantum_vault_streamlit.py")
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "streamlit", "run", str(app_path)],
            cwd=str(app_path.parent),
        )
    )
