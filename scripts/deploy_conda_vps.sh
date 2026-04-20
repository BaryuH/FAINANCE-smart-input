#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/slacker-ai}"
CONDA_HOME="${CONDA_HOME:-$HOME/miniconda3}"
ENV_NAME="${ENV_NAME:-slacker-ai}"

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "PROJECT_DIR not found: $PROJECT_DIR"
  exit 1
fi

if [[ ! -x "$CONDA_HOME/bin/conda" ]]; then
  echo "Conda not found at $CONDA_HOME/bin/conda"
  exit 1
fi

cd "$PROJECT_DIR"

source "$CONDA_HOME/etc/profile.d/conda.sh"

if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  conda create -y -n "$ENV_NAME" python=3.11
fi

conda activate "$ENV_NAME"
python -m pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f ".env" ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Please edit .env before starting service."
fi

echo "Conda environment ready: $ENV_NAME"
echo "Install systemd file:"
echo "  sudo cp deploy/systemd/slacker-aicore.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable --now slacker-aicore"
