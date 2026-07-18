#!/usr/bin/env bash
# Initialize (or verify) the QueueCTL database schema.
#
# Usage:
#   ./scripts/run_migrations.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

"$PYTHON" "$SCRIPT_DIR/init_db.py"
