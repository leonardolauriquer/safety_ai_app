import os
import logging

import pandas as pd
import streamlit as st

from safety_ai_app.fines_data_processor import FinesDataProcessor, format_currency_br
from safety_ai_app.google_drive_integrator import get_service_account_drive_integrator_instance
from safety_ai_app.theme_config import _get_material_icon_html
from safety_ai_app.web_interface.shared_styles import glass_marker, inject_glass_styles, render_back_button

logger = logging.getLogger(__name__)

_DRIVE_FILE_PATH = "SafetyAI - Conhecimento Base/Multas NR28/NR28_Multas.xlsx"


def fines_consult_page() -> None:
    inject_glass_styles()

    render_back_button("← Consultas Rápidas", "quick_queries_page", "back_from_fines")

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="page-header">
                {_get_material_icon_html("fines_consult")}
                <h1>Multas NR 28</h1>
            </div>
            <div class="page-subtitle">
                Calcule penalidades com base na NR 28, considerando número de funcionários
                e infrações identificadas.
            </div>
            """,
            unsafe_allow_html=True,
        )

        local_temp_dir = os.path.join(st.session_state.project_root, "downloads_temp")
        os.makedirs(local_temp_dir, exist_ok=True)

        if "fines_processor" not in st.session_state:
            st.session_state.fines_processor = None
            with st.spinner("Carregando dados de multas da NR 28..."):
                try:
                    integrator = get_service_account_drive_integrator_instance()
                    if integrator:
                        st.session_state.fines_processor = FinesDataProcessor(
                            integrator, _DRIVE_FILE_PATH, local_temp_dir
                        )
                    else:
                        st.markdown(
                            f"""
                            <div class="info-hint" style="background:rgba(239,68,68,0.08);
                                border-color:rgba(239,68,68,0.25);color:#F87171;">
                                {_get_material_icon_html("alert")}
                                <b>Erro:</b> Não foi possível conectar ao Google Drive.
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                except Exception as e:
                    err_msg = str(e)
                    logger.error(f"Erro ao inicializar FinesDataProcessor: {err_msg}", exc_info=True)
                    st.markdown(
                        f"""
                        <div class="info-hint" style="background:rgba(239,68,68,0.08);
                            border-color:rgba(239,68,68,0.25);color:#F87171;">
                            {_get_material_icon_html("alert")}
                            <b>Erro ao carregar dados de multas:</b> {err_msg}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        fines_processor: FinesDataProcessor = st.session_state.fines_processor
        if not fines_processor:
            return

        st.markdown(
            f"""
            <div class="section-title">
                {_get_material_icon_html("settings")}
                Parâmetros de Cálculo
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            employee_ranges = [
                "01 à 10", "11 à 25", "26 à 50", "51 à 100",
                "101 à 250", "251 à 500", "501 à 1000", "Mais de 1000",
            ]
            selected_employee_range = st.selectbox(
                "Número de Funcionários",
                options=employee_ranges,
                index=0,
            )
        with col2:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            has_recidivism = st.checkbox("Reincidência?", value=False)

        item_options: dict = {}
        selected_item_codes: list = []

        if fines_processor.df_itens is not None:
            for _, row in fines_processor.df_itens.iterrows():
                nr_display = int(row["nr"]) if pd.notna(row["nr"]) else "N/A"
                infr_display = int(row["infracao"]) if pd.notna(row["infracao"]) else "N/A"
                label = f"NR {nr_display} - {row['item_subitem']} (I: {infr_display}, {row['tipo']})"
                item_options[row["codigo"]] = label

            selected_item_codes = st.multiselect(
                "Itens Irregulares Identificados",
                options=list(item_options.keys()),
                format_func=lambda x: item_options[x],
                placeholder="Selecione as infrações identificadas...",
            )
        else:
            st.markdown(
                """
                <div class="info-hint">
                    <b>Aviso:</b> Dados de itens de infração não disponíveis.
                </div>
                """,
                unsafe_allow_html=True,
            )

        if st.button("⚖️ Calcular Multa Total", type="primary", use_container_width=True):
            if not selected_item_codes:
                st.markdown(
                    """
                    <div class="info-hint" style="background:rgba(245,158,11,0.1);
                        border-color:rgba(245,158,11,0.2);color:#F59E0B;">
                        <b>Atenção:</b> Selecione pelo menos um item irregular.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                return

            total_base, total_seg, total_med, details = fines_processor.calculate_total_fine(
                selected_employee_range, has_recidivism, selected_item_codes
            )

            st.markdown(
                f"""
                <div class="section-title" style="margin-top:16px;">
                    {_get_material_icon_html("sparkles")}
                    Resultado do Cálculo
                </div>
                """,
                unsafe_allow_html=True,
            )

            if total_base > 0:
                min_clt = (total_seg * 5) + (total_med * 3)
                max_clt = (total_seg * 50) + (total_med * 30)

                st.markdown(
                    f"""
                    <div class="result-card">
                        <div style="display:flex;justify-content:space-between;
                            align-items:flex-start;flex-wrap:wrap;gap:10px;">
                            <div>
                                <div class="result-title">Valor Base da Multa (NR 28)</div>
                                <div class="result-meta">
                                    Base: {"Reincidência" if has_recidivism else "Máximo regulamentar"} ·
                                    Segurança: <b>R$ {format_currency_br(total_seg)}</b> ·
                                    Medicina: <b>R$ {format_currency_br(total_med)}</b>
                                </div>
                            </div>
                            <div class="result-code" style="font-size:1.35em;white-space:nowrap;">
                                R$ {format_currency_br(total_base)}
                            </div>
                        </div>
                        <div class="result-detail" style="color:#FFD700;
                            border-top-color:rgba(255,215,0,0.15);margin-top:8px;padding-top:8px;">
                            ⚠️ <b>Estimativa CLT (Art. 201):</b>
                            De R$ {format_currency_br(min_clt)} até R$ {format_currency_br(max_clt)}
                            dependendo da gravidade e reincidência.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if details:
                    st.markdown(
                        f"""
                        <div class="section-title" style="margin-top:16px;">
                            {_get_material_icon_html("list")} Detalhamento das Infrações
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    for d in details:
                        item_cod = d.get("item_codigo", "")
                        item_desc = d.get("item_descricao", "")
                        tipo = d.get("tipo_infracao", "")
                        nivel = d.get("nivel_infracao", "")
                        valor = d.get("valor_multa", 0) or 0
                        base = d.get("base_calculo", "")

                        tipo_badge = (
                            f'<span style="color:#4ADE80;font-size:0.78em;font-weight:600;">{tipo}</span>'
                            if tipo else ""
                        )
                        nivel_badge = (
                            f'<span class="result-meta" style="margin-left:4px;">· I: {nivel}</span>'
                            if nivel else ""
                        )
                        st.markdown(
                            f"""
                            <div class="result-card" style="padding:10px 14px;margin-bottom:6px;">
                                <div style="display:flex;justify-content:space-between;
                                    align-items:flex-start;gap:8px;">
                                    <div>
                                        <span class="result-code">{item_cod}</span>
                                        {tipo_badge}{nivel_badge}
                                        <div class="result-title" style="margin-top:3px;font-size:0.85em;">
                                            {item_desc}
                                        </div>
                                        <div class="result-meta" style="margin-top:2px;">{base}</div>
                                    </div>
                                    <div style="text-align:right;flex-shrink:0;">
                                        <div class="result-code" style="font-size:1em;">
                                            R$ {format_currency_br(valor)}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
            else:
                st.markdown(
                    """
                    <div class="empty-state">
                        Nenhum valor calculado para os parâmetros selecionados.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
