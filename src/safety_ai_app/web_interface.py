import streamlit as st
import os
from safety_ai_app.safety_analyzer import SafetyAnalyzer

# Tenta inicializar o analisador.
# Usamos st.cache_resource para que o analisador seja criado apenas uma vez
# e reutilizado em todas as interações do Streamlit, melhorando a performance.
@st.cache_resource
def get_safety_analyzer():
    try:
        # Verifica se a GOOGLE_API_KEY está definida antes de inicializar o SafetyAnalyzer
        if not os.getenv("GOOGLE_API_KEY"):
            st.error("Erro: A variável de ambiente GOOGLE_API_KEY não está configurada.")
            st.error("Por favor, defina a GOOGLE_API_KEY para que o aplicativo funcione.")
            return None
            
        analyzer = SafetyAnalyzer()
        st.success("✅ Safety Analyzer inicializado com sucesso!")
        return analyzer
    except Exception as e:
        st.error(f"Erro ao inicializar o Safety Analyzer: {e}")
        st.error("Verifique sua conexão e a configuração da GOOGLE_API_KEY.")
        return None

# --- Configuração da Interface do Streamlit ---
st.set_page_config(
    page_title="Safety AI App",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="auto"
)

st.title("🛡️ Safety AI App: Análise de Segurança de Texto")
st.markdown("""
Bem-vindo, Leo! Utilize este aplicativo para analisar a segurança de textos 
utilizando o poder do Google Gemini 1.5 Flash.
""")

analyzer = get_safety_analyzer()

if analyzer:
    text_input = st.text_area(
        "Digite o texto para análise de segurança (máximo 1000 caracteres):",
        height=200,
        max_chars=1000,
        placeholder="Ex: Eu quero construir um aplicativo seguro e útil."
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        analyze_button = st.button("Analisar Texto")

    st.markdown("---") # Linha divisória

    if analyze_button:
        if not text_input.strip():
            st.warning("⚠️ Por favor, digite algum texto para análise antes de clicar no botão.")
        else:
            with st.spinner("⏳ Analisando a segurança do texto com IA..."):
                try:
                    result = analyzer.analyze_text_for_safety(text_input)
                    
                    if result["is_flagged"]:
                        st.error("🚨 INSEGURO!")
                        st.subheader("Detalhes da Análise:")
                        st.write(f"**Razão:** {result['reason']}")
                        # Exibir categorias detalhadas se disponíveis e relevantes para o modelo
                        if "categories" in result and result["categories"]:
                            st.write("**Categorias Sinalizadas:**")
                            for category, value in result["categories"].items():
                                if value:
                                    st.write(f"- {category.replace('_', ' ').title()}")
                        st.info("Recomendação: Revise o conteúdo para remover elementos inseguros.")
                    else:
                        st.success("✅ SEGURO!")
                        st.subheader("Detalhes da Análise:")
                        st.write(f"**Razão:** {result['reason']}")
                        st.info("Este conteúdo parece estar em conformidade com as diretrizes de segurança.")
                    
                    st.markdown("---")
                    st.subheader("Resposta Completa do Modelo (para depuração):")
                    st.code(result['full_response'], language='json') # Mostra a resposta JSON completa
                except Exception as e:
                    st.error(f"❌ Ocorreu um erro durante a análise: {e}")
                    st.error("Por favor, tente novamente ou verifique o log para mais detalhes.")
else:
    st.warning("⚠️ O analisador não pôde ser inicializado. Por favor, verifique se sua `GOOGLE_API_KEY` está configurada e tente novamente.")

st.markdown("""
<br>
<hr>
<p style='text-align: center; color: gray;'>Desenvolvido por Leo com IA - Adaptações do Safety AI App</p>
""", unsafe_allow_html=True)