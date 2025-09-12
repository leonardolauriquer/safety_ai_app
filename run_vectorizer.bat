@echo off
echo Executando o script de vetorizacao e indexacao das NRs...
poetry run python scripts/vectorize_nrs.py
echo.
echo Script vectorize_nrs.py executado.
pause