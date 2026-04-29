"""
TAB 3 — Planos & Preços
Painel de Administração SafetyAI

CRUD de planos: criar, editar, remover e pré-visualizar planos de assinatura.
"""

import logging
from typing import Dict, List

import streamlit as st

from safety_ai_app.web_interface.pages.admin._helpers import (
    _load_json,
    _save_json,
    _PLANS_PATH,
)

logger = logging.getLogger(__name__)

_FEATURE_LABELS: Dict[str, str] = {
    "chat_messages_per_day": "Msgs de chat por dia (-1 = ilimitado)",
    "knowledge_base_sync": "Sincronização da Base de Conhecimento",
    "document_generation": "Geração de Documentos (APR, ATA)",
    "job_board": "Quadro de Empregos",
    "games": "Jogos e Desafios",
    "quick_queries": "Consultas Rápidas (CBO, CID, CNAE, CA)",
    "dimensioning": "Dimensionamentos (CIPA, SESMT, Brigada)",
    "news_feed": "Feed de Notícias",
    "custom_branding": "Personalização Visual",
    "priority_support": "Suporte Prioritário",
}

_DEFAULT_PLANS = {
    "plans": [
        {
            "id": "free", "name": "Gratuito", "price_monthly": 0.0, "price_yearly": 0.0, "currency": "BRL",
            "description": "Acesso básico às NRs e consultas rápidas.",
            "features": {
                "chat_messages_per_day": 10, "knowledge_base_sync": False, "document_generation": False,
                "job_board": True, "games": True, "quick_queries": True, "dimensioning": True,
                "news_feed": True, "custom_branding": False, "priority_support": False,
            },
        },
        {
            "id": "pro", "name": "Profissional", "price_monthly": 29.90, "price_yearly": 299.00, "currency": "BRL",
            "description": "Acesso completo com geração de documentos e sincronização automática.",
            "features": {
                "chat_messages_per_day": -1, "knowledge_base_sync": True, "document_generation": True,
                "job_board": True, "games": True, "quick_queries": True, "dimensioning": True,
                "news_feed": True, "custom_branding": False, "priority_support": False,
            },
        },
        {
            "id": "enterprise", "name": "Enterprise", "price_monthly": 99.90, "price_yearly": 999.00, "currency": "BRL",
            "description": "Multi-utilizador, suporte prioritário e personalização completa.",
            "features": {
                "chat_messages_per_day": -1, "knowledge_base_sync": True, "document_generation": True,
                "job_board": True, "games": True, "quick_queries": True, "dimensioning": True,
                "news_feed": True, "custom_branding": True, "priority_support": True,
            },
        },
    ]
}


def _tab_plans() -> None:
    import pandas as pd  # noqa: F401 — mantido para consistência com o arquivo original

    plans_data = _load_json(_PLANS_PATH, None)
    if not plans_data or not plans_data.get("plans"):
        plans_data = _DEFAULT_PLANS
        _save_json(_PLANS_PATH, plans_data)
    plans: List[Dict] = plans_data.get("plans", [])

    if not plans:
        st.warning("Nenhum plano definido. Clique em 'Adicionar Novo Plano' para começar.")
        plans = list(_DEFAULT_PLANS["plans"])

    st.markdown('<div class="section-title">💳 Planos Actuais</div>', unsafe_allow_html=True)

    plan_names = [f"{p.get('name', p.get('id', '?'))} ({p.get('id', '?')})" for p in plans]
    sel_idx = st.selectbox("Seleccionar plano para editar", range(len(plan_names)),
                           format_func=lambda i: plan_names[i], key="admin_plan_select")

    plan = plans[sel_idx] if plans else {}

    col_edit, col_preview = st.columns([3, 2])

    with col_edit:
        st.markdown('<div class="section-title">✏️ Editar Plano</div>', unsafe_allow_html=True)

        new_id = st.text_input("ID (chave única)", value=plan.get("id", ""), key="plan_id")
        new_name = st.text_input("Nome", value=plan.get("name", ""), key="plan_name")
        new_desc = st.text_area("Descrição", value=plan.get("description", ""), key="plan_desc", height=80)
        new_currency = st.text_input("Moeda", value=plan.get("currency", "BRL"), key="plan_currency")

        pcol1, pcol2 = st.columns(2)
        with pcol1:
            new_price_m = st.number_input("Preço Mensal", min_value=0.0, step=0.01,
                                          value=float(plan.get("price_monthly", 0.0)), key="plan_price_m", format="%.2f")
        with pcol2:
            new_price_y = st.number_input("Preço Anual", min_value=0.0, step=0.01,
                                          value=float(plan.get("price_yearly", 0.0)), key="plan_price_y", format="%.2f")

        st.markdown('<div class="section-title" style="margin-top:12px;">🔧 Funcionalidades</div>', unsafe_allow_html=True)
        features = dict(plan.get("features", {}))
        new_features = {}
        for feat_key, feat_label in _FEATURE_LABELS.items():
            current_val = features.get(feat_key, False)
            if feat_key == "chat_messages_per_day":
                new_features[feat_key] = st.number_input(
                    feat_label, value=int(current_val) if isinstance(current_val, (int, float)) else 10,
                    min_value=-1, step=1, key=f"feat_{feat_key}_{sel_idx}",
                )
            else:
                new_features[feat_key] = st.checkbox(
                    feat_label, value=bool(current_val), key=f"feat_{feat_key}_{sel_idx}"
                )

        bcol1, bcol2, bcol3 = st.columns(3)
        with bcol1:
            if st.button("💾 Salvar Plano", key="plan_save", type="primary", use_container_width=True):
                updated_plan = {
                    "id": new_id, "name": new_name, "price_monthly": new_price_m,
                    "price_yearly": new_price_y, "currency": new_currency,
                    "description": new_desc, "features": new_features,
                }
                plans[sel_idx] = updated_plan
                plans_data["plans"] = plans
                if _save_json(_PLANS_PATH, plans_data):
                    st.success("✅ Plano salvo com sucesso!")
                else:
                    st.error("❌ Erro ao salvar. Verifique as permissões de ficheiro.")

        with bcol2:
            if st.button("➕ Novo Plano", key="plan_add", use_container_width=True):
                new_plan = {
                    "id": f"novo_{len(plans)+1}", "name": "Novo Plano",
                    "price_monthly": 0.0, "price_yearly": 0.0, "currency": "BRL",
                    "description": "Descrição do novo plano.",
                    "features": {k: False for k in _FEATURE_LABELS},
                }
                plans.append(new_plan)
                plans_data["plans"] = plans
                _save_json(_PLANS_PATH, plans_data)
                st.rerun()

        with bcol3:
            if st.button("🗑️ Remover Plano", key="plan_remove", use_container_width=True):
                if len(plans) > 1:
                    plans.pop(sel_idx)
                    plans_data["plans"] = plans
                    if _save_json(_PLANS_PATH, plans_data):
                        st.success("Plano removido.")
                        st.rerun()
                else:
                    st.warning("Não é possível remover o último plano.")

    with col_preview:
        st.markdown('<div class="section-title">👁️ Pré-visualização</div>', unsafe_allow_html=True)
        price_m = plan.get("price_monthly", 0)
        price_y = plan.get("price_yearly", 0)
        currency = plan.get("currency", "BRL")
        feats_preview = plan.get("features", {})
        feat_list = "".join([
            f'<li style="color:#{"4ADE80" if v else "475569"}; font-size:0.82em; padding:2px 0;">'
            f'{"✓" if v else "✗"} {lbl}</li>'
            for feat_key, lbl in _FEATURE_LABELS.items()
            if (v := feats_preview.get(feat_key, False)) is not None
        ])
        st.markdown(f"""
            <div class="result-card" style="padding:20px 18px;">
                <div style="color:#4ADE80; font-size:1.1em; font-weight:700; margin-bottom:4px;">{plan.get('name','–')}</div>
                <div style="color:#94A3B8; font-size:0.82em; margin-bottom:12px;">{plan.get('description','')}</div>
                <div style="color:#F8FAFC; font-size:1.4em; font-weight:800; margin-bottom:4px;">
                    {currency} {price_m:.2f}<span style="font-size:0.55em;color:#64748B;">/mês</span>
                </div>
                <div style="color:#64748B; font-size:0.78em; margin-bottom:14px;">
                    ou {currency} {price_y:.2f}/ano
                </div>
                <ul style="list-style:none; padding:0; margin:0;">
                    {feat_list}
                </ul>
            </div>
        """, unsafe_allow_html=True)
