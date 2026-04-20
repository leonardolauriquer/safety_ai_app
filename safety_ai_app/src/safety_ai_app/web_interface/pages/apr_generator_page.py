# src/safety_ai_app/web_interface/pages/apr_generator_page.py

import streamlit as st
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import date
from io import BytesIO
import base64
from PIL import Image, ImageOps # Importar ImageOps para inverter cores
import os
import tempfile
import sys

PYTHONCOM_AVAILABLE = False
if sys.platform == "win32":
    try:
        import pythoncom
        PYTHONCOM_AVAILABLE = True
    except ImportError:
        pass

# Tenta importar docx2pdf. Se falhar, a funcionalidade de PDF não estará disponível.
try:
    from docx2pdf import convert
    DOCX2PDF_AVAILABLE = True
except ImportError:
    convert = None
    DOCX2PDF_AVAILABLE = False
    logging.warning("A biblioteca 'docx2pdf' não está instalada. A conversão para PDF não estará disponível.")
except Exception as e:
    convert = None
    DOCX2PDF_AVAILABLE = False
    logging.error(f"Erro ao importar 'docx2pdf': {e}. A conversão para PDF não estará disponível.")


try:
    from safety_ai_app.feature_access import user_has_feature, render_upgrade_prompt
except ImportError:
    def user_has_feature(f):  # noqa: E301
        st.error("⚠️ Módulo de controle de acesso indisponível. Acesso bloqueado.")
        return False
    def render_upgrade_prompt(feature_label="este recurso"):  # noqa: E301
        st.warning("Recurso não disponível. Entre em contato com o administrador.")

# Importa _get_material_icon_html e THEME do theme_config
try:
    from safety_ai_app.theme_config import _get_material_icon_html, THEME
    from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker
except ImportError:
    st.error("Erro ao carregar configurações de tema. Verifique 'theme_config.py'.")
    _get_material_icon_html = lambda icon: f"<span>{icon}</span>" # Fallback
    THEME = {"phrases": {}, "icons": {}} # Fallback
    inject_glass_styles = lambda: None
    glass_marker = lambda: ""

# Importa o gerador de documentos da APR
try:
    from safety_ai_app.document_generators.apr_document_generator import create_apr_document
except ImportError:
    st.error("Erro ao carregar o gerador de documentos da APR. Verifique 'safety_ai_app/document_generators/apr_document_generator.py'.")
    create_apr_document = None # Fallback

# Importa o componente de canvas para assinatura
try:
    from streamlit_drawable_canvas import st_canvas
except ImportError:
    st.warning("A biblioteca 'streamlit-drawable-canvas' não está instalada. A funcionalidade de assinatura digital não estará disponível.")
    st_canvas = None # Fallback

logger = logging.getLogger(__name__)


def _alert(msg: str, kind: str = "info") -> None:
    styles = {
        "error":   ("rgba(239,68,68,0.08)",   "rgba(239,68,68,0.25)",   "#F87171", "alert"),
        "warning": ("rgba(245,158,11,0.08)",  "rgba(245,158,11,0.25)",  "#FBBF24", "warning"),
        "info":    ("rgba(34,211,238,0.06)",  "rgba(34,211,238,0.20)",  "#22D3EE", "info"),
        "success": ("rgba(74,222,128,0.08)",  "rgba(74,222,128,0.25)",  "#4ADE80", "check"),
    }
    bg, border, color, icon_key = styles.get(kind, styles["info"])
    icon_html = _get_material_icon_html(icon_key) if callable(_get_material_icon_html) else ""
    st.markdown(
        f'<div class="info-hint" style="background:{bg};border-color:{border};color:{color};">'
        f'{icon_html} {msg}</div>',
        unsafe_allow_html=True,
    )


# --- Listas pré-definidas para seleção (baseadas nos seus exemplos) ---
COMMON_EPIS = [
    "Capacete com jugular", "Óculos de segurança", "Protetor auditivo", "Bota de segurança",
    "Luva de vaqueta", "Luva impermeável", "Respirador PFF-2", "Protetor facial",
    "Cinto de segurança (Paraquedista)", "Trava Quedas", "Vestimenta de couro",
    "Uniforme normativo", "Creme de proteção", "Escudo de solda", "Mangotes/Perneiras/Avental/Blusão de Raspa",
    "Máscaras (Filtro, Celeron, Autônoma)", "Bota/Luva alta tensão", "Calça jeans / Camisa de brim manga longa"
]

COMMON_EQUIPMENTS_TOOLS = [
    "Ferramentas manuais", "Pistola pneumática", "Máquina de solda", "Esmerilhadeira",
    "Conjunto oxicorte", "Guindauto/Munck", "Empilhadeira", "Ponte rolante", "Talha",
    "Andaime", "Escadas (simples/extensível)", "Betoneira", "Furadeira", "Lixadeira",
    "Serra circular", "Máquina de corte plasma", "Máquina de metalização", "Macaco hidráulico",
    "Tifor/Talhas Manuais", "Estropos/Cintas", "Compressor", "Extensão elétrica",
    "Equipamento/Ferramenta de uso em alta tensão", "Iluminação", "Pá/Enxada/Picareta/Alavanca"
]

WASTE_TYPES = ["Plástico", "Sucata metálica", "Lixo comum", "Borracha", "Contaminados com óleos e/ou graxas", "Papel", "Madeira", "Fibra cerâmica", "Resíduo cáustico", "Resíduo de resinas/tintas"]

COMMON_MEASURES = [
    "Etiquetamento e bloqueios elétricos NR-10", "Não ficar ou permanecer em baixo de cargas",
    "Ferramentas elétricas/pneumáticas NR-12", "Somente adentrar a área operacional após liberação do trabalho",
    "Comunicar ao responsável da área operacional qualquer incidente", "Inspecionar todas as ferramentas e equipamentos antes do uso",
    "Manter e usar corretamente os EPI's específicos para a tarefa", "Não operar, ligar/desligar qualquer equipamento de processo não especificado nesta APR",
    "Não deixar cabos elétricos em atrito com ferragens", "Comunicar as atividades para equipes vizinhas",
    "Participar do DDS e divulgação da APR", "Isolar e sinalizar corretamente o local",
    "Acessórios de içar/manilhas/cintas/correntes etc.", "Cumprir as normas e procedimentos de segurança",
    "Realizar etiquetamento e bloqueios mecânicos", "Biombo/tapume", "Manter a atenção no trabalho",
    "Exaustor", "Equipamento para resgate", "Kit Ambiental", "Procedimento cor do mês",
    "FISPQ", "Talhas manuais de correntes", "Extintor", "Multigás", "Plano de rigger",
    "Caminhões/prancha"
]

COMMON_TRAININGS = [
    "NR 10 - Segurança em Instalações e Serviços em Eletricidade",
    "NR 12 - Segurança no Trabalho em Máquinas e Equipamentos",
    "NR 33 - Segurança e Saúde nos Trabalhos em Espaços Confinados",
    "NR 35 - Trabalho em Altura",
    "Primeiros Socorros",
    "Combate a Incêndio",
    "Operação de Empilhadeira",
    "Operação de Ponte Rolante",
    "Operação de Guindauto/Munck",
    "DDS - Diálogo Diário de Segurança"
]

# Novas opções para Probabilidade e Severidade
PROBABILITY_OPTIONS = ["Rara", "Baixa", "Média", "Alta", "Muito Alta"]
SEVERITY_OPTIONS = ["Leve", "Moderada", "Grave", "Muito Grave"] # Ordem do menos grave para o mais grave

def _initialize_apr_session_state() -> None:
    """Inicializa o estado da sessão para a página de geração de APR."""
    if "apr_data" not in st.session_state:
        st.session_state.apr_data = {
            "apr_number": "",
            "revision_number": "",
            "start_date": date.today(),
            "end_date": None,
            "work_schedule": "",
            "location": "",
            "company": "",
            "supervisor": "",
            "supervisor_signature_image_base64": None,
            "supervisor_signature_json_data": None,
            "user_logo_base64": None, # Adicionado para o logo do usuário
            "task_name": "",
            "task_objective": "",
            "selected_epis": [],
            "other_epis": "",
            "selected_equipments_tools": [],
            "other_equipments_tools": "",
            "activity_steps": [], # List of dicts: {"id": unique_id, "step_description": "", "hazards": "", "consequences": "", "controls": "", "probability": "", "severity": ""}
            "general_observations": "",
            "emergency_contacts": "",
            "waste_disposal": [],
            "other_waste_disposal": "",
            "additional_measures": [],
            "other_additional_measures": "",
            "trainings": [],
            "other_trainings": "",
            "approvers": [], # List of dicts: {"id": unique_id, "name": "", "role": "", "signature_image_base64": None, "signature_json_data": None}
            "executors": [], # Not implemented yet, but keeping the structure
        }
    if "apr_step_counter" not in st.session_state:
        st.session_state.apr_step_counter = 0 # Para gerenciar IDs únicos das etapas
    if "apr_approvers_counter" not in st.session_state:
        st.session_state.apr_approvers_counter = 0 # Para gerenciar IDs únicos dos aprovadores
    if "generated_pdf_buffer" not in st.session_state:
        st.session_state.generated_pdf_buffer = None
    if "generated_pdf_filename" not in st.session_state:
        st.session_state.generated_pdf_filename = None
    if "shared_drive_link" not in st.session_state:
        st.session_state.shared_drive_link = None


def _add_activity_step_callback() -> None:
    """Callback para adicionar uma nova etapa de atividade ao estado da sessão."""
    st.session_state.apr_data["activity_steps"].append({
        "id": st.session_state.apr_step_counter,
        "step_description": "",
        "hazards": "",
        "consequences": "",
        "controls": "",
        "probability": PROBABILITY_OPTIONS[0], # Default
        "severity": SEVERITY_OPTIONS[0] # Default
    })
    st.session_state.apr_step_counter += 1

def _remove_activity_step_callback(step_id: int) -> None:
    """Callback para remover uma etapa de atividade do estado da sessão."""
    st.session_state.apr_data["activity_steps"] = [
        step for step in st.session_state.apr_data["activity_steps"] if step["id"] != step_id
    ]

def _add_approver_callback() -> None:
    """Callback para adicionar um novo aprovador ao estado da sessão."""
    st.session_state.apr_data["approvers"].append({"id": st.session_state.apr_approvers_counter, "name": "", "role": "", "signature_image_base64": None, "signature_json_data": None})
    st.session_state.apr_approvers_counter += 1

def _remove_approver_callback(approver_id: int) -> None:
    """Callback para remover um aprovador do estado da sessão."""
    st.session_state.apr_data["approvers"] = [a for a in st.session_state.apr_data["approvers"] if a["id"] != approver_id]

# Função auxiliar para renderizar o canvas de assinatura
def _render_signature_canvas(key_prefix: str, current_signature_b64: Optional[str], current_signature_json: Optional[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Renderiza um canvas para assinatura e retorna a assinatura em base64 e os dados JSON.
    A assinatura é persistida através de reruns se não houver nova interação.
    """
    if st_canvas:
        st.write("Desenhe sua assinatura abaixo:")
        
        # Always use the current state from session_state as initial_drawing
        initial_json_for_canvas = current_signature_json if current_signature_json else {"version": "5.2.4", "objects": []}
        
        canvas_result = st_canvas(
            fill_color="rgba(0, 0, 0, 0)",  # Fundo transparente no canvas
            stroke_width=2,
            stroke_color="#FFFFFF",  # Cor da linha (branco) para o desenho no canvas
            background_color="#000000", # Fundo preto do canvas
            height=150,
            width=300,
            drawing_mode="freedraw",
            key=f"canvas_{key_prefix}",
            initial_drawing=initial_json_for_canvas
        )

        # Initialize return values with current state
        new_b64 = current_signature_b64
        new_json = current_signature_json

        # Check if the canvas component returned data (meaning it was rendered and possibly interacted with)
        # and if there are actual objects drawn.
        if canvas_result.json_data is not None:
            if len(canvas_result.json_data.get("objects", [])) > 0: # User drew something
                pil_image = Image.fromarray(canvas_result.image_data)
                
                # Convert white-on-black drawing to black-on-white
                # Create a transparent image with black strokes
                black_stroke_transparent_bg = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
                for x in range(pil_image.width):
                    for y in range(pil_image.height):
                        r_orig, g_orig, b_orig, a_orig = pil_image.getpixel((x, y)) 
                        # If the pixel is not black (it's part of the white stroke)
                        if r_orig > 0 or g_orig > 0 or b_orig > 0:
                            black_stroke_transparent_bg.putpixel((x, y), (0, 0, 0, a_orig)) # Make stroke black
                
                # Paste this transparent black stroke image onto a white background
                final_image = Image.new('RGB', pil_image.size, (255, 255, 255)) # White background
                final_image.paste(black_stroke_transparent_bg, (0, 0), black_stroke_transparent_bg) # Paste black stroke
                
                buffered = BytesIO()
                final_image.save(buffered, format="PNG")
                new_b64 = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
                new_json = canvas_result.json_data
            else: # Canvas is empty (user cleared it or never drew)
                new_b64 = None
                new_json = {"version": "5.2.4", "objects": []} # Explicitly empty JSON
        
        # Button to clear the signature
        if st.button("Limpar Assinatura", key=f"clear_canvas_{key_prefix}"):
            new_b64 = None
            new_json = {"version": "5.2.4", "objects": []}
            st.rerun() # Force a rerun to update the canvas with empty initial_drawing
            
        return new_b64, new_json
    else:
        _alert("Componente de assinatura digital não disponível. Instale 'streamlit-drawable-canvas'.", "warning")
        return current_signature_b64, current_signature_json

def apr_generator_page() -> None:
    """
    Renderiza a página de geração de Análise Preliminar de Risco (APR).
    """
    if not user_has_feature("document_generation"):
        render_upgrade_prompt("Geração de APR (Análise Preliminar de Risco)")
        return

    _initialize_apr_session_state()

    apr_icon = THEME['icons'].get('apr_generator_icon', 'assignment')
    apr_title = THEME['phrases'].get('apr_generator', 'Geração de APR')

    inject_glass_styles()

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(f'''
        <div class="page-header">
            {_get_material_icon_html(apr_icon)}
            <h1>{apr_title}</h1>
        </div>
        <div class="page-subtitle">Preencha os campos abaixo para gerar sua Análise Preliminar de Risco (APR).</div>
        ''', unsafe_allow_html=True)

    st.markdown(f'<div class="section-title">{_get_material_icon_html("info")} 1. Identificação da APR</div>', unsafe_allow_html=True)

    uploaded_logo = st.file_uploader(
        "Logo da empresa (PNG/JPG — opcional, aparecerá no cabeçalho do documento)",
        type=["png", "jpg", "jpeg"],
        key="user_logo_uploader"
    )

    if uploaded_logo is not None:
        # Exibir pré-visualização
        st.image(uploaded_logo, width=100, caption="Pré-visualização do Logo")
        st.caption("Recomendado: Largura máxima de 2.5 cm (aproximadamente 95 pixels) e fundo transparente para melhor ajuste no cabeçalho.")
        
        # Converter para base64 e armazenar no session_state
        bytes_data = uploaded_logo.getvalue()
        user_logo_base64_encoded = base64.b64encode(bytes_data).decode('utf-8')
        st.session_state.apr_data["user_logo_base64"] = f"data:{uploaded_logo.type};base64,{user_logo_base64_encoded}"
        logger.info("Logo do usuário carregado e armazenado em base64.")
    elif st.session_state.apr_data["user_logo_base64"] is not None:
        # Se um logo já foi carregado e a página recarregou, manter a pré-visualização
        try:
            # Extrair o base64 puro e o tipo para exibir
            header, encoded = st.session_state.apr_data["user_logo_base64"].split(',', 1)
            # mime_type = header.split(';')[0].split(':')[1] # Não é necessário para st.image
            st.image(base64.b64decode(encoded), width=100, caption="Pré-visualização do Logo (já carregado)")
            st.caption("Recomendado: Largura máxima de 2.5 cm (aproximadamente 95 pixels) e fundo transparente para melhor ajuste no cabeçalho.")
        except Exception as e:
            logger.error(f"Erro ao exibir logo pré-carregado: {e}")
            st.session_state.apr_data["user_logo_base64"] = None # Limpar se houver erro
    else:
        st.session_state.apr_data["user_logo_base64"] = None # Garantir que seja None se nada for carregado

    col1, col2, col3 = st.columns(3)
    with col1:
        st.session_state.apr_data["apr_number"] = st.text_input("Número da APR", value=st.session_state.apr_data["apr_number"], key="apr_num")
    with col2:
        st.session_state.apr_data["revision_number"] = st.text_input("Revisão", value=st.session_state.apr_data["revision_number"], key="apr_rev")
    with col3:
        # st.date_input exibe a data no formato local do navegador.
        # Não há como forçar DD/MM/AAAA se o navegador não estiver configurado para pt-BR.
        st.session_state.apr_data["start_date"] = st.date_input("Data de Início", value=st.session_state.apr_data["start_date"], key="apr_start_date")
    
    col4, col5 = st.columns(2)
    with col4:
        st.session_state.apr_data["end_date"] = st.date_input("Data de Término (Opcional)", value=st.session_state.apr_data["end_date"] if st.session_state.apr_data["end_date"] else None, key="apr_end_date")
    # Removido o campo de Validade

    st.session_state.apr_data["work_schedule"] = st.text_input("Horário de Trabalho", value=st.session_state.apr_data["work_schedule"], placeholder="Ex: 1º Turno (07:00-17:00)", key="apr_schedule")
    st.session_state.apr_data["location"] = st.text_input("Local / Área / Setor", value=st.session_state.apr_data["location"], placeholder="Ex: Canteiro de Obras - Pátio de Ferragem", key="apr_location")
    st.session_state.apr_data["company"] = st.text_input("Empresa / Contratada", value=st.session_state.apr_data["company"], placeholder="Ex: ENCALSO CONSTRUÇÕES LTDA", key="apr_company")
    
    # Campo de supervisor e sua assinatura
    st.session_state.apr_data["supervisor"] = st.text_input("Supervisor / Encarregado Responsável", value=st.session_state.apr_data["supervisor"], key="apr_supervisor")
    st.markdown(f"**Assinatura Digital do Supervisor {st.session_state.apr_data.get('supervisor', '')}:**")
    
    # Atualiza tanto a imagem base64 quanto os dados JSON da assinatura do supervisor
    st.session_state.apr_data["supervisor_signature_image_base64"], st.session_state.apr_data["supervisor_signature_json_data"] = _render_signature_canvas(
        "supervisor_signature", 
        st.session_state.apr_data["supervisor_signature_image_base64"],
        st.session_state.apr_data["supervisor_signature_json_data"]
    )
    # Pré-visualização da assinatura do supervisor (sempre abaixo do canvas)
    if st.session_state.apr_data["supervisor_signature_image_base64"]:
        st.image(st.session_state.apr_data["supervisor_signature_image_base64"], width=150, caption="Pré-visualização da Assinatura do Supervisor")

    st.markdown(f'<div class="section-title">{_get_material_icon_html("work")} 2. Detalhes da Atividade/Tarefa</div>', unsafe_allow_html=True)
    st.session_state.apr_data["task_name"] = st.text_input("Nome da Atividade / Tarefa Específica", value=st.session_state.apr_data["task_name"], placeholder="Ex: Corte e Dobra de Ferragem", key="apr_task_name")
    st.session_state.apr_data["task_objective"] = st.text_area("Objetivo da Atividade", value=st.session_state.apr_data["task_objective"], placeholder="Descreva o objetivo principal da tarefa.", key="apr_task_obj")
    
    st.markdown(f'<div class="section-title">{_get_material_icon_html("shield")} 3. EPIs e Equipamentos/Ferramentas</div>', unsafe_allow_html=True)
    st.session_state.apr_data["selected_epis"] = st.multiselect(
        "Selecione os EPIs necessários:", # Label em português
        options=COMMON_EPIS,
        default=[item for item in st.session_state.apr_data["selected_epis"] if item in COMMON_EPIS],
        key="apr_epis"
    )
    st.session_state.apr_data["other_epis"] = st.text_area("Outros EPIs (se houver)", value=st.session_state.apr_data["other_epis"], placeholder="Liste outros EPIs não mencionados acima, um por linha.", key="apr_other_epis")

    st.session_state.apr_data["selected_equipments_tools"] = st.multiselect(
        "Selecione os Equipamentos e Ferramentas necessários:", # Label em português
        options=COMMON_EQUIPMENTS_TOOLS,
        default=[item for item in st.session_state.apr_data["selected_equipments_tools"] if item in COMMON_EQUIPMENTS_TOOLS],
        key="apr_equip_tools"
    )
    st.session_state.apr_data["other_equipments_tools"] = st.text_area("Outros Equipamentos/Ferramentas (se houver)", value=st.session_state.apr_data["other_equipments_tools"], placeholder="Liste outros equipamentos/ferramentas, um por linha.", key="apr_other_equip_tools")
    
    st.markdown(f'<div class="section-title">{_get_material_icon_html("alert")} 4. Detalhamento da Atividade e Análise de Risco</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-hint">Adicione os riscos da atividade em sequência e analise-os, definindo a probabilidade e severidade.</div>', unsafe_allow_html=True)

    # Botão alterado para "Adicionar Risco"
    if st.button("Adicionar Risco", on_click=_add_activity_step_callback, key="add_step_btn_outside"):
        st.rerun()

    if not st.session_state.apr_data["activity_steps"]:
        _alert("Clique em 'Adicionar Risco' para começar a detalhar a análise de risco por etapa da atividade.", "info")

    for i, step in enumerate(st.session_state.apr_data["activity_steps"]):
        with st.expander(f"Risco {i+1}: {step['step_description'] if step['step_description'] else 'Nova Análise de Risco'}", expanded=True):
            step["step_description"] = st.text_input(f"Descrição da Etapa/Atividade Relacionada ao Risco {i+1}", key=f"step_desc_{step['id']}", value=step["step_description"], placeholder="Ex: Posicionamento da máquina de corte")
            step["hazards"] = st.text_area(f"Perigos e Riscos Identificados (Risco {i+1})", key=f"hazards_{step['id']}", value=step["hazards"], placeholder="Ex: Ruído excessivo, projeção de partículas, corte, prensamento")
            step["consequences"] = st.text_area(f"Consequências (Risco {i+1})", key=f"consequences_{step['id']}", value=step["consequences"], placeholder="Ex: Perda auditiva, lesões oculares, amputação")
            step["controls"] = st.text_area(f"Medidas de Controle (Risco {i+1})", key=f"controls_{step['id']}", value=step["controls"], placeholder="Ex: Protetor auricular, óculos de segurança, luvas de raspa, isolamento da área")
            
            col_prob, col_sev = st.columns(2)
            with col_prob:
                step["probability"] = st.selectbox(
                    f"Probabilidade (Risco {i+1})",
                    options=PROBABILITY_OPTIONS,
                    index=PROBABILITY_OPTIONS.index(step["probability"]) if step["probability"] in PROBABILITY_OPTIONS else 0,
                    key=f"prob_{step['id']}"
                )
            with col_sev:
                step["severity"] = st.selectbox(
                    f"Severidade (Risco {i+1})",
                    options=SEVERITY_OPTIONS,
                    index=SEVERITY_OPTIONS.index(step["severity"]) if step["severity"] in SEVERITY_OPTIONS else 0,
                    key=f"sev_{step['id']}"
                )

            if st.button("Remover Risco", key=f"remove_step_{step['id']}", on_click=_remove_activity_step_callback, args=(step["id"],)):
                st.rerun()
    st.markdown(f'<div class="section-title">{_get_material_icon_html("comment")} 5. Observações Gerais</div>', unsafe_allow_html=True)
    st.session_state.apr_data["general_observations"] = st.text_area(
        "Observações Importantes",
        value=st.session_state.apr_data["general_observations"],
        placeholder="Ex: Qualquer risco, etapa ou situação não prevista na APR, o trabalho deverá ser parado de imediato e solicitado ajuda da equipe de aprovação.",
        key="apr_obs"
    )

    st.markdown(f'<div class="section-title">{_get_material_icon_html("phone")} 6. Contatos de Emergência</div>', unsafe_allow_html=True)
    st.session_state.apr_data["emergency_contacts"] = st.text_area(
        "Telefones e Procedimentos de Emergência",
        value=st.session_state.apr_data["emergency_contacts"],
        placeholder="Ex: Ramal 5555, Faixa de Rádio 01. Em incidentes com lesão, aguardar ambulância.",
        key="apr_emergency"
    )

    st.markdown(f'<div class="section-title">{_get_material_icon_html("recycle")} 7. Disposição de Resíduos</div>', unsafe_allow_html=True)
    st.session_state.apr_data["waste_disposal"] = st.multiselect(
        "Tipos de Resíduos Gerados:",
        options=WASTE_TYPES,
        default=[item for item in st.session_state.apr_data["waste_disposal"] if item in WASTE_TYPES],
        key="apr_waste"
    )
    st.session_state.apr_data["other_waste_disposal"] = st.text_area(
        "Outros Resíduos e Observações sobre Disposição",
        value=st.session_state.apr_data["other_waste_disposal"],
        placeholder="Ex: Os resíduos deverão ser dispostos nos coletores/containers específicos localizados nas áreas de resíduos.",
        key="apr_other_waste"
    )

    st.markdown(f'<div class="section-title">{_get_material_icon_html("checklist")} 8. Medidas a Serem Adotadas pelos Envolvidos</div>', unsafe_allow_html=True)
    st.session_state.apr_data["additional_measures"] = st.multiselect(
        "Selecione as medidas a serem adotadas:",
        options=COMMON_MEASURES,
        default=[item for item in st.session_state.apr_data["additional_measures"] if item in COMMON_MEASURES],
        key="apr_measures"
    )
    st.session_state.apr_data["other_additional_measures"] = st.text_area(
        "Outras Medidas Adicionais (se houver)",
        value=st.session_state.apr_data["other_additional_measures"],
        placeholder="Liste outras medidas não mencionadas acima, um por linha.",
        key="apr_other_measures"
    )
    
    st.markdown(f'<div class="section-title">{_get_material_icon_html("school")} 9. Treinamentos</div>', unsafe_allow_html=True)
    st.session_state.apr_data["trainings"] = st.multiselect(
        "Selecione os treinamentos relevantes:",
        options=COMMON_TRAININGS,
        default=[item for item in st.session_state.apr_data["trainings"] if item in COMMON_TRAININGS],
        key="apr_trainings"
    )
    st.session_state.apr_data["other_trainings"] = st.text_area(
        "Outros Treinamentos (se houver)",
        value=st.session_state.apr_data["other_trainings"],
        placeholder="Liste outros treinamentos não mencionados acima, um por linha.",
        key="apr_other_trainings"
    )

    st.markdown(f'<div class="section-title">{_get_material_icon_html("signature")} 10. Responsáveis pela Aprovação</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-hint">Adicione os responsáveis pela aprovação da APR e colete suas assinaturas digitais.</div>', unsafe_allow_html=True)
    
    if st.button("Adicionar Aprovador", on_click=_add_approver_callback, key="add_approver_btn_outside"):
        st.rerun()

    for i, approver in enumerate(st.session_state.apr_data["approvers"]):
        with st.container(border=True):
            cols_app = st.columns([0.45, 0.45, 0.1])
            with cols_app[0]:
                approver["name"] = st.text_input(f"Nome do Aprovador {i+1}", key=f"approver_name_{approver['id']}", value=approver["name"])
            with cols_app[1]:
                approver["role"] = st.text_input(f"Cargo do Aprovador {i+1}", key=f"approver_role_{approver['id']}", value=approver["role"])
            with cols_app[2]:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("X", key=f"remove_approver_{approver['id']}", on_click=_remove_approver_callback, args=(approver["id"],)):
                    st.rerun()
            
            st.write("---")
            st.markdown(f"**Assinatura Digital de {approver.get('name', f'Aprovador {i+1}')}:**")
            # Atualiza tanto a imagem base64 quanto os dados JSON da assinatura do aprovador
            approver["signature_image_base64"], approver["signature_json_data"] = _render_signature_canvas(
                f"approver_signature_{approver['id']}", 
                approver["signature_image_base64"],
                approver["signature_json_data"]
            )
            if approver["signature_image_base64"]:
                st.image(approver["signature_image_base64"], width=150, caption="Pré-visualização da Assinatura")

    # Botão final para gerar a APR completa e baixar o documento
    if st.button("Gerar APR Completa", key="generate_apr_btn"):
        if create_apr_document:
            with st.spinner("Gerando e convertendo documento... Por favor, aguarde."): # Adicionado spinner
                try:
                    # Limpa o estado de PDF e link de compartilhamento anteriores
                    st.session_state.generated_pdf_buffer = None
                    st.session_state.generated_pdf_filename = None
                    st.session_state.shared_drive_link = None

                    final_additional_measures = list(st.session_state.apr_data["additional_measures"])
                    if st.session_state.apr_data["other_additional_measures"]:
                        final_additional_measures.extend([
                            m.strip() for m in st.session_state.apr_data["other_additional_measures"].split('\n') if m.strip()
                        ])
                    
                    final_trainings = list(st.session_state.apr_data["trainings"])
                    if st.session_state.apr_data["other_trainings"]:
                        final_trainings.extend([
                            t.strip() for t in st.session_state.apr_data["other_trainings"].split('\n') if t.strip()
                        ])

                    apr_data_for_doc = st.session_state.apr_data.copy()
                    apr_data_for_doc["additional_measures"] = final_additional_measures
                    apr_data_for_doc["trainings"] = final_trainings

                    # 1. Gerar DOCX
                    # Passa o logo do usuário para a função de geração do documento
                    docx_buffer = create_apr_document(apr_data_for_doc, user_logo_base64=st.session_state.apr_data["user_logo_base64"])
                    
                    apr_num = st.session_state.apr_data.get('apr_number', 'SemNumero')
                    apr_rev = st.session_state.apr_data.get('revision_number', '0')
                    base_filename = f"APR_{apr_num}_Rev{apr_rev}_{date.today().strftime('%Y%m%d')}"
                    docx_filename = f"{base_filename}.docx"
                    pdf_filename = f"{base_filename}.pdf"

                    # 2. Converter DOCX para PDF
                    if DOCX2PDF_AVAILABLE:
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_docx_file:
                                temp_docx_file.write(docx_buffer.getvalue())
                                temp_docx_path = temp_docx_file.name
                            
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf_file:
                                temp_pdf_path = temp_pdf_file.name
                            
                            if PYTHONCOM_AVAILABLE:
                                pythoncom.CoInitialize()
                            try:
                                convert(temp_docx_path, temp_pdf_path)
                            finally:
                                if PYTHONCOM_AVAILABLE:
                                    pythoncom.CoUninitialize()
                            
                            with open(temp_pdf_path, "rb") as f:
                                st.session_state.generated_pdf_buffer = BytesIO(f.read())
                            st.session_state.generated_pdf_filename = pdf_filename
                            
                            _alert("APR gerada e convertida para PDF com sucesso!", "success")
                            logger.info(f"Documento APR '{pdf_filename}' gerado e pronto para download.")

                        except FileNotFoundError as fnfe:
                            _alert(
                                f"Ferramenta externa (LibreOffice/Microsoft Word) não encontrada. "
                                f"O documento será baixado como DOCX. Detalhes: {fnfe}",
                                "warning"
                            )
                            logger.error(f"FileNotFoundError durante conversão para PDF: {fnfe}", exc_info=True)
                            st.session_state.generated_pdf_buffer = docx_buffer
                            st.session_state.generated_pdf_filename = docx_filename
                        except Exception as e:
                            _alert(f"Erro ao converter para PDF: {e}. O documento será baixado como DOCX.", "warning")
                            logger.error(f"Erro inesperado durante conversão para PDF: {e}", exc_info=True)
                            st.session_state.generated_pdf_buffer = docx_buffer
                            st.session_state.generated_pdf_filename = docx_filename
                        finally:
                            if 'temp_docx_path' in locals() and os.path.exists(temp_docx_path):
                                os.remove(temp_docx_path)
                            if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
                                os.remove(temp_pdf_path)
                    else:
                        _alert("A biblioteca 'docx2pdf' não está instalada. O documento será baixado como DOCX.", "warning")
                        st.session_state.generated_pdf_buffer = docx_buffer
                        st.session_state.generated_pdf_filename = docx_filename
                except Exception as e:
                    _alert(f"Erro ao gerar o documento da APR: {e}", "error")
                    logger.error(f"Erro ao gerar documento da APR: {e}", exc_info=True)
        else:
            _alert("O gerador de documentos da APR não foi carregado corretamente. Verifique os logs.", "warning")
    
    # Exibe botões de download e compartilhamento se o PDF foi gerado
    if st.session_state.generated_pdf_buffer:
        col_download, col_share = st.columns([0.5, 0.5])
        with col_download:
            st.download_button(
                label=f"Baixar {st.session_state.generated_pdf_filename.split('.')[-1].upper()}",
                data=st.session_state.generated_pdf_buffer.getvalue(),
                file_name=st.session_state.generated_pdf_filename,
                mime="application/pdf" if st.session_state.generated_pdf_filename.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="download_apr_final_button"
            )
        with col_share:
            if st.button("Compartilhar no Google Drive", key="share_apr_button"):
                if st.session_state.get('google_drive_integrator') and st.session_state.google_drive_integrator.get_user_service():
                    with st.spinner("Fazendo upload e gerando link de compartilhamento..."):
                        # É importante passar uma cópia do buffer para o upload, pois ele pode ser consumido
                        pdf_buffer_copy = BytesIO(st.session_state.generated_pdf_buffer.getvalue())
                        share_link = st.session_state.google_drive_integrator.upload_file_and_get_share_link(
                            file_content=pdf_buffer_copy,
                            file_name=st.session_state.generated_pdf_filename,
                            folder_id=st.session_state.google_drive_integrator.donation_folder_id # Ou outra pasta específica para APRs
                        )
                        if share_link:
                            st.session_state.shared_drive_link = share_link
                            _alert("Documento enviado para o Google Drive e link gerado!", "success")
                        else:
                            _alert("Falha ao enviar para o Google Drive. Verifique sua autenticação.", "error")
                else:
                    _alert("Autentique-se com o Google Drive antes de compartilhar. Sincronize sua conta primeiro.", "warning")
        
        if st.session_state.shared_drive_link:
            st.markdown(f"**Link de Compartilhamento:** [Abrir no Google Drive]({st.session_state.shared_drive_link}){{target='_blank'}}")
            _alert("O compartilhamento via WhatsApp/Gmail não é suportado diretamente pelo Streamlit. O botão acima compartilha no Google Drive.", "info")