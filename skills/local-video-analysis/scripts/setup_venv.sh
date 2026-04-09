#!/usr/bin/env bash
set -euo pipefail

PYTHON_EXE="${PYTHON_EXE:-python3}"
INSTALL_TRANSFORMERS="${INSTALL_TRANSFORMERS:-0}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${ROOT_DIR}/.venv"
REQ_BASE="${ROOT_DIR}/requirements.txt"
REQ_TF="${ROOT_DIR}/requirements-transformers.txt"

echo "[1/4] Creating venv at ${VENV_PATH}"
"${PYTHON_EXE}" -m venv "${VENV_PATH}"

PYTHON_BIN="${VENV_PATH}/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Failed to create venv python at ${PYTHON_BIN}" >&2
  exit 1
fi

echo "[2/4] Upgrading pip"
"${PYTHON_BIN}" -m pip install --upgrade pip

echo "[3/4] Installing Python dependencies"
"${PYTHON_BIN}" -m pip install -r "${REQ_BASE}"

if [[ "${INSTALL_TRANSFORMERS}" == "1" ]]; then
  echo "Installing Transformers extras (may take longer)"
  "${PYTHON_BIN}" -m pip install -r "${REQ_TF}"
fi

echo "[4/4] Verifying ffmpeg/ffprobe"
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "WARNING: ffmpeg/ffprobe not found in PATH." >&2
  echo "Install instructions:"
  echo "  Ubuntu/Debian: sudo apt-get update && sudo apt-get install -y ffmpeg"
  echo "  Fedora/RHEL:   sudo dnf install -y ffmpeg"
  echo "  Arch:          sudo pacman -S ffmpeg"
  echo "  macOS:         brew install ffmpeg"
else
  echo "ffmpeg OK: $(command -v ffmpeg)"
  echo "ffprobe OK: $(command -v ffprobe)"
fi

echo
echo "Done. Use the venv Python:"
echo "  ${PYTHON_BIN} scripts/run_video_pipeline.py <video.mp4> --sampling hybrid --max-side 768 --segment-seconds 120"
