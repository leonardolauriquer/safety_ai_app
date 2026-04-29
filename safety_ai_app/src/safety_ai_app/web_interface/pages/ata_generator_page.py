# src/safety_ai_app/web_interface/pages/ata_generator_page.py

import streamlit as st
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import date, time
from io import BytesIO
import base64
from PIL import Image
import os
import tempfile
import sys

# Importa _get_material_icon_html e THEME do theme_config
try:
    from safety_ai_app.theme_config import _get_material_icon_html, THEME
    from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker, render_back_button
    from safety_ai_app.security.security_logger import log_security_event, SecurityEvent
except ImportError:
    st.error("Erro ao carregar configurações de tema. Verifique 'theme_config.py'.")
    _get_material_icon_html = lambda icon: f"<span>{icon}</span>"
    THEME = {"phrases": {}, "icons": {}}
    inject_glass_styles = lambda: None
    glass_marker = lambda: ""
    render_back_button = lambda label, page, key: None

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


# --- Listas pré-definidas para seleção ---
EVENT_TYPES = ["DDS (Diálogo Diário de Segurança)", "Treinamento", "Reunião", "Outro"]
ATTACHMENT_TYPES = ["Foto", "Documento (PDF/DOCX/TXT)", "Nota de Texto"]

def _initialize_ata_session_state() -> None:
    """Inicializa o estado da sessão para a página de geração de Ata."""
    if "ata_data" not in st.session_state:
        st.session_state.ata_data = {
            "event_type": EVENT_TYPES[0],
            "title": "",
            "date": date.today(),
            "start_time": time(8, 0),
            "end_time": time(9, 0),
            "location": "",
            "instructor_name": "",
            "instructor_signature_image_base64": None,
            "instructor_signature_json_data": None,
            "content": "",
            "participants": [], # List of dicts: {"id": unique_id, "name": "", "cpf": "", "signature_image_base64": None, "signature_json_data": None}
            "attachments": [], # List of dicts: {"id": unique_id, "type": "", "description": "", "file_base64": None, "file_name": None, "file_type": None}
            "user_logo_base64": None,
        }
    if "ata_participant_counter" not in st.session_state:
        st.session_state.ata_participant_counter = 0
    if "ata_attachment_counter" not in st.session_state:
        st.session_state.ata_attachment_counter = 0
    if "generated_pdf_buffer" not in st.session_state:
        st.session_state.generated_pdf_buffer = None
    if "generated_pdf_filename" not in st.session_state:
        st.session_state.generated_pdf_filename = None
    if "shared_drive_link" not in st.session_state:
        st.session_state.shared_drive_link = None

def _add_participant_callback() -> None:
    """Callback para adicionar um novo participante ao estado da sessão."""
    st.session_state.ata_data["participants"].append({
        "id": st.session_state.ata_participant_counter,
        "name": "",
        "cpf": "",
        "signature_image_base64": None,
        "signature_json_data": None
    })
    st.session_state.ata_participant_counter += 1

def _remove_participant_callback(participant_id: int) -> None:
    """Callback para remover um participante do estado da sessão."""
    st.session_state.ata_data["participants"] = [
        p for p in st.session_state.ata_data["participants"] if p["id"] != participant_id
    ]

def _add_attachment_callback() -> None:
    """Callback para adicionar um novo anexo ao estado da sessão."""
    st.session_state.ata_data["attachments"].append({
        "id": st.session_state.ata_attachment_counter,
        "type": ATTACHMENT_TYPES[0],
        "description": "",
        "file_base64": None,
        "file_name": None,
        "file_type": None
    })
    st.session_state.ata_attachment_counter += 1

def _remove_attachment_callback(attachment_id: int) -> None:
    """Callback para remover um anexo do estado da sessão."""
    st.session_state.ata_data["attachments"] = [
        a for a in st.session_state.ata_data["attachments"] if a["id"] != attachment_id
    ]

# Função auxiliar para renderizar o canvas de assinatura (reutilizada e aprimorada do APR)
def _render_signature_canvas(key_prefix: str, current_signature_b64: Optional[str], current_signature_json: Optional[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Renderiza um canvas para assinatura e retorna a assinatura em base64 e os dados JSON.
    A assinatura é persistida através de reruns se não houver nova interação.
    A imagem da assinatura é convertida para tinta preta em fundo branco.
    """
    if st_canvas:
        st.write("Desenhe sua assinatura abaixo:")
        
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

        new_b64 = current_signature_b64
        new_json = current_signature_json

        if canvas_result.json_data is not None:
            if len(canvas_result.json_data.get("objects", [])) > 0: # User drew something
                pil_image = Image.fromarray(canvas_result.image_data)
                
                # Convert white-on-black drawing to black-on-white
                black_stroke_transparent_bg = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
                for x in range(pil_image.width):
                    for y in range(pil_image.height):
                        r_orig, g_orig, b_orig, a_orig = pil_image.getpixel((x, y)) 
                        if r_orig > 0 or g_orig > 0 or b_orig > 0: # If the pixel is not black (it's part of the white stroke)
                            black_stroke_transparent_bg.putpixel((x, y), (0, 0, 0, a_orig)) # Make stroke black
                
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

try:
    from safety_ai_app.feature_access import user_has_feature, render_upgrade_prompt
except ImportError:
    def user_has_feature(f):  # noqa: E301
        return True # Default to True if module missing
    def render_upgrade_prompt(feature_label="este recurso"):  # noqa: E301
        st.warning("Recurso não disponível.")

def ata_generator_page() -> None:
    """
    Renderiza a página de geração de Ata.
    """
    if not user_has_feature("document_generation"):
        render_upgrade_prompt("Geração de Ata (DDS / Reunião / Treinamento)")
        return

    _initialize_ata_session_state()

    ata_icon = THEME['icons'].get('ata_generator_icon', 'description')
    ata_title = THEME['phrases'].get('ata_generator', 'Emissão de Ata')

    inject_glass_styles()

    render_back_button("← Início", "home", "back_from_ata")

    # ... (header container)
    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="page-header">
                {_get_material_icon_html(ata_icon)}
                <h1>{ata_title}</h1>
            </div>
            <div class="page-subtitle">
                Preencha os campos abaixo para gerar sua Ata de DDS, Treinamento ou Reunião.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ... (inputs section)
    # [Lines omitted for brevity in thought, but included in replacement]
    # (I'll use the viewed file content to reconstruct exactly)

    st.markdown(f'<div class="section-title">{_get_material_icon_html("info")} 1. Identificação da Ata</div>', unsafe_allow_html=True)

    uploaded_logo = st.file_uploader(
        "Logo da empresa (PNG/JPG — opcional, aparecerá no cabeçalho do documento)",
        type=["png", "jpg", "jpeg"],
        key="user_logo_uploader_ata"
    )

    MAX_FILE_SIZE_MB = 15
    if uploaded_logo is not None:
        logo_size_mb = len(uploaded_logo.getvalue()) / (1024 * 1024)
        if logo_size_mb > MAX_FILE_SIZE_MB:
            try:
                log_security_event(
                    SecurityEvent.FILE_REJECTED,
                    file_name=uploaded_logo.name,
                    file_size_mb=logo_size_mb,
                    detail=f"Logo excede {MAX_FILE_SIZE_MB} MB",
                    feature="ata_logo_upload",
                )
            except Exception as log_err:
                logger.warning(f"Falha ao registrar evento de segurança (logo): {log_err}")
            _alert(f"Logo rejeitado: tamanho máximo é {MAX_FILE_SIZE_MB} MB (enviado: {logo_size_mb:.1f} MB).", "error")
        else:
            st.image(uploaded_logo, width=100, caption="Pré-visualização do Logo")
            st.caption("Recomendado: Largura máxima de 2.5 cm (aproximadamente 95 pixels) e fundo transparente para melhor ajuste no cabeçalho.")
            bytes_data = uploaded_logo.getvalue()
            user_logo_base64_encoded = base64.b64encode(bytes_data).decode('utf-8')
            st.session_state.ata_data["user_logo_base64"] = f"data:{uploaded_logo.type};base64,{user_logo_base64_encoded}"
            logger.info("Logo do usuário carregado e armazenado em base64 para Ata.")
    elif st.session_state.ata_data["user_logo_base64"] is not None:
        try:
            header, encoded = st.session_state.ata_data["user_logo_base64"].split(',', 1)
            st.image(base64.b64decode(encoded), width=100, caption="Pré-visualização do Logo (já carregado)")
            st.caption("Recomendado: Largura máxima de 2.5 cm (aproximadamente 95 pixels) e fundo transparente para melhor ajuste no cabeçalho.")
        except Exception as e:
            logger.error(f"Erro ao exibir logo pré-carregado para Ata: {e}")
            st.session_state.ata_data["user_logo_base64"] = None
    else:
        st.session_state.ata_data["user_logo_base64"] = None

    st.session_state.ata_data["event_type"] = st.selectbox(
        "Tipo de Evento",
        options=EVENT_TYPES,
        index=EVENT_TYPES.index(st.session_state.ata_data["event_type"]),
        key="ata_event_type"
    )
    st.session_state.ata_data["title"] = st.text_input(
        "Título / Assunto da Ata",
        value=st.session_state.ata_data["title"],
        placeholder="Ex: DDS - Uso de EPIs em Altura",
        key="ata_title"
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        st.session_state.ata_data["date"] = st.date_input("Data", value=st.session_state.ata_data["date"], key="ata_date")
    with col2:
        st.session_state.ata_data["start_time"] = st.time_input("Hora Início", value=st.session_state.ata_data["start_time"], key="ata_start_time")
    with col3:
        st.session_state.ata_data["end_time"] = st.time_input("Hora Término", value=st.session_state.ata_data["end_time"], key="ata_end_time")
    
    st.session_state.ata_data["location"] = st.text_input(
        "Local",
        value=st.session_state.ata_data["location"],
        placeholder="Ex: Sala de Reuniões Principal / Canteiro de Obras",
        key="ata_location"
    )
    st.session_state.ata_data["instructor_name"] = st.text_input(
        "Nome do Instrutor / Responsável",
        value=st.session_state.ata_data["instructor_name"],
        placeholder="Ex: João Silva",
        key="ata_instructor_name"
    )

    st.markdown(f'<div class="section-title">{_get_material_icon_html("document")} 2. Conteúdo / Agenda</div>', unsafe_allow_html=True)
    st.session_state.ata_data["content"] = st.text_area(
        "Detalhes do Conteúdo / Tópicos Abordados",
        value=st.session_state.ata_data["content"],
        height=200,
        placeholder="Descreva os pontos discutidos, treinamentos realizados, etc.",
        key="ata_content"
    )
    st.markdown(f'<div class="section-title">{_get_material_icon_html("users")} 3. Participantes</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-hint">Adicione os participantes do evento. Cada um poderá assinar digitalmente.</div>', unsafe_allow_html=True)

    if st.button("Adicionar Participante", on_click=_add_participant_callback, key="add_participant_btn"):
        st.rerun()

    if not st.session_state.ata_data["participants"]:
        _alert("Clique em 'Adicionar Participante' para incluir os presentes.", "info")

    for i, participant in enumerate(st.session_state.ata_data["participants"]):
        with st.container(border=True):
            cols_p = st.columns([0.45, 0.45, 0.1])
            with cols_p[0]:
                participant["name"] = st.text_input(f"Nome do Participante {i+1}", key=f"p_name_{participant['id']}", value=participant["name"])
            with cols_p[1]:
                participant["cpf"] = st.text_input(f"CPF do Participante {i+1}", key=f"p_cpf_{participant['id']}", value=participant["cpf"])
            with cols_p[2]:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("X", key=f"remove_p_{participant['id']}", on_click=_remove_participant_callback, args=(participant["id"],)):
                    st.rerun()
            
            st.markdown(f"**Assinatura Digital de {participant.get('name', f'Participante {i+1}')}:**")
            participant["signature_image_base64"], participant["signature_json_data"] = _render_signature_canvas(
                f"p_signature_{participant['id']}",
                participant["signature_image_base64"],
                participant["signature_json_data"]
            )
            if participant["signature_image_base64"]:
                st.image(participant["signature_image_base64"], width=150, caption="Pré-visualização da Assinatura")

    st.markdown(f'<div class="section-title">{_get_material_icon_html("attachment")} 4. Anexos</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-hint">Adicione fotos, documentos ou notas de texto relevantes ao evento.</div>', unsafe_allow_html=True)

    if st.button("Adicionar Anexo", on_click=_add_attachment_callback, key="add_attachment_btn"):
        st.rerun()

    if not st.session_state.ata_data["attachments"]:
        _alert("Clique em 'Adicionar Anexo' para incluir arquivos ou notas.", "info")

    for i, attachment in enumerate(st.session_state.ata_data["attachments"]):
        with st.container(border=True):
            cols_a = st.columns([0.9, 0.1])
            with cols_a[0]:
                attachment["type"] = st.selectbox(
                    f"Tipo de Anexo {i+1}",
                    options=ATTACHMENT_TYPES,
                    index=ATTACHMENT_TYPES.index(attachment["type"]),
                    key=f"a_type_{attachment['id']}"
                )
            with cols_a[1]:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("X", key=f"remove_a_{attachment['id']}", on_click=_remove_attachment_callback, args=(attachment["id"],)):
                    st.rerun()
            
            attachment["description"] = st.text_input(
                f"Descrição do Anexo {i+1}",
                value=attachment["description"],
                placeholder="Ex: Foto da equipe durante o DDS",
                key=f"a_desc_{attachment['id']}"
            )

            if attachment["type"] == "Nota de Texto":
                st.session_state.ata_data["attachments"][i]["file_base64"] = st.text_area(
                    f"Conteúdo da Nota {i+1}",
                    value=attachment["file_base64"] if attachment["file_base64"] else "",
                    height=100,
                    key=f"a_text_content_{attachment['id']}"
                )
                st.session_state.ata_data["attachments"][i]["file_name"] = f"Nota_{attachment['id']}.txt"
                st.session_state.ata_data["attachments"][i]["file_type"] = "text/plain"
            else:
                uploaded_file = st.file_uploader(
                    f"Upload do Anexo {i+1}",
                    type=["png", "jpg", "jpeg", "pdf", "docx", "txt"],
                    key=f"a_file_uploader_{attachment['id']}"
                )
                if uploaded_file is not None:
                    attach_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
                    if attach_size_mb > MAX_FILE_SIZE_MB:
                        try:
                            log_security_event(
                                SecurityEvent.FILE_REJECTED,
                                file_name=uploaded_file.name,
                                file_size_mb=attach_size_mb,
                                detail=f"Anexo excede {MAX_FILE_SIZE_MB} MB",
                                feature="ata_attachment_upload",
                            )
                        except Exception as log_err:
                            logger.warning(f"Falha ao registrar evento de segurança (anexo): {log_err}")
                        _alert(f"Anexo '{uploaded_file.name}' rejeitado: máximo {MAX_FILE_SIZE_MB} MB (enviado: {attach_size_mb:.1f} MB).", "error")
                    else:
                        bytes_data = uploaded_file.getvalue()
                        file_base64_encoded = base64.b64encode(bytes_data).decode('utf-8')
                        st.session_state.ata_data["attachments"][i]["file_base64"] = f"data:{uploaded_file.type};base64,{file_base64_encoded}"
                        st.session_state.ata_data["attachments"][i]["file_name"] = uploaded_file.name
                        st.session_state.ata_data["attachments"][i]["file_type"] = uploaded_file.type
                    if attachment["type"] == "Foto" and st.session_state.ata_data["attachments"][i]["file_base64"]:
                        st.image(uploaded_file, width=150, caption="Pré-visualização da Foto")
                elif st.session_state.ata_data["attachments"][i]["file_base64"]:
                    st.write(f"Arquivo atual: {st.session_state.ata_data['attachments'][i]['file_name']} ({st.session_state.ata_data['attachments'][i]['file_type']})")
                    if attachment["type"] == "Foto":
                        try:
                            header, encoded = st.session_state.ata_data["attachments"][i]["file_base64"].split(',', 1)
                            st.image(base64.b64decode(encoded), width=150, caption="Pré-visualização da Foto (já carregada)")
                        except Exception as e:
                            logger.error(f"Erro ao exibir foto pré-carregada para Ata: {e}")
                else:
                    st.session_state.ata_data["attachments"][i]["file_base64"] = None
                    st.session_state.ata_data["attachments"][i]["file_name"] = None
                    st.session_state.ata_data["attachments"][i]["file_type"] = None
    st.markdown(f'<div class="section-title">{_get_material_icon_html("signature")} 5. Assinatura do Instrutor / Responsável</div>', unsafe_allow_html=True)
    st.markdown(f"**Assinatura Digital de {st.session_state.ata_data.get('instructor_name', '')}:**")
    
    st.session_state.ata_data["instructor_signature_image_base64"], st.session_state.ata_data["instructor_signature_json_data"] = _render_signature_canvas(
        "instructor_signature", 
        st.session_state.ata_data["instructor_signature_image_base64"],
        st.session_state.ata_data["instructor_signature_json_data"]
    )
    if st.session_state.ata_data["instructor_signature_image_base64"]:
        st.image(st.session_state.ata_data["instructor_signature_image_base64"], width=150, caption="Pré-visualização da Assinatura do Instrutor")

    # Botão final para gerar a Ata completa e baixar o documento
    if st.button("Gerar Ata Completa", key="generate_ata_btn"):
        if st.session_state.get('api_client'):
            with st.spinner("Gerando documento via API... Por favor, aguarde."):
                try:
                    st.session_state.generated_pdf_buffer = None
                    st.session_state.generated_pdf_filename = None
                    st.session_state.shared_drive_link = None

                    ata_data_for_doc = st.session_state.ata_data.copy()
                    # Converte data para string para JSON
                    ata_data_for_doc['date'] = ata_data_for_doc['date'].isoformat()
                    ata_data_for_doc['start_time'] = str(ata_data_for_doc['start_time'])
                    ata_data_for_doc['end_time'] = str(ata_data_for_doc['end_time'])
                    
                    doc_bytes = st.session_state.api_client.generate_document(
                        "ata", 
                        ata_data_for_doc, 
                        user_logo_base64=st.session_state.ata_data["user_logo_base64"]
                    )
                    
                    if doc_bytes:
                        event_title_safe = "".join(c for c in ata_data_for_doc.get('title', 'Ata').replace(' ', '_') if c.isalnum() or c == '_')
                        docx_filename = f"ATA_{event_title_safe}.docx"
                        
                        st.session_state.generated_pdf_buffer = BytesIO(doc_bytes)
                        st.session_state.generated_pdf_filename = docx_filename
                        
                        _alert("Ata gerada com sucesso via API!", "success")
                    else:
                        _alert("Erro ao gerar Ata: A API não retornou dados.", "error")
                except Exception as e:
                    _alert(f"Erro ao gerar o documento da Ata via API: {e}", "error")
                    logger.error(f"Erro ao gerar documento da Ata: {e}", exc_info=True)
        else:
            _alert("Cliente da API não inicializado. Verifique a conexão.", "warning")
    
    if st.session_state.generated_pdf_buffer:
        col_download, col_share = st.columns([0.5, 0.5])
        with col_download:
            st.download_button(
                label=f"Baixar {st.session_state.generated_pdf_filename.split('.')[-1].upper()}",
                data=st.session_state.generated_pdf_buffer.getvalue(),
                file_name=st.session_state.generated_pdf_filename,
                mime="application/pdf" if st.session_state.generated_pdf_filename.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="download_ata_final_button"
            )
        with col_share:
            if st.button("Compartilhar no Google Drive", key="share_ata_button"):
                if st.session_state.get('google_drive_integrator') and st.session_state.google_drive_integrator.get_user_service():
                    with st.spinner("Fazendo upload e gerando link de compartilhamento..."):
                        pdf_buffer_copy = BytesIO(st.session_state.generated_pdf_buffer.getvalue())
                        share_link = st.session_state.google_drive_integrator.upload_file_and_get_share_link(
                            file_content=pdf_buffer_copy,
                            file_name=st.session_state.generated_pdf_filename,
                            folder_id=st.session_state.google_drive_integrator.donation_folder_id # Ou outra pasta específica
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
