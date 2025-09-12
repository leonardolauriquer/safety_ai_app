import streamlit as st
import os
from safety_ai_app.nr_rag_qa import NRQuestionAnswering

# A GOOGLE_API_KEY agora é carregada do ambiente, definida no script .bat.
# Isso remove o hardcoding direto do arquivo Python.

@st.cache_resource
def get_nr_rag_qa_system():
    try:
        qa_system = NRQuestionAnswering()
        return qa_system
    except Exception as e:
        st.error(f"❌ Erro ao inicializar o Sistema de QA de NRs: {e}")
        st.error("Verifique se o ChromaDB foi populado e se a API Key está acessível (definida como variável de ambiente).")
        return None

st.set_page_config(
    page_title="Safety AI Chat - SST",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="auto"
)

st.markdown(
    """
    <style>
    /* Estilo Geral do App */
    .stApp {
        background-color: #0d1117; /* Fundo base escuro, inspirado no GitHub Dark */
        color: #c9d1d9; /* Cor de texto padrão clara */
        font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif; /* Fonte moderna e legível */
    }

    /* Títulos */
    h1, h2, h3, h4, h5, h6 {
        color: #27ae60; /* Verde Jade/Esmeralda para títulos */
        text-align: center;
        text-shadow: 0 0 8px rgba(39, 174, 96, 0.6); /* Brilho verde sutil */
        margin-bottom: 20px;
    }
    h2 {
        text-align: left;
        border-bottom: 2px solid #30363d; /* Borda divisória discreta */
        padding-bottom: 10px;
        margin-top: 30px;
    }

    /* Botões */
    .stButton>button {
        background-color: #27ae60; /* Verde Jade/Esmeralda para botões */
        color: white;
        border-radius: 8px;
        border: 1px solid #1e8449; /* Borda mais escura para contraste */
        padding: 12px 25px;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 0 15px rgba(39, 174, 96, 0.4);
    }
    .stButton>button:hover {
        background-color: #39d353; /* Verde mais claro no hover */
        border-color: #56d364;
        box-shadow: 0 0 20px rgba(39, 174, 96, 0.6);
        transform: translateY(-2px);
    }

    /* Abas de Navegação (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #161b22; /* Fundo dos tabs um pouco mais claro que o app */
        border-radius: 8px;
        padding: 5px;
        border: 1px solid #30363d;
    }
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #161b22;
        color: #8b949e; /* Texto cinza suave para tabs inativas */
        border-radius: 6px;
        transition: all 0.2s ease;
        padding: 10px 15px;
        border: none;
    }
    .stTabs [data-baseweb="tab-list"] button:hover {
        background-color: #30363d; /* Fundo mais escuro no hover */
        color: #c9d1d9;
    }
    .stTabs [data-baseweb="tab-list"] [aria-selected="true"] {
        background-color: #27ae60; /* Verde Jade/Esmeralda para tab selecionada */
        color: white;
        box-shadow: 0 0 10px rgba(39, 174, 96, 0.4);
    }
    .stTabs [data-baseweb="tab-list"] [aria-selected="true"] p {
        color: white !important; /* Garante que o texto da tab selecionada seja branco */
    }

    /* Campos de Texto (Input/TextArea) */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #0d1117; /* Input com o mesmo fundo do app */
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 5px;
        padding: 10px;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #27ae60; /* Borda verde Jade/Esmeralda no foco */
        box-shadow: 0 0 8px rgba(39, 174, 96, 0.5);
        outline: none;
    }
    
    /* Estilo para o Container do Chat */
    .st-emotion-cache-1ft0xkn { /* Seletor para st.container com border=True */
        border: 2px solid #30363d; /* Borda mais proeminente para o chat */
        border-radius: 10px;
        background-color: #161b22; /* Fundo do chat um pouco diferente */
        margin-top: 20px;
        box-shadow: 0 0 20px rgba(0, 255, 127, 0.1); /* Sutil brilho esverdeado */
        /* max-height e overflow-y são definidos diretamente no st.container */
    }
    
    /* Estilo para as Mensagens do Chat */
    .chat-message {
        padding: 12px 18px;
        border-radius: 18px; /* Cantos mais arredondados para bolhas */
        margin-bottom: 12px;
        max-width: 85%;
        color: #e0e6ed;
        word-wrap: break-word; /* Quebra de linha para textos longos */
        line-height: 1.5; /* Espaçamento de linha para melhor leitura */
        box-shadow: 0 2px 5px rgba(0,0,0,0.2); /* Sutil sombra para profundidade */
    }
    .chat-message.user {
        background-color: #27ae60; /* Verde Jade/Esmeralda para bolha do usuário */
        margin-left: auto;
        text-align: left;
        border-bottom-right-radius: 4px; /* Canto inferior direito levemente reto (efeito bolha) */
    }
    .chat-message.ai {
        background-color: #30363d; /* Cinza escuro para bolha da AI */
        border: 1px solid #484f58; /* Borda mais clara para definição */
        margin-right: auto;
        text-align: left;
        border-bottom-left-radius: 4px; /* Canto inferior esquerdo levemente reto (efeito bolha) */
    }
    .chat-message-container {
        display: flex;
        width: 100%;
        margin-top: 5px; /* Espaçamento entre containers de mensagens */
    }
    /* Estilo para markdown dentro das mensagens */
    .chat-message p {
        margin-bottom: 0; /* Remove margem inferior padrão de parágrafos */
    }
    .chat-message ul, .chat-message ol {
        padding-left: 20px;
        margin-top: 5px;
        margin-bottom: 5px;
    }
    .chat-message li {
        margin-bottom: 5px;
    }
    .chat-message strong {
        color: #56d364; /* Verde mais claro para negrito na AI, para se destacar */
    }

    /* Alertas (Info, Success, Error) */
    .stAlert > div {
        border-left: 5px solid;
        border-radius: 5px;
        background-color: #161b22;
        color: #c9d1d9;
        margin-top: 15px;
        padding: 15px;
    }
    .stAlert.info > div { border-color: #56d364; } /* Verde suave para info */
    .stAlert.success > div { border-color: #39d353; } /* Verde brilhante para sucesso */
    .stAlert.error > div { border-color: #f85149; } /* Vermelho para erro (padrão GitHub) */

    /* Rodapé */
    .st-emotion-cache-nahz7x { /* Seletor para o rodapé padrão do Streamlit */
        text-align: center;
        color: #8b949e;
        font-size: 0.9em;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px dashed #30363d;
    }
    
    .stAlert p { /* Garante que o texto dentro dos alertas seja legível no tema escuro */
        color: #c9d1d9 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("💬 Safety AI Chat: Seu Assistente SST")
st.markdown("Converse com a inteligência artificial para obter respostas amigáveis e diretas sobre Normas Regulamentadoras.")

tab_qa, tab_doc_processing, tab_image_analysis = st.tabs([
    "💬 **Chat com NRs**",
    "📁 **Processamento de Documentos**",
    "📸 **Análise de Imagem**"
])

# Inicializa o histórico de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

with tab_qa:
    st.header("Converse sobre Normas Regulamentadoras")
    st.markdown("Faça perguntas sobre as NRs e receba respostas detalhadas e contextuais, **focadas em SST.**")

    qa_system = get_nr_rag_qa_system()

    if qa_system:
        # Container para o histórico do chat
        chat_display_area = st.container(height=400, border=True)
        with chat_display_area:
            # Renderiza as mensagens em ordem reversa para que a mais recente fique no topo visualmente do contêiner,
            # mas o container em si exibe o scroll para as mais antigas.
            for message in reversed(st.session_state.messages): # Inverte para exibir do mais antigo para o mais novo
                if message["role"] == "user":
                    st.markdown(f'<div class="chat-message-container"><div class="chat-message user">{message["content"]}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message-container"><div class="chat-message ai">{message["content"]}</div></div>', unsafe_allow_html=True)
        
        # Área de entrada para nova pergunta - usando st.form para ENTER enviar
        with st.form(key='chat_form', clear_on_submit=True):
            user_query = st.text_input(
                "Sua pergunta sobre as NRs:",
                placeholder="Ex: Quais são as responsabilidades do empregador segundo a NR-35? Quais EPIs são exigidos para trabalho em altura?",
                key="user_query_input" # Chave para o text_input
            )
            nr_query_button = st.form_submit_button("Enviar Pergunta")

            if nr_query_button and user_query.strip():
                # Adiciona a pergunta do usuário ao histórico (no início da lista para manter a ordem para o modelo e exibição)
                st.session_state.messages.insert(0, {"role": "user", "content": user_query}) 
                
                with st.spinner("⏳ Analisando e gerando resposta..."):
                    try:
                        # A função answer_question espera uma lista de dicts no formato {"role": "user", "content": "..."}
                        nr_answer = qa_system.answer_question(user_query, st.session_state.messages)
                        
                        # Adiciona a resposta da IA ao histórico (também no início)
                        st.session_state.messages.insert(0, {"role": "ai", "content": nr_answer})
                        
                        st.rerun() # Força o Streamlit a re-renderizar para mostrar a nova mensagem
                    except Exception as e:
                        st.error(f"❌ Ocorreu um erro ao obter a resposta: {e}")
                        st.error("Por favor, tente novamente ou verifique o log para mais detalhes.")
            elif nr_query_button and not user_query.strip():
                st.warning("⚠️ Por favor, digite uma pergunta antes de enviar.")
    else:
        st.warning("⚠️ O sistema de QA de NRs não pôde ser inicializado. Verifique se o ChromaDB está populado e a API Key está configurada.")

with tab_doc_processing:
    st.header("Processamento de Documentos")
    st.markdown("Esta seção será dedicada a funcionalidades futuras, como:\n"
                "- **Upload de documentos** (PDFs, DOCX) para expansão da base de conhecimento.\n"
                "- **Extração de informações** e sumarização automática.\n"
                "- **Perguntas e Respostas** sobre seus próprios documentos.")
    st.info("💡 **Em desenvolvimento:** Funcionalidades para gerenciar seus próprios documentos de segurança.")
    st.file_uploader("Carregue seu documento aqui (futuro)", type=["pdf", "docx", "txt"], disabled=True)
    st.image("https://via.placeholder.com/400x200/161b22/27ae60?text=Documentos+SST+[Futuro]", # Placeholder com cores novas
             caption="Gerenciamento inteligente de documentos",
             width='stretch')

with tab_image_analysis:
    st.header("Análise de Imagem (Visão)")
    st.markdown("Esta funcionalidade permitirá análises visuais avançadas para o ambiente de trabalho.")
    st.info('👁️ **Funcionalidade da Plataforma:** Para utilizar a "Análise de Imagem", ative a ferramenta Vision.')
    st.image("https://via.placeholder.com/400x200/161b22/27ae60?text=Análise+Visual+SST+[Futuro]", # Placeholder com cores novas
             caption="Identificação inteligente de riscos visuais",
             width='stretch')
    st.write("Aguarde futuras atualizações para integração direta de upload de imagem via Streamlit.")

st.markdown("""
<br>
<hr style="border-top: 1px dashed #30363d;">
<p style='text-align: center; color: #8b949e; font-size: 0.85em;'>
    Desenvolvido com IA 🤖 por Leo - Focado em um futuro mais seguro.
</p>
""", unsafe_allow_html=True)