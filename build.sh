#!/usr/bin/env bash
# Build a single-file executable for the current platform (macOS / Linux).
set -euo pipefail
cd "$(dirname "$0")"

VENV_DIR=".venv"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment in $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Installing / updating PyInstaller in venv ..."
python -m pip install --upgrade pip pyinstaller

python -m PyInstaller \
  --onefile \
  --clean \
  --name atw622g-decrypt \
  --console \
  atw622g_decrypt.py

echo ""
if [[ -f dist/atw622g-decrypt ]]; then
  echo "Binary: dist/atw622g-decrypt"
  ls -lh dist/atw622g-decrypt
elif [[ -f dist/atw622g-decrypt.exe ]]; then
  echo "Binary: dist/atw622g-decrypt.exe"
  ls -lh dist/atw622g-decrypt.exe
fi
