#!/usr/bin/env bash
# Build the Linux binary of Test Solver AI v1.0.2 (onefile).
# Usage: ./build_linux.sh   -> output at dist/test_solver_v1.0.2
set -euo pipefail
cd "$(dirname "$0")"

python3 -m pip install --user -r requirements.txt
python3 -m PyInstaller test_solver_v1.0.2.spec --noconfirm --clean

echo
echo "✔ Binario generado en dist/test_solver_v1.0.2"
echo "  Ejecutar con privilegios para los hotkeys globales:"
echo "  sudo ./dist/test_solver_v1.0.2"
