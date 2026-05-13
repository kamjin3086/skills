#!/usr/bin/env bash
# setup_project.sh — Clone video-analyzer, set up venv, check ffmpeg.
# Works on Linux, macOS, and Windows (Git Bash / WSL).
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/kamjin3086/video-analyzer}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/video-analyzer}"
PYTHON_EXE="${PYTHON_EXE:-python3}"

# ── 1. Clone or update ────────────────────────────────────────────────────────
if [[ -d "${INSTALL_DIR}/.git" ]]; then
  echo "[1/4] Updating existing clone at ${INSTALL_DIR}"
  git -C "${INSTALL_DIR}" pull --ff-only
else
  echo "[1/4] Cloning ${REPO_URL} -> ${INSTALL_DIR}"
  git clone "${REPO_URL}" "${INSTALL_DIR}"
fi

# ── 2. Create Python venv ─────────────────────────────────────────────────────
VENV_DIR="${INSTALL_DIR}/venv"
if [[ ! -d "${VENV_DIR}" ]]; then
  echo "[2/4] Creating venv at ${VENV_DIR}"
  "${PYTHON_EXE}" -m venv "${VENV_DIR}"
fi

# Resolve python binary (cross-platform)
if [[ -x "${VENV_DIR}/bin/python" ]]; then
  PY="${VENV_DIR}/bin/python"
elif [[ -x "${VENV_DIR}/Scripts/python.exe" ]]; then
  PY="${VENV_DIR}/Scripts/python.exe"
else
  echo "ERROR: Could not find python inside venv at ${VENV_DIR}" >&2
  exit 1
fi
echo "   venv python: ${PY}"

# ── 3. Install dependencies ───────────────────────────────────────────────────
echo "[3/4] Installing dependencies"
"${PY}" -m pip install --upgrade pip -q
"${PY}" -m pip install -r "${INSTALL_DIR}/requirements.txt" -q

# ── 4. Check ffmpeg ───────────────────────────────────────────────────────────
echo "[4/4] Checking ffmpeg"
if command -v ffmpeg >/dev/null 2>&1; then
  echo "   ffmpeg OK: $(command -v ffmpeg)"
else
  echo ""
  echo "WARNING: ffmpeg not found. Install it for your platform:" >&2
  echo ""
  echo "  Ubuntu / Debian:"
  echo "    sudo apt-get update && sudo apt-get install -y ffmpeg"
  echo ""
  echo "  Fedora / RHEL / Rocky:"
  echo "    sudo dnf install -y ffmpeg   # enable RPM Fusion first if needed"
  echo ""
  echo "  Arch Linux:"
  echo "    sudo pacman -S ffmpeg"
  echo ""
  echo "  macOS (Homebrew):"
  echo "    brew install ffmpeg"
  echo ""
  echo "  Windows (Chocolatey):"
  echo "    choco install ffmpeg"
  echo "  Windows (Scoop):"
  echo "    scoop install ffmpeg"
  echo "  Windows (manual): download from https://github.com/BtbN/FFmpeg-Builds/releases"
  echo "    then set FFMPEG_PATH in .env to the ffmpeg binary path."
  echo ""
  echo "After installing, re-run this script or set FFMPEG_PATH in .env."
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "Done. Next steps:"
echo "  1. Copy and configure .env:"
echo "       cp ${INSTALL_DIR}/.env.example ${INSTALL_DIR}/.env  (or create manually)"
echo "       # Set VISION_API_BASE, VISION_MODEL"
echo "  2. Detect your LLM backend:"
echo "       pip install httpx"
echo "       python ${INSTALL_DIR}/scripts/detect_backend.py --json"
echo "  3. Run a test:"
echo "       ${PY} ${INSTALL_DIR}/cli.py describe /path/to/video.mp4"
