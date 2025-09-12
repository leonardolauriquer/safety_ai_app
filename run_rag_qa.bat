@echo off
echo Iniciando o sistema RAG de Perguntas e Respostas das NRs...
poetry run python scripts/run_rag_qa.py
echo.
echo Sistema RAG encerrado.
pause