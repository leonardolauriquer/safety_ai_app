#!/bin/bash
set -e

echo "=== Post-merge setup: SafetyAI App ==="

cd safety_ai_app

echo "Instalando/atualizando dependências Python..."
pip install -e ".[dev]" --quiet 2>/dev/null || pip install -e . --quiet

echo "=== Post-merge setup concluído com sucesso ==="
