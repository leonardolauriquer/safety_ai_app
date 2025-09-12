@echo off
setlocal

echo --- Iniciando Safety AI App Web (Streamlit) ---

:: Define a variável de ambiente GOOGLE_API_KEY aqui.
:: ATENÇÃO: Hardcoding de chaves de API não é a prática mais segura para produção.
set GOOGLE_API_KEY=AIzaSyD2sKHDVSSRQ5xveygd1oj57yBJHCW9hQ

:: Navega para o diretório raiz do projeto (onde está o pyproject.toml)
pushd "%~dp0"

:: Ativa o ambiente virtual do Poetry e executa o Streamlit como um módulo Python.
:: Isso garante que o Streamlit seja encontrado e executado corretamente.
poetry run python -m streamlit run src/safety_ai_app/web_interface.py

:: Retorna ao diretório original
popd

pause