#!/bin/sh
# Executable wrapper for the local Melodiva background-job contract.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "${MELODIVA_PYTHON:-${MIXMASTER_PYTHON:-python3}}" "$SCRIPT_DIR/ace_step_adapter.py" "$1" "$2"
