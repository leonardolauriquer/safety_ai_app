import streamlit as st
import logging
from typing import List, Dict, Any
from safety_ai_app.theme_config import THEME, _get_material_icon_html
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, render_back_button

logger = logging.getLogger(__name__)

def show():
    inject_glass_styles()
    
    # Cabeçalho com ícone de Admin
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 30px;">
            <div style="background: {THEME['colors']['primary']}; padding: 12px; border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                {_get_material_icon_html("admin_panel_settings", size=32, color="#FFFFFF")}
            </div>
            <div>
                <h1 style="margin: 0; font-size: 1.8rem;">Base de Conhecimento Curada</h1>
                <p style="margin: 0; color: #94a3b8; font-size: 0.9rem;">Gestão administrativa de documentos para a IA</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if not st.session_state.get("is_admin", False):
        st.error("⚠️ Acesso Negado. Esta página é restrita a administradores.")
        if st.button("Voltar ao Início"):
            st.session_state.page = "home"
            st.rerun()
        return

    client = st.session_state.get("api_client")
    if not client:
        st.error("Erro: Cliente API não inicializado.")
        return

    # Tabs para Organização
    tab_list, tab_upload = st.tabs(["📚 Documentos Atuais", "📤 Novo Upload"])

    with tab_list:
        st.markdown("### Repositório Central")
        docs = client.admin_list_knowledge()
        
        if not docs:
            st.info("Nenhum documento cadastrado na base de conhecimento curada.")
        else:
            # Tabela customizada com Glassmorphism
            for doc in docs:
                status_color = "#4ade80" if doc.get("active", True) else "#94a3b8"
                status_text = "Ativo" if doc.get("active", True) else "Inativo"
                
                with st.container():
                    st.markdown(
                        f"""
                        <div style="
                            background: rgba(30, 41, 59, 0.4);
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            border-radius: 12px;
                            padding: 15px;
                            margin-bottom: 10px;
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                        ">
                            <div style="flex: 1;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span style="font-weight: 600; color: #f8fafc;">{doc['title']}</span>
                                    <span style="font-size: 0.7rem; background: rgba(74, 222, 128, 0.1); color: {status_color}; padding: 2px 8px; border-radius: 10px; border: 1px solid {status_color}40;">
                                        {status_text}
                                    </span>
                                </div>
                                <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">
                                    {doc['category']} • {doc['filename']}
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Ações (Streamlit Native Buttons dentro de colunas para melhor controle)
                    col1, col2, col3 = st.columns([1, 1, 4])
                    with col1:
                        if st.button("Alternar Status", key=f"toggle_{doc['id']}"):
                            client.admin_toggle_knowledge(doc['id'])
                            st.rerun()
                    with col2:
                        if st.button("Remover", key=f"del_{doc['id']}", type="secondary"):
                            if client.admin_delete_knowledge(doc['id']):
                                st.success(f"Removido: {doc['title']}")
                                st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)

    with tab_upload:
        st.markdown("### Adicionar à Inteligência do Sistema")
        st.write("Documentos enviados aqui serão usados como base para todas as respostas da IA e geração de documentos.")
        
        with st.form("upload_form", clear_on_submit=True):
            uploaded_file = st.file_uploader("Escolha o arquivo (PDF, DOCX)", type=["pdf", "docx"])
            title = st.text_input("Título do Documento", placeholder="Ex: NR-35 - Trabalho em Altura")
            category = st.selectbox("Categoria", ["Normas Regulamentadoras", "Procedimentos Internos", "Manuais de Equipamento", "Checklists", "Outros"])
            description = st.text_area("Descrição Breve (opcional)")
            
            submit = st.form_submit_button("🚀 Upload e Indexar")
            
            if submit:
                if not uploaded_file or not title:
                    st.error("Por favor, forneça o arquivo e um título.")
                else:
                    with st.spinner("Processando upload e indexação..."):
                        result = client.admin_upload_knowledge(
                            uploaded_file, 
                            title, 
                            category, 
                            description or ""
                        )
                        if result.get("status") == "success":
                            st.success(f"Sucesso! Documento '{title}' indexado com ID: {result.get('id')}")
                        else:
                            st.error(f"Erro no upload: {result.get('message')}")

    render_back_button("Voltar ao Dashboard", "home", key="back_to_home_admin")

if __name__ == "__main__":
    # Para teste direto
    show()
