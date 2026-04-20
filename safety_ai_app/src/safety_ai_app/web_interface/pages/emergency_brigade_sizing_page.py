import streamlit as st
import logging
from typing import Dict, Any
from safety_ai_app.theme_config import THEME, _get_material_icon_html
from safety_ai_app.cnae_risk_data_processor import CNAERiskDataProcessor
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker, render_back_button

logger = logging.getLogger(__name__)

_RISK_COLORS = {"baixo": "#4ADE80", "medio": "#F59E0B", "alto": "#EF4444"}


def _alert(msg: str, kind: str = "info") -> None:
    styles = {
        "error":   ("rgba(239,68,68,0.08)",   "rgba(239,68,68,0.25)",   "#F87171", "alert"),
        "warning": ("rgba(245,158,11,0.08)",  "rgba(245,158,11,0.25)",  "#FBBF24", "warning"),
        "info":    ("rgba(34,211,238,0.06)",  "rgba(34,211,238,0.20)",  "#22D3EE", "info"),
        "success": ("rgba(74,222,128,0.08)",  "rgba(74,222,128,0.25)",  "#4ADE80", "check"),
    }
    bg, border, color, icon = styles.get(kind, styles["info"])
    st.markdown(
        f'<div class="info-hint" style="background:{bg};border-color:{border};color:{color};">'
        f'{_get_material_icon_html(icon)} {msg}</div>',
        unsafe_allow_html=True,
    )

BRIGADE_TABLE = {
    "baixo": {
        (0, 10): {"brigadistas": 0, "obs": "Sem exigência formal. Recomenda-se treinamento básico."},
        (11, 25): {"brigadistas": 2, "obs": "Mínimo recomendado para pequenas instalações."},
        (26, 50): {"brigadistas": 4, "obs": ""},
        (51, 100): {"brigadistas": 6, "obs": ""},
        (101, 250): {"brigadistas": 8, "obs": ""},
        (251, 500): {"brigadistas": 10, "obs": ""},
        (501, 1000): {"brigadistas": 15, "obs": ""},
        (1001, 2500): {"brigadistas": 20, "obs": ""},
        (2501, float('inf')): {"brigadistas": 25, "obs": "Para cada 1000 pessoas adicionais, acrescentar 5 brigadistas."},
    },
    "medio": {
        (0, 10): {"brigadistas": 2, "obs": "Mínimo recomendado."},
        (11, 25): {"brigadistas": 4, "obs": ""},
        (26, 50): {"brigadistas": 6, "obs": ""},
        (51, 100): {"brigadistas": 10, "obs": ""},
        (101, 250): {"brigadistas": 15, "obs": ""},
        (251, 500): {"brigadistas": 20, "obs": ""},
        (501, 1000): {"brigadistas": 25, "obs": ""},
        (1001, 2500): {"brigadistas": 35, "obs": ""},
        (2501, float('inf')): {"brigadistas": 50, "obs": "Para cada 1000 pessoas adicionais, acrescentar 10 brigadistas."},
    },
    "alto": {
        (0, 10): {"brigadistas": 4, "obs": "Mínimo obrigatório para alto risco."},
        (11, 25): {"brigadistas": 6, "obs": ""},
        (26, 50): {"brigadistas": 10, "obs": ""},
        (51, 100): {"brigadistas": 15, "obs": ""},
        (101, 250): {"brigadistas": 25, "obs": ""},
        (251, 500): {"brigadistas": 35, "obs": ""},
        (501, 1000): {"brigadistas": 50, "obs": ""},
        (1001, 2500): {"brigadistas": 70, "obs": ""},
        (2501, float('inf')): {"brigadistas": 100, "obs": "Para cada 1000 pessoas adicionais, acrescentar 20 brigadistas."},
    },
}

RISK_LEVEL_MAPPING = {
    1: "baixo",
    2: "medio",
    3: "medio",
    4: "alto",
}

def get_brigade_dimensioning(risk_level: str, population: int) -> Dict[str, Any]:
    if risk_level not in BRIGADE_TABLE:
        return {"error": "Nível de risco inválido."}
    
    table = BRIGADE_TABLE[risk_level]
    
    for (min_pop, max_pop), data in table.items():
        if min_pop <= population <= max_pop:
            result = {
                "brigadistas": data["brigadistas"],
                "nivel_risco": risk_level,
                "populacao": population,
                "observacao": data["obs"] if data["obs"] else None
            }
            
            if max_pop == float('inf') and population > 2500:
                base = data["brigadistas"]
                excess = population - 2500
                groups = (excess + 999) // 1000
                
                if risk_level == "baixo":
                    additional = groups * 5
                elif risk_level == "medio":
                    additional = groups * 10
                else:
                    additional = groups * 20
                
                result["brigadistas"] = base + additional
                result["observacao"] = f"Base de {base} brigadistas + {additional} adicionais para população excedente."
            
            return result
    
    return {"error": "Não foi possível calcular o dimensionamento."}


def emergency_brigade_sizing_page() -> None:
    inject_glass_styles()

    render_back_button("← Dimensionamentos", "sizing_page", "back_from_brigade")

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="page-header">
                {_get_material_icon_html('fire')}
                <h1>Brigada de Emergência</h1>
            </div>
            <div class="page-subtitle">
                Calcule o número de brigadistas necessários conforme o nível de risco
                e a população fixa do estabelecimento.
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with st.container():
        st.markdown(f'''
            <div class="section-title">
                {_get_material_icon_html('calculator')}
                <span>Dados do Estabelecimento</span>
            </div>
        ''', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            cnae_input = st.text_input(
                "Código CNAE (opcional)",
                placeholder="Ex: 4120-4/00",
                help="Informe o CNAE para determinar automaticamente o grau de risco."
            )
        
        with col2:
            manual_risk = st.selectbox(
                "Nível de Risco",
                options=["Selecione...", "Baixo (Grau 1)", "Médio (Grau 2-3)", "Alto (Grau 4)"],
                help="Se informar o CNAE, o risco será preenchido automaticamente."
            )
        
        detected_risk = None
        if cnae_input:
            try:
                processor = CNAERiskDataProcessor()
                grau_risco = processor.get_risk_level(cnae_input)
                if grau_risco:
                    detected_risk = RISK_LEVEL_MAPPING.get(grau_risco, "medio")
                    risk_labels = {"baixo": "Baixo", "medio": "Médio", "alto": "Alto"}
                    risk_color = _RISK_COLORS.get(detected_risk, "#64748B")
                    _alert(
                        f"Grau de Risco detectado para o CNAE: "
                        f"<b style='color:{risk_color}'>GR {grau_risco} — {risk_labels.get(detected_risk, 'Desconhecido')}</b>",
                        "success"
                    )
            except Exception as e:
                logger.warning(f"Erro ao buscar grau de risco: {e}")
        
        population = st.number_input(
            "População Fixa do Estabelecimento",
            min_value=0,
            max_value=100000,
            value=100,
            step=10,
            help="Número total de pessoas que frequentam regularmente o local (funcionários + visitantes frequentes)."
        )
        
        if st.button("Calcular Dimensionamento", type="primary", use_container_width=True):
            final_risk = detected_risk
            if not final_risk:
                if "Baixo" in manual_risk:
                    final_risk = "baixo"
                elif "Médio" in manual_risk:
                    final_risk = "medio"
                elif "Alto" in manual_risk:
                    final_risk = "alto"
            
            if not final_risk:
                _alert("Informe o CNAE ou selecione o nível de risco manualmente.", "warning")
            else:
                with st.spinner("Calculando dimensionamento da brigada de emergência..."):
                    result = get_brigade_dimensioning(final_risk, population)

                if "error" in result:
                    _alert(result["error"], "error")
                else:
                    st.markdown(f'''
                        <div class="section-title">
                            {_get_material_icon_html('users')}
                            <span>Resultado do Dimensionamento</span>
                        </div>
                    ''', unsafe_allow_html=True)
                    
                    col_result1, col_result2, col_result3 = st.columns(3)
                    
                    with col_result1:
                        st.metric(
                            label="Brigadistas Necessários",
                            value=result["brigadistas"]
                        )
                    
                    with col_result2:
                        risk_display = {"baixo": "Baixo", "medio": "Médio", "alto": "Alto"}
                        st.metric(
                            label="Nível de Risco",
                            value=risk_display.get(result["nivel_risco"], "N/A")
                        )
                    
                    with col_result3:
                        st.metric(
                            label="População",
                            value=f"{result['populacao']} pessoas"
                        )
                    
                    if result.get("observacao"):
                        _alert(result['observacao'], "info")
                    
                    with st.expander(f"{_get_material_icon_html('info')} Informações sobre Brigada de Emergência", expanded=False):
                        st.markdown("""
**O que é a Brigada de Emergência?**

A Brigada de Incêndio/Emergência é um grupo organizado de pessoas voluntárias ou designadas, 
treinadas e capacitadas para atuar na prevenção, abandono e combate a um princípio de incêndio, 
bem como prestar os primeiros socorros.

**Base Legal:**
- **NBR 14276** - Brigada de incêndio - Requisitos
- **NBR 15219** - Plano de emergência contra incêndio - Requisitos
- **IT 17 do Corpo de Bombeiros** (varia por estado)

**Formação do Brigadista:**
- Primeiros Socorros
- Prevenção e Combate a Incêndio
- Abandono de Área
- Teoria sobre comportamento do fogo
- Exercícios práticos (simulados)

**Reciclagem:**
- O treinamento deve ser reciclado anualmente
- Simulados devem ser realizados semestralmente
                        """)
    
    st.markdown(f'''
        <div class="info-hint" style="text-align: center; margin-top: 20px;">
            {_get_material_icon_html('info')} 
            Este dimensionamento é uma referência baseada em normas e boas práticas. 
            Consulte a legislação estadual e o Corpo de Bombeiros local para requisitos específicos.
        </div>
    ''', unsafe_allow_html=True)


if __name__ == "__main__":
    emergency_brigade_sizing_page()
