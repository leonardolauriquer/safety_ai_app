@echo off
setlocal

echo --- Iniciando Safety AI App Web (Streamlit) ---

:: Navega para o diretório raiz do projeto (onde está o pyproject.toml)
pushd "%~dp0"

:: Ativa o ambiente virtual do Poetry e executa o aplicativo Streamlit.
:: 'poetry run' garante que o Python do ambiente virtual e o Streamlit sejam usados.
:: 'src/safety_ai_app/web_app.py' é o caminho para o seu script Streamlit.
poetry run python -m streamlit run src/safety_ai_app/web_app.py

:: Retorna ao diretório original
popd

pause