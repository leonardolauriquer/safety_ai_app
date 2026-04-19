#!/usr/bin/env bash
# run_security_audit.sh
# Runs pip-audit against the locally installed packages and appends results
# to safety_ai_app/docs/security_audit.md.
# Usage: bash safety_ai_app/scripts/run_security_audit.sh
# Exit code is non-zero when vulnerabilities are found.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
AUDIT_LOG="$REPO_ROOT/safety_ai_app/docs/security_audit.md"
DATE="$(date '+%Y-%m-%d %H:%M:%S %Z')"

echo "=============================="
echo " SafetyAI Security Audit"
echo " $DATE"
echo "=============================="
echo ""

AUDIT_OUTPUT="$(pip-audit --local --format columns 2>&1)"
AUDIT_EXIT=$?

echo "$AUDIT_OUTPUT"
echo ""

if [ "$AUDIT_EXIT" -eq 0 ]; then
  STATUS_MSG="**Resultado:** Nenhuma vulnerabilidade conhecida encontrada."
else
  STATUS_MSG="**Resultado:** Vulnerabilidades encontradas — revisar e atualizar dependências afetadas."
fi

# Append a dated entry to the audit log
{
  echo ""
  echo "---"
  echo ""
  echo "## Auditoria Automática — $DATE"
  echo ""
  echo '```'
  echo "$AUDIT_OUTPUT"
  echo '```'
  echo ""
  echo "$STATUS_MSG"
} >> "$AUDIT_LOG"

echo "Resultado registrado em: $AUDIT_LOG"
exit "$AUDIT_EXIT"
