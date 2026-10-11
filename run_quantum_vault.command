#!/bin/zsh

set -e
PROJECT_DIR="${0:A:h}"
cd "$PROJECT_DIR"
exec python3 -m streamlit run "$PROJECT_DIR/quantum_vault_streamlit.py"
