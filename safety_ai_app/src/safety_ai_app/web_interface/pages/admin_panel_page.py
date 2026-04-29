"""
Painel de Administração — SafetyAI

ATENÇÃO: Este arquivo é mantido apenas para compatibilidade retroativa.
A implementação foi modularizada em:
    web_interface/pages/admin/
        ├── __init__.py         (orquestrador das tabs)
        ├── _helpers.py         (helpers e paths compartilhados)
        ├── _tab_overview.py    (TAB 1 — Visão Geral)
        ├── _tab_logs.py        (TAB 2 — Logs do Sistema)
        ├── _tab_plans.py       (TAB 3 — Planos & Preços)
        ├── _tab_advanced_config.py  (TAB 4 — Configurações Avançadas)
        └── _tab_ai_pipeline.py (TAB 5 — Pipeline de IA)
"""

from safety_ai_app.web_interface.pages.admin import render_page  # noqa: F401

__all__ = ["render_page"]
