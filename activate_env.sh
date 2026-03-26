#!/bin/zsh
# Activate Python virtual environment
source .venv/bin/activate
# Load environment variables from .env
export $(grep -v '^#' .env | xargs)
