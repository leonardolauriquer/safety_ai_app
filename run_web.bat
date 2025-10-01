@echo off
setlocal

echo --- Iniciando Safety AI App Web (Streamlit) ---

:: Define a variável de ambiente GOOGLE_API_KEY aqui.
:: ATENÇÃO: Hardcoding de chaves de API não é a prática mais segura para produção.
:: Mantenha a sua chave válida.
set GOOGLE_API_KEY=AIzaSyCLyChqWhtWTpCZg3pvYbFHRR8FXHGHViY

:: Navega para o diretório raiz do projeto (onde está o pyproject.toml)
pushd "%~dp0"

:: Ativa o ambiente virtual do Poetry e executa o Streamlit como um módulo Python.
:: Agora aponta para o novo arquivo principal: web_app.py
::
:: IMPORTANTE: Se você encontrar um "ModuleNotFoundError" (ex: para 'markdown'),
:: você precisa adicionar a dependência ao seu projeto Poetry.
:: Para fazer isso, ABRA O TERMINAL NA RAIZ DO PROJETO e execute:
:: poetry add <nome_da_dependencia>
:: Exemplo: poetry add markdown
::
poetry run python -m streamlit run src/safety_ai_app/web_app.py

:: Retorna ao diretório original
popd

pause